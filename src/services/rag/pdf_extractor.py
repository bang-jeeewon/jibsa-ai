import pdfplumber
from typing import List, Dict, Any

class PDFExtractor:
    def extract_content(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        PDF 파일에서 텍스트와 표 데이터를 추출하여 순서대로 반환합니다.
        """
        all_content = []

        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                # 1. 표 추출 설정
                table_settings = {
                    "vertical_strategy": "lines", 
                    "horizontal_strategy": "lines", 
                    "snap_tolerance": 3,
                }
                
                # 2. 표 찾기
                tables = page.find_tables(table_settings=table_settings) 
                
                # 3. 테이블을 위에서 아래로 정렬 (순서 보장)
                tables.sort(key=lambda t: t.bbox[1])
                
                last_y = 0 # 마지막으로 처리된 Y 좌표 (커서 역할)
                
                for table in tables:
                    # ---------------------------------------------------------
                    # A. 표 등장 전까지의 텍스트 추출 (Last Y ~ Current Table Top)
                    # ---------------------------------------------------------
                    if table.bbox[1] > last_y:
                        try:
                            # 텍스트 영역 크롭 (페이지 전체 너비 사용)
                            text_box = (0, last_y, page.width, table.bbox[1])
                            cropped_page = page.crop(text_box)
                            text = cropped_page.extract_text()
                            
                            if text and text.strip():
                                all_content.append({
                                    "type": "text",
                                    "content": text.strip(),
                                    "page": page.page_number,
                                    "y_start": last_y,
                                    "y_end": table.bbox[1]
                                })
                        except Exception:
                            pass # 영역이 너무 작거나 오류 발생 시 패스

                    # ---------------------------------------------------------
                    # B. 표 추출 및 처리
                    # ---------------------------------------------------------
                    table_data = table.extract()
                    
                    # 표 유효성 검사는 DataProcessor에서 할 수도 있지만, 
                    # 추출 단계에서 명백한 쓰레기를 거르는 게 효율적일 수 있음.
                    # 여기서는 Raw Data를 최대한 보존하고 Processor에게 넘김.
                    
                    if table_data:
                        all_content.append({
                            "type": "table",
                            "content": table_data,
                            "page": page.page_number,
                            "y_start": table.bbox[1],
                            "y_end": table.bbox[3],
                        })
                        
                        last_y = table.bbox[3]

                # ---------------------------------------------------------
                # C. 마지막 표 이후의 남은 텍스트 추출 (Last Y ~ Page Bottom)
                # ---------------------------------------------------------
                if last_y < page.height:
                    try:
                        text_box = (0, last_y, page.width, page.height)
                        cropped_page = page.crop(text_box)
                        text = cropped_page.extract_text()
                        
                        if text and text.strip():
                            all_content.append({
                                "type": "text",
                                "content": text.strip(),
                                "page": page.page_number,
                                "y_start": last_y,
                                "y_end": page.height
                            })
                    except Exception:
                        pass
                        
        return all_content

