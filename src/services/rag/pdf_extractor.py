import pdfplumber
import requests
import html2text
from openai import OpenAI
from src.config.config import UPSTAGE_API_KEY, UPSTAGE_BASE_URL
from typing import List, Dict, Any

class PDFExtractor:
    def __init__(self):
        self.client = OpenAI(
            api_key=UPSTAGE_API_KEY,
            base_url=UPSTAGE_BASE_URL
        )

    def html_to_markdown(self, html_string: str):
        """
        HTML -> Markdown 변환
        """
        # 1. 변환기 설정
        h = html2text.HTML2Text()

        # 2. 설정 옵션
        h.ignore_links = False # 링크 유지 여부
        h.bypass_tables = False # False로 해야 표를 마크다운 형식으로 변환함
        h.body_width = 0 # 줄바꿈 방지  

        # 3. 변환 실행
        markdown_string = h.handle(html_string)
        with open("extracted_md.md", "w", encoding="utf-8") as f:
                f.write(markdown_string)

        return markdown_string
    
    
    def extract_html(self, pdf_path: str): 
        """
        Upstage API 사용하여 PDF -> HTML 변환
        """
        headers = {"Authorization": f"Bearer {UPSTAGE_API_KEY}"}
        files = {"document": open(pdf_path, "rb")}
        data = {
            "ocr": "force", 
            "base64_encoding": ["table"], 
            "model": "document-parse"
        }
        response = requests.post(UPSTAGE_BASE_URL, headers=headers, files=files, data=data)
        result = response.json()

        # --- HTML 파일 저장 ---
        html_string = result.get('content', {}).get('html', '')

        if html_string:
            with open("extracted_view.html", "w", encoding="utf-8") as f:
                f.write(html_string)
            print("✅ HTML 파일 저장 완료: extracted_view.html")
        return result


    def extract_content(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        pdfplumber 사용   
        PDF 파일에서 텍스트와 표 데이터를 추출하여 순서대로 반환합니다.
        """
        all_content = []

        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                # 1. 표 추출 설정
                table_settings = {
                    "vertical_strategy": "lines", # 표의 세로 경계
                    "horizontal_strategy": "lines", # 표의 가로 경계
                    "snap_tolerance": 3, # 3포인트. 아주 가까운 위치에 있는 선들을 "같은 선"으로 스냅할 때 허용하는 거리 임계값   
                }
                
                # 2. 표 찾기
                tables = page.find_tables(table_settings=table_settings) 
                
                # 3. 테이블을 위에서 아래로 정렬 (순서 보장) (bbox : (x0, top, x1, bottom) = (왼쪽 경계x, 위쪽 경계y, 오른쪽 경계x, 아래쪽 경계y))
                tables.sort(key=lambda t: t.bbox[1])
                
                last_y = 0 # 마지막으로 처리된 Y 좌표 (커서 역할)
                
                for table in tables:
                    # ---------------------------------------------------------
                    # A. 표 등장 전까지의 텍스트 추출 (Last Y ~ Current Table Top)
                    # ---------------------------------------------------------
                    if table.bbox[1] > last_y:
                        try:
                            # 텍스트 영역 크롭 (페이지 전체 너비 사용)
                            text_box = (0, last_y, page.width, table.bbox[1]) # 테이블의 top 좌표까지 텍스트 추출함  
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
                        
                        last_y = table.bbox[3] # 테이블의 bottom 좌표가 마지막으로 처리된 Y 좌표가 됨  

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

