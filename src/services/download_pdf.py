from pathlib import Path
import img2pdf
from pypdf import PdfReader, PdfWriter
import io
from src.client.download_client import ApplyhomeDownloadClient

class DownloadPdfService: # PDF 다운로드 서비스
    def __init__(self):
        self.download_client = ApplyhomeDownloadClient()
        # 프로젝트 내부 임시 폴더 사용 (서버 재시작 시 삭제됨)
        self.temp_dir = Path("./tmp/pdfs")
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def download_pdf(self, download_url: str, file_name: str) -> str:
        """
        URL에서 PDF를 다운로드하여 임시 파일로 저장 (메모리 기반, 서버 재시작 시 삭제)

        Args:
            download_url: PDF 다운로드 URL
            file_name: 임시 파일명 (ex: 2025000486_2025000486_01.pdf)

        Returns:
            임시 PDF 파일 경로
        """
        # 1. 임시 파일 경로 생성
        file_path = self.temp_dir / file_name
        
        # 2. PDF 다운로드
        content = self.download_client.get_pdf(download_url)

        if not content:
            print(f"PDF 다운로드 실패: {download_url}")
            return None
        
        # 3. 임시 파일에 저장 (서버 재시작 시 자동 삭제됨)
        with open(file_path, "wb") as f:
            f.write(content)
        
        print(f"PDF 임시 저장 완료: {file_path}")
        return str(file_path.absolute())

#     def merge_files_to_pdf(self, file_paths: list[str], output_filename: str) -> str:
#         """
#         실행 : python src/services/download_pdf.py
#         PDF 및 JPG 파일들을 순서대로 병합하여 하나의 PDF 파일로 저장
#         이미지 변환 시 발생하는 메타데이터(썸네일 등) 중복 페이지를 방지합니다.
        
#         Args:
#             file_paths: 병합할 파일들의 절대 경로 리스트 (순서 중요)
#             output_filename: 저장할 결과 파일명
            
#         Returns:
#             저장된 결과 파일의 절대 경로
#         """
#         if not file_paths:
#             print("에러: 병합할 파일 리스트가 비어있습니다.")
#             return None

#         writer = PdfWriter()
        
#         # 첫 번째 파일의 디렉토리를 가져와서 그 위치에 결과 파일 저장
#         first_file_path = Path(file_paths[0])
#         output_dir = first_file_path.parent
#         output_path = output_dir / output_filename
        
#         try:
#             for path_str in file_paths:
#                 path = Path(path_str)
#                 if not path.exists():
#                     print(f"경고: 파일을 찾을 수 없음 - {path}")
#                     continue
                
#                 if path.suffix.lower() in ['.jpg', '.jpeg', '.png']:
#                     # 이미지를 PDF로 변환 (메모리 상에서 처리)
#                     pdf_bytes = img2pdf.convert(str(path))
                    
#                     # 변환된 PDF 데이터에서 첫 번째 페이지만 정확히 추출 (썸네일 등 중복 방지)
#                     img_reader = PdfReader(io.BytesIO(pdf_bytes))
#                     if len(img_reader.pages) > 0:
#                         writer.add_page(img_reader.pages[0])
                        
#                 elif path.suffix.lower() == '.pdf':
#                     # PDF 파일의 모든 페이지 추가
#                     reader = PdfReader(str(path))
#                     for page in reader.pages:
#                         writer.add_page(page)
            
#             with open(output_path, "wb") as f:
#                 writer.write(f)
            
#             writer.close()
#             print(f"병합 완료: {output_path}")
#             return str(output_path.absolute())
            
#         except Exception as e:
#             print(f"병합 중 오류 발생: {e}")
#             return None

# if __name__ == "__main__":
#     # 사용 예시
#     service = DownloadPdfService()
    
#     # 실제 파일 경로 리스트
#     my_files = [
#         r"C:\Users\jwbang\샘플이미지_1.jpg",
#         r"C:\Users\jwbang\샘플이미지_2.jpg",
#         r"C:\Users\jwbang\샘플pdf.pdf",
#     ]
    
#     # 결과 파일명 설정
#     result = service.merge_files_to_pdf(my_files, "merged_file.pdf")
#     if result:
#         print(f"성공! 저장 위치: {result}")
#     else:
#         print("파일 병합에 실패했습니다.")
