import os
import pdfplumber
import pandas as pd
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI


class RAGService:
    def __init__(self, persist_directory='./data/vector_store'):
        """
        1. [데이터 준비 단계] PDF 추출 → 텍스트/표 변환
        ↓
        2. [저장 단계] 텍스트를 벡터(숫자 배열)로 변환(임베딩) → 벡터 DB에 저장
        ↓
        3. [질문 단계] 사용자 질문 → 벡터로 변환(임베딩) → 유사한 문서 검색
        ↓
        4. [답변 단계] 검색된 문서를 LLM의 컨텍스트로 제공 → LLM이 답변 생성
        """
        # 1. 벡터 DB 초기화 (없으면 생성, 있으면 로드)
        # 2. LLM 설정
        # self.persist_directory = persist_directory
        # # API Key는 환경변수 OPENAI_API_KEY에서 자동으로 로드됨
        # self.embeddings = OpenAIEmbeddings()

        # # 벡터 DB 초기화
        # self.vector_db = Chroma(
        #     persist_directory=self.persist_directory,
        #     embedding_functions=self.embeddings
        # )

        # self.llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)
        pass
    
    def extract_(self, pdf_path: str):
        """
        # PDF에서 추출한 데이터 예시

        extracted_data = 
        ## 4-1. 기관추천 특별공급

        | 구분 | 내용 |
        |------|------|
        | 대상자 | 기관에서 추천한 자 |
        | 선정방법 | 추첨 |
        """
        if not os.path.exists(pdf_path):
            print(f"Error: PDF 파일 없음: {pdf_path}")
            return
        
        print(f"PDF 파일 분석중 ... {pdf_path}")
    


    def convert_to_embedding_save(self, extracted_data: str):
        """
        # 추출한 텍스트를 "의미를 나타내는 숫자 배열"로 변환
        text = "기관추천 특별공급 대상자는 기관에서 추천한 자입니다"
        vector = [0.123, -0.456, 0.789, ...]  # 1536차원 벡터 (예시)

        # 벡터 DB에 저장
        vector_db.add({
            "text": "기관추천 특별공급 대상자는 기관에서 추천한 자입니다",
            "vector": [0.123, -0.456, 0.789, ...],
            "metadata": {"section": "4-1. 기관추천 특별공급", "type": "table"}
        })
        """



    def search_similar_documents(self, question: str):
        """
        # 사용자 질문
        question = "기관추천 특별공급 대상자는 누구인가요?"

        # 질문도 벡터로 변환
        question_vector = [0.125, -0.450, 0.790, ...]

        # 벡터 DB에서 가장 유사한 문서 검색 (코사인 유사도 계산)
        similar_docs = vector_db.search(question_vector, top_k=3)
        # 결과: [
        #   "기관추천 특별공급 대상자는 기관에서 추천한 자입니다",
        #   "특별공급은 기관추천, 다자녀가구 등이 있습니다",
        #   ...
        # ]
        """



    def get_answer(self, question: str, similar_docs: list):
        """
        # 검색된 문서를 LLM의 프롬프트에 포함
        prompt = f
        다음 문서를 참고하여 질문에 답변하세요.

        [참고 문서]
        {similar_docs[0]}
        {similar_docs[1]}

        [질문]
        {question}

        [답변]


        # LLM이 이 프롬프트를 받아서 답변 생성
        answer = llm.generate(prompt)
        # → "기관추천 특별공급 대상자는 기관에서 추천한 자입니다."
        """