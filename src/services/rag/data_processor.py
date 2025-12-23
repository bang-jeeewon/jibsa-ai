import re
from tabulate import tabulate
from typing import List, Any

class DataProcessor:
    def __init__(self):
        self.known_titles = {
            "※ 단지 주요정보": "1",
            "공통 유의사항": "1",
            "단지 유의사항": "1",
            "공급대상 및 공급금액": "1",
            "공급내역 및 공급금액": "1",
            # "특별공급": "1",
            "기관추천 특별공급": "2",
            "다자녀가구 특별공급": "2",
            "신혼부부 특별공급": "2",
            "노부모부양 특별공급": "2",
            "생애최초 특별공급": "2",
            # "일반공급": "1",
            "청약신청 및 당첨자 발표 안내": "1",
            "당첨자 및 예비입주자": "1",
            "당첨자 및 예비입주자 계약 체결": "1",
            # "추가": "1",
        }

    def process_content(self, raw_content: List[dict]) -> List[str]:
        """
        추출된 Raw Content를 정제하고 마크다운 형식으로 변환합니다.
        """
        processed_docs = []
        
        for item in raw_content:
            item_type = item["type"]
            content = item["content"]
            
            if item_type == "text":
                # 1. 텍스트 정제 및 마크다운 변환
                clean_text = self._clean_text(content)
                markdown_text = self._convert_titles_to_markdown(clean_text)
                processed_docs.append(markdown_text)
                
            elif item_type == "table":
                # 2. 표 정제 및 마크다운 변환
                clean_table = self._clean_table(content)
                
                # 정제 후 유효한 표인지 확인
                if self._is_valid_table(clean_table):
                    # 제목 추가 (임시)
                    # processed_docs.append("### **표 제목**")
                    # processed_docs.append(f"### {item['page']}page - {item['y_start']} ~ {item['y_end']}")
                    
                    # 마크다운 표로 변환
                    markdown_table = self._convert_list_to_markdown_table(clean_table)
                    # markdown_table = f"```{clean_table}```"
                    processed_docs.append(markdown_table)
        
        return processed_docs

    def _clean_text(self, text: str) -> str:
        """페이지 번호 등 불필요한 텍스트 제거"""
        if not text: return ""
        # 페이지 번호 제거 (- 1 -)
        text = re.sub(r'-\s*\d+\s*-', '', text)
        return text

    def _convert_titles_to_markdown(self, text: str) -> str:
        """알려진 제목을 마크다운 헤더로 변환"""
        if not text: return ""
        
        for title, level in self.known_titles.items():
            if title in text:
                header_prefix = "#" * int(level) + " "
                # 중복 적용 방지
                if header_prefix + title not in text:
                    text = text.replace(title, header_prefix + title)
        return text

    def _clean_table(self, table_data: List[List[Any]]) -> List[List[Any]]:
        """표 데이터 정제 (빈 행 제거, 병합 처리 등)"""
        if not table_data: return []

        cleaned_data = []
        
        # 1. 수평 병합 처리 (왼쪽 -> 오른쪽)
        for row in table_data:
            new_row = list(row)
            for i in range(1, len(new_row)):
                if new_row[i] is None:
                    new_row[i] = new_row[i-1] # 왼쪽 셀 값으로 채우기
                if new_row[0] is None:
                    new_row[0] = ""
            # 한 행을 한 번만 추가해야 중복이 생기지 않음
            cleaned_data.append(new_row)
        
        # # 2. 수직 병합 처리 (위 -> 아래)
        # if cleaned_data:
        #     num_cols = len(cleaned_data[0])
        #     for col_idx in range(num_cols):
        #         last_value = None
        #         for row_idx in range(len(cleaned_data)):
        #             cell = cleaned_data[row_idx][col_idx]
        #             if cell is not None and str(cell).strip():
        #                 last_value = cell
        #             elif last_value is not None:
        #                 # 위쪽 셀 값으로 채우기
        #                 cleaned_data[row_idx][col_idx] = last_value
            
        # 3. 위아래 불필요한 텍스트 행(Garbage Row) 제거
        while cleaned_data and self._is_garbage_row(cleaned_data[0]):
            cleaned_data.pop(0)
        while cleaned_data and self._is_garbage_row(cleaned_data[-1]):
            cleaned_data.pop(-1)
            
        return cleaned_data

    def _is_garbage_row(self, row: List[Any]) -> bool:
        """행이 표의 데이터가 아니라 불필요한 텍스트인지 판별"""
        # 값이 있는 칸만 골라냄
        valid_cells = [cell for cell in row if cell and str(cell).strip()]
        
        if len(valid_cells) > 1: return False # 값이 2개 이상이면 데이터
        if len(valid_cells) == 0: return True # 빈 행이면 삭제
        
        text = str(valid_cells[0]).strip()
        # 길이가 너무 길거나 특수문자로 시작하면 삭제
        if len(text) > 20: return True
        if text.startswith(('※', '■', '-', '주)', '*')): return True
        
        return False

    def _is_valid_table(self, table_data: List[List[Any]]) -> bool:
        """표가 유효한지 검사 (행/열 개수 등)"""
        if not table_data: return False
        if len(table_data) < 2: return False # 헤더만 있거나 너무 작음
        
        # 1열짜리 표는 텍스트 박스일 확률이 높으므로 제외 (선택 사항)
        if len(table_data[0]) < 2: return False
        
        return True

    def _convert_list_to_markdown_table(self, table_data: List[List[Any]]) -> str:
        """2차원 리스트를 마크다운 표 문자열로 변환"""
        if not table_data: return ""
        try:
            return tabulate(table_data, headers="firstrow", tablefmt="github")
        except Exception:
            return str(table_data)

