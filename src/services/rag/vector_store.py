from langchain_openai import OpenAIEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
# from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from src.config.config import OPENAI_API_KEY, GOOGLE_API_KEY
import time
import random

class VectorStoreService:
    def __init__(self, persist_directory=None, embedding_model="openai"):
        """
        VectorStoreService 초기화
        :param persist_directory: None이면 in-memory 모드 (파일 저장 안 함)
        :param embedding_model: 사용할 임베딩 모델 ("openai" 또는 "gemini")
        """
        self.persist_directory = persist_directory
        
        # 임베딩 모델 선택 (기본값: OpenAI - 더 안정적이고 rate limit이 높음)
        if embedding_model == "gemini":
            # GoogleGenerativeAIEmbeddings에 재시도 로직이 내장되어 있지만, 추가 설정 가능
            self.embeddings = GoogleGenerativeAIEmbeddings(
                model="models/gemini-embedding-001",
                # rate limit 방지를 위한 추가 설정
                request_options={"timeout": 60}  # 타임아웃 설정
            )
            print("🔵 임베딩 모델: Gemini")
        else:
            # 기본값: OpenAI 임베딩 (GPT 선택 시 사용, 더 안정적)
            self.embeddings = OpenAIEmbeddings(
                model="text-embedding-3-small",
                api_key=OPENAI_API_KEY
            )
            print("🟢 임베딩 모델: OpenAI")
        # self.embeddings = HuggingFaceEmbeddings(
        #     model_name="jhgan/ko-sroberta-multitask",
        #     model_kwargs={'device': 'cpu'},
        #     encode_kwargs={'normalize_embeddings': True}
        # )

        # DB 초기화 (persist_directory=None이면 in-memory 모드)
        self.vector_db = Chroma(
            persist_directory=self.persist_directory,  # None이면 메모리만 사용
            embedding_function=self.embeddings,
            collection_name="apt_notices" # 컬렉션 이름 지정
        )

    def add_documents(self, chunks):
        """청크 리스트를 벡터 DB에 추가 (재시도 로직 포함)"""
        if not chunks:
            print("⚠️ 저장할 청크가 없습니다.")
            return
        
        print(f"💾 벡터 DB 저장 시작... (청크 {len(chunks)}개)")
        
        # 재시도 로직 (429 에러 대응)
        max_retries = 3
        retry_delay = 2  # 초기 대기 시간 (초)
        
        for attempt in range(max_retries):
            try:
                # 청크를 작은 배치로 나누어 처리 (rate limit 방지)
                # Gemini API 무료 티어: 분당 약 15-60 요청 제한 (모델에 따라 다름)
                batch_size = 5  # 한 번에 처리할 청크 수 (더 작게)
                for i in range(0, len(chunks), batch_size):
                    batch = chunks[i:i + batch_size]
                    self.vector_db.add_documents(batch)
                    # 배치 간 대기 (rate limit 방지) - 분당 15 요청 기준으로 약 4초 간격
                    if i + batch_size < len(chunks):
                        wait_time = 4.0  # 4초 대기 (분당 15 요청 = 4초당 1 요청)
                        print(f"  배치 {i//batch_size + 1} 완료. {wait_time}초 대기 중... (rate limit 방지)")
                        time.sleep(wait_time)
                
                print("✅ 벡터 DB 저장 완료!")
                return
                
            except Exception as e:
                error_msg = str(e)
                
                # 차원 불일치 에러 처리 (임베딩 모델 변경 시 발생)
                if "dimension" in error_msg.lower() or "expecting embedding" in error_msg.lower():
                    print("⚠️ 임베딩 차원 불일치 감지. 기존 벡터 DB를 초기화합니다...")
                    try:
                        # 기존 컬렉션 삭제
                        self.vector_db.delete_collection()
                        # 새 컬렉션 생성 (현재 임베딩 모델로)
                        self.vector_db = Chroma(
                            persist_directory=self.persist_directory,
                            embedding_function=self.embeddings,
                            collection_name="apt_notices"
                        )
                        print("✅ 벡터 DB 재생성 완료. 다시 시도합니다...")
                        # 재시도 (한 번만)
                        continue
                    except Exception as init_error:
                        print(f"❌ 벡터 DB 재생성 실패: {init_error}")
                        raise
                
                # 429 에러 처리 (할당량 초과)
                elif "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg or "quota" in error_msg.lower():
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
            self.vector_db = Chroma(
                persist_directory=self.persist_directory,  # None이면 in-memory
                embedding_function=self.embeddings,
                collection_name="apt_notices"
            )
            print("✅ 벡터 DB 초기화 완료")
        except Exception as e:
            print(f"❌ 초기화 실패: {e}")
