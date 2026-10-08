# from langchain_openai import OpenAIEmbeddings
# from langchain_google_genai import GoogleGenerativeAIEmbeddings
# from langchain_huggingface import HuggingFaceEmbeddings
# from langchain_chroma import Chroma
from src.config.config import OPENAI_API_KEY, GOOGLE_API_KEY, RENDER, SUPABASE_DB_URL
import time
import random
import gc

class VectorStoreService:
    def __init__(self, embedding_model="openai"):
        """
        VectorStoreService 초기화 (Supabase pgvector 사용)
        :param embedding_model: 사용할 임베딩 모델 ("openai" 또는 "gemini")
        """
        # from langchain_openai import OpenAIEmbeddings
        # from langchain_google_genai import GoogleGenerativeAIEmbeddings
        # from langchain_chroma import Chroma

        gc.collect()
        print("VectorStoreService 1")

        # 1. 임베딩 라이브러리만 먼저 로드
        if embedding_model == "gemini":
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            gc.collect()
            print("VectorStoreService 2")
            self.embeddings = GoogleGenerativeAIEmbeddings(
                model="models/gemini-embedding-001",
                google_api_key=GOOGLE_API_KEY,  # API 키 명시적으로 전달
                # rate limit 방지를 위한 추가 설정
                request_options={"timeout": 60}  # 타임아웃 설정
            )
        else:
            from langchain_openai import OpenAIEmbeddings
            gc.collect()
            print("VectorStoreService 2.1")
            self.embeddings = OpenAIEmbeddings(
                model="text-embedding-3-small",
                api_key=OPENAI_API_KEY
            )
        gc.collect() # 2. 임시 메모리 청소  

        # 3. Supabase pgvector 연결
        if not SUPABASE_DB_URL:
            raise ValueError("SUPABASE_DB_URL 환경변수가 설정되지 않았습니다.")
        from langchain_postgres import PGVector
        from sqlalchemy import create_engine
        gc.collect()
        print("VectorStoreService 3")
        # 임베딩 모델별로 컬렉션 분리 (OpenAI 1536차원 / Gemini 3072차원 섞이지 않게)

        self.collection_name = f"apt_notices_{embedding_model}"
        self.engine = create_engine(SUPABASE_DB_URL, pool_pre_ping=True, pool_size=2, max_overflow=0)
        self.vector_db = PGVector(
            embeddings=self.embeddings,
            collection_name=self.collection_name,
            connection=self.engine,
            use_jsonb=True
        )
        gc.collect()

        # # 3. 그 다음 Chroma 로드
        # from langchain_chroma import Chroma
        # gc.collect()
        # print("VectorStoreService 3")
        # self.vector_db = Chroma(
        #     embedding_function=self.embeddings,
        #     collection_name="apt_notices" # 컬렉션 이름 지정
        # )
        # gc.collect() # 4. 메모리 청소  
        
        # # 임베딩 모델 선택 (기본값: OpenAI - 더 안정적이고 rate limit이 높음)
        # if embedding_model == "gemini":
        #     # GoogleGenerativeAIEmbeddings에 재시도 로직이 내장되어 있지만, 추가 설정 가능
        #     self.embeddings = GoogleGenerativeAIEmbeddings(
        #         model="models/gemini-embedding-001",
        #         google_api_key=GOOGLE_API_KEY,  # API 키 명시적으로 전달
        #         # rate limit 방지를 위한 추가 설정
        #         request_options={"timeout": 60}  # 타임아웃 설정
        #     )
        #     print("🔵 임베딩 모델: Gemini")
        # else:
        #     # 기본값: OpenAI 임베딩 (GPT 선택 시 사용, 더 안정적)
        #     self.embeddings = OpenAIEmbeddings(
        #         model="text-embedding-3-small",
        #         api_key=OPENAI_API_KEY
        #     )
        #     print("🟢 임베딩 모델: OpenAI")

        # self.embeddings = HuggingFaceEmbeddings(
        #     model_name="jhgan/ko-sroberta-multitask",
        #     model_kwargs={'device': 'cpu'},
        #     encode_kwargs={'normalize_embeddings': True}
        # )
        # gc.collect()
    
    def _exists(self, doc_id):
        """같은 doc_id 청크가 이미 저장돼 있는지 확인 (Chroma의 .get(where=...) 대체)"""
        from sqlalchemy import text
        sql = text("""
            SELECT 1 FROM langchain_pg_embedding e
            JOIN langchain_pg_collection c ON e.collection_id = c.uuid
            WHERE c.name = :name AND e.cmetadata->>'doc_id' = :doc_id
            LIMIT 1
        """)
        with self.engine.connect() as conn:
            return conn.execute(sql, {"name": self.collection_name, "doc_id": doc_id}).first() is not None

    def add_documents(self, chunks):
        """청크 리스트를 벡터 DB에 추가 (재시도 로직 포함)"""
        if not chunks:
            print("⚠️ 저장할 청크가 없습니다.")
            return

        # 중복 방지: 동일 doc_id가 이미 저장돼 있으면 스킵
        try:
            first_meta = getattr(chunks[0], "metadata", {}) or {}
            doc_id = str(first_meta.get("doc_id")) if first_meta.get("doc_id") is not None else None
            if doc_id and self._exists(doc_id):
                print(f"⏩ doc_id={doc_id}는 이미 저장되어 있어 추가하지 않습니다.")
                return
        except Exception as e:
            # 중복 체크 실패 시에는 로그만 남기고 계속 진행
            print(f"⚠️ 중복 확인 실패(계속 진행): {e}")
        
        print(f"💾 벡터 DB 저장 시작... (청크 {len(chunks)}개)")
        
        # 재시도 로직 (429 에러 대응)
        max_retries = 3
        retry_delay = 2  # 초기 대기 시간 (초)
        
        for attempt in range(max_retries):
            try:
                # 배치 분할(Render 메모리 대응)은 rag_service.process_for_rag에서 처리
                self.vector_db.add_documents(chunks)
                
                print("✅ 벡터 DB 저장 완료!")
                return
                
            except Exception as e:
                error_msg = str(e)

                # 429 에러 처리 (할당량 초과)
                if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg or "quota" in error_msg.lower():
                    if attempt < max_retries - 1:
                        # Exponential backoff: 대기 시간 증가
                        wait_time = retry_delay * (2 ** attempt) + random.uniform(0, 1)
                        print(f"⚠️ 할당량 초과 (429). {wait_time:.1f}초 후 재시도... ({attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                    else:
                        print(f"❌ 최대 재시도 횟수 초과. 에러: {e}")
                        raise
                else:
                    # 다른 에러는 즉시 재발생
                    print(f"❌ 벡터 DB 저장 실패: {e}")
                    raise

    def search(self, query, k=3, filter=None):
        """유사한 문서 검색"""
        return self.vector_db.similarity_search(query, k=k, filter=filter)

    def clear(self):
        """벡터 DB 데이터를 모두 삭제합니다."""
        try:
            self.vector_db.delete_collection()
            # 컬렉션 재생성 (삭제 후 다시 쓰기 위해)
            self.vector_db.create_collection()
            print("✅ 벡터 DB 초기화 완료")
        except Exception as e:
            print(f"❌ 초기화 실패: {e}")
