import pandas as pd
from pathlib import Path
from src.config.config import OPENAI_API_KEY
from openai import OpenAI

# 분리된 모듈 import
from src.services.rag.pdf_extractor import PDFExtractor
from src.services.rag.data_processor import DataProcessor
from src.services.rag.text_chunker import TextChunker
from src.services.rag.vector_store import VectorStoreService

openai = OpenAI(api_key=OPENAI_API_KEY)

class RAGService:
    def __init__(self, persist_directory='./data/vector_store'):
        """
        RAG 파이프라인을 총괄하는 서비스 클래스.
        ETL 프로세스를 각 담당 클래스에게 위임하여 실행합니다.
        """
        # 각 단계별 담당자(Worker) 초기화
        self.pdf_extractor = PDFExtractor()
        self.data_processor = DataProcessor()
        self.text_chunker = TextChunker()
        self.vector_store = VectorStoreService(persist_directory)


    def process_pdf_for_rag(self, pdf_path: str, doc_id: str):
        """
        PDF 파일을 처리하여 RAG 시스템에 적재할 수 있는 형태로 변환 및 저장합니다.
        :param pdf_path: PDF 파일 경로
        :param doc_id: 문서를 식별할 수 있는 고유 ID (예: house_manage_no)
        """
        # 1. Extract: PDF에서 Raw 데이터 추출
        print(f"🔍 PDF 추출 시작: {pdf_path}")
        raw_content = self.pdf_extractor.extract_content(pdf_path)
        
        # (디버깅용) 추출된 표 데이터 엑셀 저장
        self.save_tables_to_excel(raw_content)
        
        # 2. Transform: 데이터 정제 및 마크다운 변환
        print("🧹 데이터 정제 및 변환 중...")
        processed_docs = self.data_processor.process_content(raw_content)
        
        # 3. Load (Temporary): 파일로 저장 (추후 Vector DB 저장으로 변경)
        final_rag_document = "\n\n".join(processed_docs)
        self.save_rag_document_as_md(pdf_path, final_rag_document)
        
        # 4. Chunking: 텍스트 청킹
        print("🔪 텍스트 청킹 중...")
        chunks = self.text_chunker.chunk_markdown(final_rag_document)
        
        # [중요] 모든 청크에 문서 ID(doc_id) 메타데이터 추가
        for chunk in chunks:
            chunk.metadata['doc_id'] = str(doc_id)

        print(f"✅ 총 {len(chunks)}개의 청크가 생성되었습니다.")
        
        # (디버깅용) 첫 번째 청크 내용 출력
        if chunks:
            print(f"🔍 첫 번째 청크 예시:\n{chunks[0].page_content[:200]}...")
            print(f"🔖 메타데이터: {chunks[0].metadata}")
            
            # 5. Load: 벡터 DB 저장
            self.vector_store.add_documents(chunks)

        return '====처리 완료===='

    def answer_question(self, question: str, doc_id: str = None):
        """
        사용자의 질문에 대해 RAG 방식으로 답변을 생성합니다.
        :param doc_id: 특정 문서에서만 검색하려면 ID 지정
        """
        print(f"🤔 질문 분석 중: {question} (doc_id: {doc_id})")
        
        # 1. Retrieve: 관련 문서 검색 (필터 적용)
        filter_condition = {"doc_id": str(doc_id)} if doc_id else None
        related_docs = self.vector_store.search(query=question, k=5, filter=filter_condition) 
        
        if not related_docs:
            return "죄송합니다. 해당 공고문에서 관련 정보를 찾을 수 없습니다."

        # 2. Augment: 프롬프트 구성
        context = "\n\n".join([doc.page_content for doc in related_docs])
        
        system_prompt = f"""
        당신은 아파트 청약 공고문을 전문적으로 분석하여 사용자에게 정보를 제공하는 AI 어시스턴트입니다.
        아래 제공된 [공고문 내용]을 바탕으로 사용자의 질문에 정확하고 친절하게 답변해 주세요.
        
        - [공고문 내용]에 없는 정보라면, 추측하지 말고 "공고문 내용에서 관련 정보를 찾을 수 없습니다."라고 답변하세요.
        - 답변은 핵심 내용을 요약하여 이해하기 쉽게 설명하세요.
        - 표 형식의 데이터가 있다면 필요 시 표나 리스트 형태로 정리해서 보여주세요.

        [공고문 내용]
        {context}
        """

        # 3. Generate: 답변 생성
        try:
            response = openai.chat.completions.create(
                model="gpt-4o-mini", # 가성비 좋은 모델 사용 (필요 시 gpt-4o 변경 가능)
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}
                ],
                temperature=0, # 사실 기반 답변을 위해 0 설정
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
