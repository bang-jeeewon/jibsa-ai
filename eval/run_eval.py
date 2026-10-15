"""
답변 품질 테스트 (실행: python eval/run_eval.py)
- 질문 세트를 RAG로 답변받아 자동 채점하고 eval/results/에 CSV로 저장
- 정답 키워드가 파이프라인의 어느 단계에서 사라지는지 함께 기록
  ① 추출(HTML) → ② 변환(마크다운) → ③ 청킹(DB 청크) → ④ 검색(상위 k개) → ⑤ 생성(답변)
"""
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

# src 모듈을 import할 수 있도록 프로젝트 루트를 경로에 추가 (app.py와 같은 방식)
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from bs4 import BeautifulSoup
from sqlalchemy import text
from src.services.rag_service import RAGService

QUESTIONS_PATH = PROJECT_ROOT / "eval" / "questions_2026000494.json"
RESULTS_DIR = PROJECT_ROOT / "eval" / "results"
HTML_CACHE_DIR = PROJECT_ROOT / "tmp" / "html"  # ① Upstage 추출 결과 캐시
MARKDOWN_DIR = PROJECT_ROOT / "data" / "md"     # ② 마크다운 변환 결과 (로컬 분석 시 저장)
SEARCH_K = 10  # rag_service.answer_question의 검색 개수와 같게 맞춤

# 파이프라인 단계 (앞에서부터 처음 X가 나온 단계를 원인으로 봄)
STAGES = [
    ("in_html", "① 추출"),
    ("in_markdown", "② 변환"),
    ("in_chunks", "③ 청킹"),
    ("retrieval_hit", "④ 검색"),
    ("answer_hit", "⑤ 생성"),
]


def normalize(text):
    """공백/쉼표/줄바꿈 차이로 채점이 틀리지 않도록 제거"""
    return text.replace(" ", "").replace(",", "").replace("\n", "")


def contains_all(text, expected):
    """expected = [["표기A", "표기B"], ["정답2"]] → 그룹마다 표기 중 하나라도 있으면 통과"""
    t = normalize(text)
    return all(any(normalize(v) in t for v in group) for group in expected)


def mark(text, expected):
    """O: 정답 있음 / X: 없음 / -: 결과물이 없어서 확인 못 함"""
    if text is None:
        return "-"
    return "O" if contains_all(text, expected) else "X"


def find_cause(row):
    """답변이 맞으면 '정상', 아니면 처음으로 X가 나온 단계"""
    if row["answer_hit"] == "O":
        return "정상"
    for key, name in STAGES:
        if row[key] == "X":
            return name
    return "확인 불가"


def load_stage_texts(rag, doc_id):
    """①②③ 단계 결과물 전체 텍스트 (정답 키워드가 어느 단계에서 사라지는지 추적용)"""
    html_path = HTML_CACHE_DIR / f"{doc_id}.html"
    html_text = None
    if html_path.exists():
        html_text = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser").get_text(" ")

    md_paths = sorted(MARKDOWN_DIR.glob(f"{doc_id}_*.md"))
    markdown_text = md_paths[-1].read_text(encoding="utf-8") if md_paths else None

    sql = text("""
        SELECT e.document FROM langchain_pg_embedding e
        JOIN langchain_pg_collection c ON e.collection_id = c.uuid
        WHERE c.name = :name AND e.cmetadata->>'doc_id' = :doc_id
    """)
    with rag.vector_store.engine.connect() as conn:
        rows = conn.execute(sql, {"name": rag.vector_store.collection_name, "doc_id": doc_id})
        chunks_text = "\n".join(row[0] for row in rows) or None

    return {"html": html_text, "markdown": markdown_text, "chunks": chunks_text}


def main():
    data = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    doc_id = data["doc_id"]
    rag = RAGService()
    stage_texts = load_stage_texts(rag, doc_id)

    rows = []
    for q in data["questions"]:
        # 4) 검색 결과(상위 k개)에 정답이 들어 있는지
        docs = rag.vector_store.search(q["question"], k=SEARCH_K, filter={"doc_id": doc_id})
        context = "\n".join(d.page_content for d in docs)

        # 5) 실제 답변에 정답이 들어 있는지
        answer = rag.answer_question(q["question"], doc_id=doc_id, model="openai", conversation_history=[])

        row = {
            "id": q["id"],
            "question": q["question"],
            "answer_key": q["answer"],
            "in_html": mark(stage_texts["html"], q["expected"]),
            "in_markdown": mark(stage_texts["markdown"], q["expected"]),
            "in_chunks": mark(stage_texts["chunks"], q["expected"]),
            "retrieval_hit": mark(context, q["expected"]),
            "answer_hit": mark(answer, q["expected"]),
        }
        row["cause"] = find_cause(row)
        row["manual_grade"] = ""  # 직접 채점: 정답 / 부분 / 오답 / 없음
        row["answer"] = answer
        rows.append(row)

        print(
            f"[{q['id']:>2}] HTML {row['in_html']} | MD {row['in_markdown']} | 청크 {row['in_chunks']} | "
            f"검색 {row['retrieval_hit']} | 답변 {row['answer_hit']} → {row['cause']} | {q['question']}"
        )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / f"{doc_id}_{datetime.now():%Y%m%d_%H%M%S}.csv"
    # utf-8-sig: 엑셀에서 열었을 때 한글이 깨지지 않도록
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    passed = sum(r["answer_hit"] == "O" for r in rows)
    print(f"\n자동 채점: {passed}/{len(rows)} 통과 → {out_path}")

    # 원인 단계별 개수 (어느 단계를 고쳐야 효과가 큰지)
    causes = {}
    for r in rows:
        causes[r["cause"]] = causes.get(r["cause"], 0) + 1
    print("원인별:", ", ".join(f"{k} {v}개" for k, v in sorted(causes.items())))


if __name__ == "__main__":
    main()
