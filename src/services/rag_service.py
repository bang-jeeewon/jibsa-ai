import pandas as pd
from pathlib import Path
from src.config.config import OPENAI_API_KEY, GOOGLE_API_KEY
from openai import OpenAI
from google.genai import Client
import time
import random
import re

# 분리된 모듈 import
from src.services.rag.pdf_extractor import PDFExtractor
# from src.services.rag.pdf_extractor_pymupdf import PDFExtractorPyMuPDF
# from src.services.rag.pdf_extractor_llama import PDFExtractorLlama
# from src.services.rag.pdf_extractor_marker import PDFExtractorMarker
from src.services.rag.data_processor import DataProcessor
from src.services.rag.text_chunker import TextChunker
from src.services.rag.vector_store import VectorStoreService

openai = OpenAI(api_key=OPENAI_API_KEY)
genai_client = Client(api_key=GOOGLE_API_KEY) 

class RAGService:
    def __init__(self, persist_directory=None, embedding_model="openai"):
        """
        RAG 파이프라인을 총괄하는 서비스 클래스.
        ETL 프로세스를 각 담당 클래스에게 위임하여 실행합니다.
        :param persist_directory: None이면 in-memory 모드 (파일 저장 안 함, 서버 재시작 시 데이터 사라짐)
        :param embedding_model: 사용할 임베딩 모델 ("openai" 또는 "gemini")
        """
        # 각 단계별 담당자(Worker) 초기화
        self.pdf_extractor = PDFExtractor()
        # self.pdf_extractor_pymupdf = PDFExtractorPyMuPDF()
        # self.pdf_extractor_llama = PDFExtractorLlama()
        # self.pdf_extractor_marker = PDFExtractorMarker()
        self.data_processor = DataProcessor()
        self.text_chunker = TextChunker()
        self.vector_store = VectorStoreService(persist_directory, embedding_model=embedding_model)  # None = in-memory


    def process_pdf_for_rag(self, pdf_path: str, doc_id: str):
        """
        PDF 파일을 처리하여 RAG 시스템에 적재할 수 있는 형태로 변환 및 저장합니다.
        :param pdf_path: PDF 파일 경로
        :param doc_id: 문서를 식별할 수 있는 고유 ID (예: house_manage_no)
        """
        # 1. Extract: PDF에서 Raw 데이터 추출
        print(f"🔍 PDF 추출 시작: {pdf_path}")
        raw_content = self.pdf_extractor.extract_content(pdf_path)
        # raw_content = self.pdf_extractor_pymupdf.extract_content(pdf_path)
        # raw_content = self.pdf_extractor_llama.extract_content(pdf_path)
        # raw_content = self.pdf_extractor_marker.extract_content(pdf_path)
        
        # (디버깅용) 추출된 표 데이터 엑셀 저장
        # self.save_tables_to_excel(raw_content)
        
        # 2. Transform: 데이터 정제 및 마크다운 변환
        print("🧹 데이터 정제 및 변환 중...")
        processed_docs = self.data_processor.process_content(raw_content)
        
        # 3. 마크다운 문서 생성 (파일 저장 없이 메모리에서만 처리)
        final_rag_document = "\n\n".join(processed_docs)
        # 파일 저장 제거: self.save_rag_document_as_md(pdf_path, final_rag_document)
        
        # 4. Chunking: 텍스트 청킹
        print("🔪 텍스트 청킹 중...")
        chunks = self.text_chunker.chunk_markdown(final_rag_document)
        
        # [중요] 모든 청크에 문서 ID(doc_id) 메타데이터 추가
        for chunk in chunks:
            chunk.metadata['doc_id'] = str(doc_id)

        print(f"✅ 총 {len(chunks)}개의 청크가 생성되었습니다.")
        
        # (디버깅용) 첫 번째 청크 내용 출력
        if chunks:
            # 5. Load: 벡터 DB 저장
            self.vector_store.add_documents(chunks)

        return '====처리 완료===='

    def answer_question(self, question: str, doc_id: str = None, model: str = "openai"):
        """
        사용자의 질문에 대해 RAG 방식으로 답변을 생성합니다.
        :param doc_id: 특정 문서에서만 검색하려면 ID 지정
        :param model: 사용할 모델 ("openai" 또는 "gemini")
        """
        model_display = "GPT-4o-mini" if model == "openai" else "Gemini Pro"
        print(f"🤔 질문 분석 중: {question}")
        print(f"📋 문서 ID: {doc_id}, 선택된 LLM: {model_display}")
        # 1회 질문 비용 계산 (k=5 기준):
        # - 질문: 약 50 토큰
        # - 검색된 컨텍스트 (k=5): 청크 5개 × 250 토큰 = 약 1,250 토큰
        # - 시스템 프롬프트: 약 50 토큰
        # - 총 입력: 약 1,350 토큰
        # - 출력: 500 토큰
        # - OpenAI gpt-4o-mini 가격: Input $0.15/1M tokens, Output $0.60/1M tokens
        # - 비용: (1,350/1,000,000 × $0.15) + (500/1,000,000 × $0.60) = $0.0002025 + $0.0003 = $0.0005025 (약 0.65원)
        # - 한 달 10,000원 예산: 하루 약 512개 질문 가능 (여전히 충분!)
        
        # 1. Retrieve: 관련 문서 검색 (필터 적용)
        # k=5로 설정하여 더 많은 컨텍스트 제공 (정확도 향상)
        filter_condition = {"doc_id": str(doc_id)} if doc_id else None
        related_docs = self.vector_store.search(query=question, k=5, filter=filter_condition) 
        
        if not related_docs:
            return "죄송합니다. 해당 공고문에서 관련 정보를 찾을 수 없습니다."

        # 2. Augment: 프롬프트 구성
        context = "\n\n".join([doc.page_content for doc in related_docs])
        
        # 비용 절감: 프롬프트 간소화
        system_prompt = f"""아파트 청약 공고문 전문 분석 AI입니다. 아래 내용만 참고하여 질문에 답변하세요. 없는 정보는 "찾을 수 없습니다"라고 답변하세요.

[공고문 내용]
{context}
"""

        # 3. Generate: 답변 생성
        try:
            if model == "gemini":
                # Gemini 모델 사용 (새 SDK: google-genai)
                if not genai_client:
                    return "GOOGLE_API_KEY가 설정되지 않아 Gemini를 사용할 수 없습니다."
                
                prompt = f"{system_prompt}\n\n질문: {question}"
                
                # 재시도 로직 (429 에러 대응)
                max_retries = 3
                retry_delay = 2  # 초기 대기 시간 (초)
                
                for attempt in range(max_retries):
                    try:
                        # 새 SDK 사용법
                        response = genai_client.models.generate_content(
                            model='gemini-2.0-flash-exp',
                            contents=prompt,
                            config={
                                'temperature': 0,
                                'max_output_tokens': 500,
                            }
                        )
                        return response.text
                        
                    except Exception as e:
                        error_msg = str(e)
                        
                        # 429 에러 처리
                        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg or "quota" in error_msg.lower():
                            if attempt < max_retries - 1:
                                # 에러 메시지에서 retry delay 추출 시도
                                retry_after = None
                                retry_match = re.search(r'retry in ([\d.]+)s', error_msg, re.IGNORECASE)
                                if retry_match:
                                    retry_after = float(retry_match.group(1))
                                else:
                                    # Exponential backoff
                                    retry_after = retry_delay * (2 ** attempt) + random.uniform(0, 1)
                                
                                print(f"⚠️ Gemini 할당량 초과 (429). {retry_after:.1f}초 후 재시도... ({attempt + 1}/{max_retries})")
                                time.sleep(retry_after)
                            else:
                                return f"죄송합니다. Gemini API 할당량이 초과되어 답변을 생성할 수 없습니다. 잠시 후 다시 시도해주세요."
                        else:
                            # 다른 에러는 즉시 재발생
                            raise
            else:
                # OpenAI 모델 사용 (기본값)
                response = openai.chat.completions.create(
                    model="gpt-4o-mini", # 가성비 좋은 모델 사용
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": question}
                    ],
                    temperature=0, # 사실 기반 답변을 위해 0 설정
                    max_tokens=500,  # 답변 길이 확장 (200 → 500, 긴 답변도 완전히 제공)
                )
                return response.choices[0].message.content
        except Exception as e:
            return f"죄송합니다. 답변 생성 중 오류가 발생했습니다: {e}"

    def clear_database(self):
        """벡터 DB를 초기화합니다."""
        print("🗑️ 벡터 DB 초기화 요청")
        self.vector_store.clear()

    def save_tables_to_excel(self, all_content, output_path="extracted_tables.xlsx"):
        """
        (디버깅용) 추출된 표 데이터를 엑셀 파일로 저장
        """
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            table_count = 0
            for item in all_content:
                if item["type"] == "table":
                    table_count += 1
                    table_data = item["content"]
                    
                    # 데이터가 없거나 유효하지 않으면 패스
                    if not table_data: continue
                    
                    df = pd.DataFrame(table_data)
                    sheet_name = f"Table {table_count}"
                    # 시트 이름 길이 제한 (31자)
                    if len(sheet_name) > 31: sheet_name = sheet_name[:31]
                    
                    try:
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                    except Exception as e:
                        print(f"엑셀 시트 저장 실패 ({sheet_name}): {e}")

        print(f"✅ 표 데이터 엑셀 저장 완료: {output_path}")

    def save_rag_document_as_md(self, pdf_path: str, final_rag_document: str):
        """
        최종 변환된 문서를 .md 파일로 저장
        """
        original_stem = Path(pdf_path).stem 
        md_filename = original_stem + ".md"
        output_dir = "data/md" 
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        output_path = Path(output_dir) / md_filename

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(final_rag_document)
            print(f"✅ 최종 Markdown 저장 완료: {output_path}")
        except Exception as e:
            print(f"❌ 파일 저장 실패: {e}")
