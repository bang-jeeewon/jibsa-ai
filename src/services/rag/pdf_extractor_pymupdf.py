import pymupdf4llm
from typing import List, Dict, Any

class PDFExtractorPyMuPDF:
    def extract_content(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        PyMuPDF4LLM을 사용하여 PDF에서 마크다운 데이터를 추출합니다.
        page_chunks=True 옵션을 사용하여 페이지별 마크다운 청크를 반환합니다.
        """
        try:
            # page_chunks=True returns a list of dicts with keys: metadata, text, tables, images, etc.
            md_data = pymupdf4llm.to_markdown(pdf_path, page_chunks=True)
            
            formatted_content = []
            for item in md_data:
                # metadata page number is usually 1-based in pymupdf4llm output? Let's check.
                # Usually libraries use 0-based or 1-based. PyMuPDF is 0-based.
                # pymupdf4llm output metadata usually matches source.
                metadata = item.get("metadata", {})
                page_num = metadata.get("page", 0) + 1 # Convert to 1-based for consistency
                
                text = item.get("text", "")
                
                # 이미 마크다운이므로 별도 정제 없이 바로 사용할 수 있도록 타입 지정
                if text.strip():
                    formatted_content.append({
                        "type": "markdown_chunk",
                        "content": text,
                        "page": page_num,
                        "tables": item.get("tables", []), # 테이블 데이터도 포함될 수 있음
                        "images": item.get("images", [])
                    })
            
            return formatted_content
            
        except Exception as e:
            print(f"Error in PyMuPDF4LLM extraction: {e}")
            return []

