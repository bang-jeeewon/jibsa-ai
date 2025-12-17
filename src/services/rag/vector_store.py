from langchain_openai import OpenAIEmbeddings
# from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

class VectorStoreService:
    def __init__(self, persist_directory=None):
        """
        VectorStoreService 초기화
        :param persist_directory: None이면 in-memory 모드 (파일 저장 안 함)
        """
        self.persist_directory = persist_directory
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
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
        """청크 리스트를 벡터 DB에 추가"""
        if not chunks:
            print("⚠️ 저장할 청크가 없습니다.")
            return
        
        print(f"💾 벡터 DB 저장 시작... (청크 {len(chunks)}개)")
        self.vector_db.add_documents(chunks)
        print("✅ 벡터 DB 저장 완료!")

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
