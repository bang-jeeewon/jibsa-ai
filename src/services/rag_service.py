from pathlib import Path
from src.config.config import OPENAI_API_KEY, GOOGLE_API_KEY, CHUNK_BATCH_SIZE, RENDER
# from openai import OpenAI
# from google.genai import Client
import time
import random
import re
import gc

# 분리된 모듈 import
# from src.services.rag.pdf_extractor_pymupdf import PDFExtractorPyMuPDF
# from src.services.rag.pdf_extractor_llama import PDFExtractorLlama
# from src.services.rag.pdf_extractor_marker import PDFExtractorMarker
# from src.services.rag.pdf_extractor import PDFExtractor
# from src.services.rag.data_processor import DataProcessor
# from src.services.rag.text_chunker import TextChunker
# from src.services.rag.vector_store import VectorStoreService

# openai = OpenAI(api_key=OPENAI_API_KEY)
# genai_client = Client(api_key=GOOGLE_API_KEY) 

class RAGService:
    def __init__(self, embedding_model="openai"):
        """
        RAG 파이프라인을 총괄하는 서비스 클래스.
        ETL 프로세스를 각 담당 클래스에게 위임하여 실행합니다.
        :param embedding_model: 사용할 임베딩 모델 ("openai" 또는 "gemini")
        """
        print("RAGService 1")
        from google.genai import Client
        gc.collect()
        print("RAGService 2")
        from openai import OpenAI
        gc.collect()
        print("RAGService 3")
        from src.services.rag.pdf_extractor import PDFExtractor
        gc.collect()
        print("RAGService 4")
        # from src.services.rag.data_processor import DataProcessor
        from src.services.rag.text_chunker import TextChunker
        gc.collect()
        print("RAGService 5")
        from src.services.rag.vector_store import VectorStoreService
        gc.collect()
        print("RAGService 6")
        from src.services.archive_service import ArchiveService
        print("RAGService 7")

        self.openai = OpenAI(api_key=OPENAI_API_KEY)
        self.genai_client = Client(api_key=GOOGLE_API_KEY) if GOOGLE_API_KEY else None

        # 각 단계별 담당자(Worker) 초기화
        self.pdf_extractor = PDFExtractor()
        # self.pdf_extractor_pymupdf = PDFExtractorPyMuPDF()
        # self.pdf_extractor_llama = PDFExtractorLlama()
        # self.pdf_extractor_marker = PDFExtractorMarker()
        # self.data_processor = DataProcessor()
        self.text_chunker = TextChunker()
        self.vector_store = VectorStoreService(embedding_model=embedding_model)
        self.archive = ArchiveService() # S3 아카이브 (app.py에서도 rag.archive로 사용)
        gc.collect()


    def process_for_rag(self, pdf_path: str, doc_id: str, archive_prefix: str = None):
        """
        PDF 파일을 처리하여 RAG 시스템에 적재할 수 있는 형태로 변환 및 저장합니다.
        :param pdf_path: PDF 파일 경로
        :param doc_id: 문서를 식별할 수 있는 고유 ID (예: house_manage_no)
        :param archive_prefix: S3 아카이브 폴더 (None이면 S3 저장 안 함)
        :return: {"skipped": 이미 처리된 공고인지, "chunk_count": 생성된 청크 수}
        """
        # 0. 이미 벡터 DB에 적재된 공고면 추출/청킹/아카이브 모두 건너뜀
        if self.vector_store._exists(str(doc_id)):
            print(f"⏩ doc_id={doc_id}는 이미 처리된 공고입니다. 분석을 건너뜁니다.")
            return {"skipped": True, "chunk_count": 0}

        
        # 1. Extract: Upstage Document Parse API로 PDF -> HTML 변환 후 Markdown으로 변환
        print(f"🔍 PDF 추출 시작: {pdf_path}")
        # 같은 공고를 다시 분석할 때 Upstage 재호출 방지 (페이지당 과금 절약, tmp/는 gitignore 대상)
        html_cache_path = Path("tmp/html") / f"{doc_id}.html"
        if html_cache_path.exists():
            html_content = html_cache_path.read_text(encoding="utf-8")
            print(f"♻️ 캐시된 추출 결과 사용: {html_cache_path}")
        else:
            html_content = self.pdf_extractor.extract_html_by_document_digitization(pdf_path)
            html_cache_path.parent.mkdir(parents=True, exist_ok=True)
            html_cache_path.write_text(html_content, encoding="utf-8")
        markdown_content = self.pdf_extractor.html_to_markdown(html_content)


        # (아카이브) 원본 PDF, 추출 HTML, 변환 Markdown 저장
        if archive_prefix:
            self.archive.put_file(pdf_path, archive_prefix + "notice.pdf", "application/pdf")
            self.archive.put_text(html_content, archive_prefix + "extracted.html", "text/html; charset=utf-8")
            self.archive.put_text(markdown_content, archive_prefix + "document.md", "text/markdown; charset=utf-8")

        # raw_content = self.pdf_extractor.extract_content(pdf_path) ############################################## 1
        # # raw_content = self.pdf_extractor_pymupdf.extract_content(pdf_path)
        # # raw_content = self.pdf_extractor_llama.extract_content(pdf_path)
        # # raw_content = self.pdf_extractor_marker.extract_content(pdf_path)
        
        # # (디버깅용) 추출된 표 데이터 엑셀 저장
        # self.save_tables_to_excel(raw_content)
        
        # # 2. Transform: 데이터 정제 및 마크다운 변환
        # print("🧹 데이터 정제 및 변환 중...")
        # processed_docs = self.data_processor.process_content(raw_content) ######################################## 2
        
        # # raw_content 메모리 해제 (더 이상 필요 없음)
        # del raw_content
        # import gc
        # gc.collect()
        
        # # 3. 마크다운 문서 생성
        # final_rag_document = "\n\n".join(processed_docs)
        
        final_rag_document = markdown_content
        
        # 로컬 환경에서만 마크다운 파일 저장
        is_render = RENDER == "true" or RENDER == "1"
        if not is_render:
            # 로컬 환경: data/md/에 마크다운 저장
            self.save_rag_document_as_md(pdf_path, final_rag_document)
        
        # processed_docs 메모리 해제
        # del processed_docs
        # gc.collect()
        
        # 4. Chunking: 텍스트 청킹 (메모리 효율을 위해 배치로 처리)
        print("🔪 텍스트 청킹 중...")
        chunks = self.text_chunker.chunk_markdown(final_rag_document) ############################################ 3
        
        # final_rag_document 메모리 해제 (청킹 완료 후 더 이상 필요 없음)
        del final_rag_document
        gc.collect()
        
        # [중요]⭐ 모든 청크에 문서 ID(doc_id) 메타데이터 추가
        # 검색(Retrieval) 성능을 높이기 위해 다음 메타데이터 추가하면 좋음
        # 청크 요약, 핵심 키워드, 부모 문서의 제목, 페이지 번호  
        for chunk in chunks:
            chunk.metadata['doc_id'] = str(doc_id)

        chunk_count = len(chunks)
        print(f"✅ 총 {chunk_count}개의 청크가 생성되었습니다.")

        # (아카이브) 청크 저장 - 벡터 DB 저장 전에 올려서, 임베딩이 실패해도 디버깅 자료가 남도록 함
        if archive_prefix:
            self.archive.put_chunks(chunks, archive_prefix)
        
        # 5. Load: 벡터 DB 저장
        if chunks:
            # Render 환경인지 확인 (환경 변수로 구분)
            # CHUNK_BATCH_SIZE가 명시적으로 설정되어 있으면 그 값을 사용
            # 없으면 RENDER 환경 변수를 확인하여 결정
            chunk_batch_size_env = CHUNK_BATCH_SIZE
            
            if chunk_batch_size_env is not None:
                # 명시적으로 설정된 경우
                chunk_batch_size = int(chunk_batch_size_env)
            else:
                # 환경 변수가 없으면 RENDER 환경 확인
                is_render = RENDER == "true" or RENDER == "1"
                chunk_batch_size = 50 if is_render else 0  # Render면 50, 로컬이면 0 (한 번에 처리)
            
            # 배치 크기가 0이거나 청크 개수보다 크면 한 번에 처리 (로컬 환경)
            if chunk_batch_size == 0 or chunk_batch_size >= len(chunks):
                print(f"  💾 청크 저장 중... (한 번에 {len(chunks)}개)")
                self.vector_store.add_documents(chunks) ########################################################### 4
            else:
                # Render 환경: 배치로 나누어 저장 (메모리 효율)
                total_chunks = len(chunks)
                print(f"  💾 청크 배치 저장 중... (배치 크기: {chunk_batch_size})")
                
                for i in range(0, total_chunks, chunk_batch_size):
                    batch = chunks[i:i + chunk_batch_size]
                    print(f"    배치 {i//chunk_batch_size + 1}/{(total_chunks + chunk_batch_size - 1)//chunk_batch_size} 저장 중...")
                    self.vector_store.add_documents(batch)
                    # 배치 저장 후 메모리 해제
                    del batch
                    gc.collect()
            
            # 모든 청크 메모리 해제
            del chunks
            gc.collect()

        return {"skipped": False, "chunk_count": chunk_count}

    def answer_question(self, question: str, doc_id: str = None, model: str = "openai", conversation_history: list = []):
        """
        사용자의 질문에 대해 RAG 방식으로 답변을 생성합니다.
        :param doc_id: 특정 문서에서만 검색하려면 ID 지정
        :param model: 사용할 모델 ("openai" 또는 "gemini")
        :param conversation_history: 이전 대화 내용
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
        # k=10으로 증가하여 표 데이터 등 다양한 형식의 정보도 포함
        filter_condition = {"doc_id": str(doc_id)} if doc_id else None
        related_docs = self.vector_store.search(query=question, k=10, filter=filter_condition) 
        
        if not related_docs:
            print("⚠️ 검색된 문서가 없습니다. 벡터 DB에 데이터가 저장되어 있는지 확인해주세요.")
            return "죄송합니다. 해당 공고문에서 관련 정보를 찾을 수 없습니다. 먼저 공고문을 분석해주세요."

        # 2. Augment: 프롬프트 구성
        context = "\n\n".join([doc.page_content for doc in related_docs])
        
        # 디버깅: 검색된 문서 정보 출력
        print(f"📄 검색된 문서 개수: {len(related_docs)}")
        for i, doc in enumerate(related_docs[:2], 1):  # 처음 2개만 출력
            preview = doc.page_content[:100].replace('\n', ' ')
            print(f"  문서 {i} (미리보기): {preview}...")
        
        # 프롬프트 구성 (더 명확한 지시사항)
        system_prompt = f"""당신은 아파트 청약 공고문을 전문적으로 분석하여 사용자가 해당 청약 자격이 되는지 정보를 제공하는 AI 어시스턴트입니다.

아래 [공고문 내용] 섹션에 있는 정보만을 참고하여 사용자의 질문에 정확하고 상세하게 답변해주세요.

**답변 규칙:**
1. 공고문 내용에 명확히 나와있는 정보만 답변하세요.
2. 정보가 없거나 불확실한 경우 "공고문에 해당 정보가 명시되어 있지 않습니다"라고 답변하세요.
3. 가능한 한 구체적이고 정확한 정보를 제공하세요 (숫자, 날짜, 조건 등).
4. **표 형식의 데이터를 주의 깊게 확인하세요.** 표에서 관련 정보를 찾을 수 있습니다.
   - 표의 헤더와 값을 매칭하여 정확한 정보를 제공하세요.

[공고문 내용]
{context}
"""

        # 대화 히스토리를 텍스트로 변환
        history_text = ""
        if conversation_history:
            for msg in conversation_history[-3:]: # 최근 3턴만 유지
                role = "user" if msg["role"] == 'user' else "AI"
                history_text += f"{role}: {msg['content']}\n"
        
        # 시스템 프롬프트에 히스토리 섹션 추가
        system_prompt += f"\n\n[이전 대화 내용]\n{history_text}"

        # 3. Generate: 답변 생성
        try:
            if model == "gemini":
                # Gemini 모델 사용 (새 SDK: google-genai)
                if not self.genai_client:
                    return "GOOGLE_API_KEY가 설정되지 않아 Gemini를 사용할 수 없습니다."
                
                prompt = f"{system_prompt}\n\n질문: {question}"
                
                # 재시도 로직 (429 에러 대응)
                max_retries = 3
                retry_delay = 2  # 초기 대기 시간 (초)
                
                for attempt in range(max_retries):
                    try:
                        # 새 SDK 사용법
                        response = self.genai_client.models.generate_content(
                            model='gemini-3-pro-preview',
                            contents=prompt,
                            config={
                                'temperature': 0,
                                'max_output_tokens': 2000,  # 500 → 2000으로 증가 (MAX_TOKENS 에러 방지)
                            }
                        )
                        
                        # response.text가 None인 경우 처리
                        if response.text is None:
                            # finish_reason 확인
                            if hasattr(response, 'candidates') and response.candidates:
                                candidate = response.candidates[0]
                                finish_reason = getattr(candidate, 'finish_reason', None)
                                print(f"⚠️ Gemini 응답이 None입니다. finish_reason: {finish_reason}")
                                
                                if finish_reason == 'MAX_TOKENS':
                                    print("⚠️ 최대 토큰 수에 도달했습니다. max_output_tokens를 늘려야 합니다.")
                                    return "죄송합니다. 응답이 너무 길어서 생성하지 못했습니다. 질문을 더 구체적으로 해주세요."
                            
                            if attempt < max_retries - 1:
                                print(f"  재시도합니다... ({attempt + 1}/{max_retries})")
                                time.sleep(2)
                                continue
                            else:
                                return "죄송합니다. Gemini가 응답을 생성하지 못했습니다. 다시 시도해주세요."
                        
                        return f"Gemini 3 Pro: {response.text}"
                        
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
                response = self.openai.chat.completions.create(
                    model="gpt-4o-mini", # 가성비 좋은 모델 사용
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": question}
                    ],
                    temperature=0, # 사실 기반 답변을 위해 0 설정
                    max_tokens=1000,  # 답변 길이 확장 (200 → 500, 긴 답변도 완전히 제공)
                )
                return f"GPT-4o-mini: {response.choices[0].message.content}"
        except Exception as e:
            return f"죄송합니다. 답변 생성 중 오류가 발생했습니다: {e}"

    def clear_database(self):
        """벡터 DB를 초기화합니다."""
        print("🗑️ 벡터 DB 초기화 요청")
        self.vector_store.clear()

    # def save_tables_to_excel(self, all_content, output_path="extracted_tables.xlsx"):
    #     """
    #     (디버깅용) 추출된 표 데이터를 엑셀 파일로 저장
    #     """
    #     with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
    #         table_count = 0
    #         for item in all_content:
    #             if item["type"] == "table":
    #                 table_count += 1
    #                 table_data = item["content"]
                    
    #                 # 데이터가 없거나 유효하지 않으면 패스
    #                 if not table_data: continue
                    
    #                 df = pd.DataFrame(table_data)
    #                 sheet_name = f"Table {table_count}"
    #                 # 시트 이름 길이 제한 (31자)
    #                 if len(sheet_name) > 31: sheet_name = sheet_name[:31]
                    
    #                 try:
    #                     df.to_excel(writer, sheet_name=sheet_name, index=False)
    #                 except Exception as e:
    #                     print(f"엑셀 시트 저장 실패 ({sheet_name}): {e}")

    #     print(f"✅ 표 데이터 엑셀 저장 완료: {output_path}")

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
