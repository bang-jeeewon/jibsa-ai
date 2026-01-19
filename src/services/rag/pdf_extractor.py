# import pdfplumber
import gc
import requests
import html2text
# from openai import OpenAI
from src.config.config import UPSTAGE_API_KEY, UPSTAGE_BASE_URL
from typing import List, Dict, Any
from bs4 import BeautifulSoup

class PDFExtractor:
    def normalize_html_table(self, table_html, debug=False):
        """
        rowspan, colspan이 포함된 HTML 표를 모든 칸이 채워진 2차원 리스트로 변환
        """
        if not table_html:
            if debug: print("DEBUG: table_html is empty")
            return []
        
        if debug: print(f"\n--- DEBUG START: Table ID {table_html.get('id', 'unknown')} ---")
        
        grid = {}
        # 표 내부의 모든 행(tr)을 찾습니다.
        rows = table_html.find_all('tr')
        if debug: print(f"DEBUG: Total rows found: {len(rows)}")

        curr_row = 0
        for row in rows:
            curr_col = 0
            # 현재 행(tr) 바로 아래의 td, th만 찾습니다.
            cells = row.find_all(['td', 'th'], recursive=False)
            if debug: print(f"  DEBUG: Row {curr_row} - Cells found: {len(cells)}")

            for cell in cells:
                # 이미 점유된 칸 건너뛰기
                while (curr_row, curr_col) in grid:
                    curr_col += 1
                
                # 병합 정보 추출 (없으면 1)
                rowspan = int(cell.get('rowspan', 1))
                colspan = int(cell.get('colspan', 1))
                
                # 셀 텍스트 정리 (공백 및 줄바꿈 정리)
                content = " ".join(cell.get_text().split())
                if debug: print(f"    DEBUG: Cell at ({curr_row}, {curr_col}) -> content: '{content[:20]}...', rowspan: {rowspan}, colspan: {colspan}")

                # 그리드의 해당 범위에 내용 채우기
                for r in range(curr_row, curr_row + rowspan):
                    for c in range(curr_col, curr_col + colspan):
                        grid[(r, c)] = content
                
                curr_col += colspan
            curr_row += 1
        
        if not grid:
            if debug: print("DEBUG: Grid is empty after processing")
            return []
        
        # 그리드 크기 측정
        max_row = max(r for r, c in grid.keys()) + 1
        max_col = max(c for r, c in grid.keys()) + 1
        if debug: print(f"DEBUG: Grid normalized to {max_row}x{max_col} matrix")

        # 2차원 리스트 생성
        table_matrix = []
        for r in range(max_row):
            row_data = [grid.get((r, c), "") for c in range(max_col)]
            table_matrix.append(row_data)
        
        if debug: print("--- DEBUG END ---\n")
        return table_matrix


    def matrix_to_markdown(self, matrix):
        """
        2차원 리스트를 마크다운 표 문자열로 변환
        """
        if not matrix:
            return ""

        lines = []
        for i, row in enumerate(matrix):
            # 특수 기호(|)가 데이터에 있을 경우 대비하여 치환
            clean_row = [str(cell).replace("|", "\\|") for cell in row]
            lines.append("| " + " | ".join(clean_row) + " |")
            
            # 헤더 아래 구분선 (첫 번째 행 직후)
            if i == 0:
                lines.append("|" + "---| " * len(row) + "|")
        
        return "\n" + "\n".join(lines) + "\n"


    def html_to_markdown(self, html_string: str):
        """
        HTML 전체를 마크다운으로 변환하되, 표는 정규화 로직 적용
        """
        soup = BeautifulSoup(html_string, 'html.parser')
        tables = soup.find_all('table')

        # 1. 테이블을 먼저 처리하여 마크다운으로 변환해둠
        normalized_tables = []
        for i, table in enumerate(tables):
            # 4번째 테이블(인덱스 3)만 디버깅 로그 출력
            matrix = self.normalize_html_table(table, debug=(i == 3))
            md_table = self.matrix_to_markdown(matrix)
            normalized_tables.append(md_table)

            # 2. HTML에서 테이블을 아주 단순한 고유 마커로 치환
            # html2text가 절대 건드리지 못할 형태의 텍스트 사용
            placeholder = soup.new_tag("p")
            placeholder.string = f"REPLACE_ME_TABLE_{i}"
            table.replace_with(placeholder)
        
        # 3. 테이블이 제거된 나머지 본문을 마크다운으로 변환
        h = html2text.HTML2Text()
        h.bypass_tables = True  # 테이블 무시
        h.ignore_links = False
        h.body_width = 0        # 자동 줄바꿈 방지
        markdown_result = h.handle(str(soup))
        
        # 4. 마커를 실제 정규화된 마크다운 표로 교체
        for i, md_table in enumerate(normalized_tables):
            # html2text 변환 결과에 따라 마커 앞뒤에 공백이 생길 수 있으므로 유연하게 처리
            target = f"REPLACE_ME_TABLE_{i}"
            markdown_result = markdown_result.replace(target, md_table)
            
        gc.collect()
        
        # 결과 확인용 저장
        with open("extracted_md.md", "w", encoding="utf-8") as f:
            f.write(markdown_result)

        return markdown_result
    

    def extract_html_by_document_digitization(self, pdf_path: str): 
        """
        Upstage document-digitization API 사용하여 PDF -> HTML 변환
        """
        headers = {"Authorization": f"Bearer {UPSTAGE_API_KEY}"}
        files = {"document": open(pdf_path, "rb")}
        data = {
            "ocr": "force", # PDF가 종이를 스캔한 이미지PDF 이어도 어떤 형태든 상관없이 이미지를 분석해서 글자를 읽어냄. 그자가 그림으로 되어 있는 복잡한 표나 로고 근처의 글자도 놓치지 않고 꼼꼼하게 읽음
            "base64_encoding": ["table"], # 표(Table)은 이미지(Base64 문자열)로도 같이 전송. Upstage는 표를 HTML 텍스트로도 주지만, 원본 표 모양 그대로 그림 형태로 보관하고 싶을 때 사용.
            "model": "document-parse", # 사용할 AI 모델의 이름 
            "output_formats": ["html"], # 명시적으로 출력 형식 요청 
            # "mode": "enhanced" # document-parse-nightly 모델에서 된다고 했는데, server error로 안됨. containing complex tables, images, charts, and other advanced visual elements.
        }
        response = requests.post(UPSTAGE_BASE_URL, headers=headers, files=files, data=data)
        result = response.json()

        # --- HTML 파일 저장 ---
        html_string = result.get('content', {}).get('html', '')
        markdown_string = result.get('content', {}).get('markdown', '')
        print("markdown_string:",markdown_string[:100])

        # return markdown_string

        if html_string:
            with open("extracted_view.html", "w", encoding="utf-8") as f:
                f.write(html_string)
            print("✅ HTML 파일 저장 완료: extracted_view.html")
        return html_string


    # def encode_pdf_to_base64(self, pdf_path: str):
    #     """
    #     PDF 파일을 Base64 인코딩
    #     """
    #     with open(pdf_path, "rb") as f:
    #         # 1. PDF의 이진 데이터를 읽음
    #         pdf_bytes = f.read()
    #         # 2. 이진 데이터를 Base64 텍스트로 변환
    #         base64_data = base64.b64encode(pdf_bytes).decode('utf-8')
    #         return base64_data


    # def extract_html_by_information_extraction(self, pdf_path: str):
    #     """
    #     Upstage information-extraction API 사용하여 PDF -> JSON 변환
    #     """
    #     client = OpenAI(
    #         api_key=UPSTAGE_API_KEY,
    #         base_url=UPSTAGE_BASE_URL
    #     )
    #     base64_data = self.encode_pdf_to_base64(pdf_path)
    #     response = client.chat.completions.create(
    #         model="information-extract",
    #         messages=[
    #             {
    #                 "role": "user",
    #                 "content": [
    #                     {
    #                         "type": "image_url",
    #                         "image_url": {"url": f"data:application/pdf;base64,{base64_data}"}
    #                     }
    #                 ]
    #             }
    #         ],
    #         response_format={
    #             "type": "json_schema",
    #             "json_schema": {
    #                 "name": "document_schema",
    #                 "schema": {
    #                     "type": "object",
    #                     "properties": {
    #                         "document_title": {
    #                             "type": "string",
    #                             "description": "전체 공고명"
    #                         },
    #                         "h1_sections": {
    #                             "type": "array",
    #                             "description": "대제목 단위 (예: I. 공통 유의사항)",
    #                             "items": {
    #                                 "type": "object",
    #                                 "properties": {
    #                                     "h1_title": { "type": "string" },
    #                                     "h2_sections": {
    #                                         "type": "array",
    #                                         "description": "중제목 단위 (예: IV-1. 기관추천)",
    #                                         "items": {
    #                                             "type": "object",
    #                                             "properties": {
    #                                                 "h2_title": { "type": "string" },
    #                                                 "h3_sections": {
    #                                                     "type": "array",
    #                                                     "description": "소제목 및 상세 내용 (예: 신청자격, 선정방법)",
    #                                                     "items": {
    #                                                         "type": "object",
    #                                                         "properties": {
    #                                                             "h3_title": { "type": "string" },
    #                                                             "content": { "type": "string" },
    #                                                         }
    #                                                     }
    #                                                 }
    #                                             }
    #                                         }
    #                                     }
    #                                 }
    #                             }
    #                         }
    #                     }
    #                 }
    #             }
    #         },
    #         extra_body={ 
    #             "mode": "enhanced"
    #         } 
    #     )
    #     result = response.choices[0].message.content
    #     return result


    def extract_content(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        pdfplumber 사용   
        PDF 파일에서 텍스트와 표 데이터를 추출하여 순서대로 반환합니다.
        """
        import pdfplumber
        gc.collect()
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
