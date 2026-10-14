"""
답변 품질 테스트 (실행: python eval/run_eval.py)
- 질문 세트를 RAG로 답변받아 자동 채점하고 eval/results/에 CSV로 저장
"""
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

# src 모듈을 import할 수 있도록 프로젝트 루트를 경로에 추가 (app.py와 같은 방식)
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.services.rag_service import RAGService

QUESTIONS_PATH = PROJECT_ROOT / "eval" / "questions_2026000494.json"
RESULTS_DIR = PROJECT_ROOT / "eval" / "results"
SEARCH_K = 10  # rag_service.answer_question의 검색 개수와 같게 맞춤


def normalize(text):
    """공백/쉼표/줄바꿈 차이로 채점이 틀리지 않도록 제거"""
    return text.replace(" ", "").replace(",", "").replace("\n", "")


def contains_all(text, expected):
    """expected = [["표기A", "표기B"], ["정답2"]] → 그룹마다 표기 중 하나라도 있으면 통과"""
    t = normalize(text)
    return all(any(normalize(v) in t for v in group) for group in expected)


def main():
    data = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    doc_id = data["doc_id"]
    rag = RAGService()

    rows = []
    for q in data["questions"]:
        # 1) 검색 결과에 정답이 들어 있는지 (검색 문제 vs 모델 문제 구분용)
        docs = rag.vector_store.search(q["question"], k=SEARCH_K, filter={"doc_id": doc_id})
        context = "\n".join(d.page_content for d in docs)
        retrieval_hit = contains_all(context, q["expected"])

        # 2) 실제 답변에 정답이 들어 있는지
        answer = rag.answer_question(q["question"], doc_id=doc_id, model="openai", conversation_history=[])
        answer_hit = contains_all(answer, q["expected"])

        rows.append({
            "id": q["id"],
            "question": q["question"],
            "answer_key": q["answer"],
            "retrieval_hit": "O" if retrieval_hit else "X",
            "answer_hit": "O" if answer_hit else "X",
            "manual_grade": "",  # 직접 채점: 정답 / 부분 / 오답 / 없음
            "answer": answer,
        })
        print(f"[{q['id']:>2}] 검색 {'O' if retrieval_hit else 'X'} | 답변 {'O' if answer_hit else 'X'} | {q['question']}")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / f"{doc_id}_{datetime.now():%Y%m%d_%H%M}.csv"
    # utf-8-sig: 엑셀에서 열었을 때 한글이 깨지지 않도록
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    passed = sum(r["answer_hit"] == "O" for r in rows)
    print(f"\n자동 채점: {passed}/{len(rows)} 통과 → {out_path}")


if __name__ == "__main__":
    main()
