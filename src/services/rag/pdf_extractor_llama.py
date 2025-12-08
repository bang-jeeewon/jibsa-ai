from typing import List, Dict, Any
import nest_asyncio
from llama_parse import LlamaParse
from src.config.config import LLAMA_CLOUD_API_KEY

# LlamaParse는 내부적으로 asyncio를 사용하므로, 
# Flask 같은 환경에서 이벤트 루프 충돌을 방지하기 위해 적용
nest_asyncio.apply()

class PDFExtractorLlama:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or LLAMA_CLOUD_API_KEY
        
        if not self.api_key:
            print("Warning: LLAMA_CLOUD_API_KEY is not set. LlamaParse extraction will fail.")
        
        self.parser = LlamaParse(
            api_key=self.api_key,
            result_type="markdown",  # RAG에 최적화된 마크다운 형식
            num_workers=4,           # 병렬 처리
            verbose=True,
            language="ko",           # 한국어 문서 최적화
        )

    def extract_content(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        LlamaParse를 사용하여 PDF에서 마크다운 데이터를 추출합니다.
        LlamaParse는 구조화된 마크다운을 반환하므로 이를 청크로 변환하여 반환합니다.
        """
        try:
            # LlamaParse 실행 (동기 방식 래퍼 사용)
            documents = self.parser.load_data(pdf_path)
            
            formatted_content = []
            
            for i, doc in enumerate(documents):
                # LlamaParse는 보통 파일 단위로 처리되지만, 설정에 따라 분할될 수 있음
                # 메타데이터에서 페이지 정보를 찾거나, 없으면 인덱스 기반으로 처리
                page_num = doc.metadata.get("page_label", i + 1)
                
                if doc.text and doc.text.strip():
                    formatted_content.append({
                        "type": "llama_markdown",
                        "content": doc.text,
                        "page": page_num,
                        "metadata": doc.metadata
                    })
            
            return formatted_content
            
        except Exception as e:
            print(f"Error in LlamaParse extraction: {e}")
            return []

