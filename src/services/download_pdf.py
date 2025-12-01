from pathlib import Path
from src.client.download_client import ApplyhomeDownloadClient

class DownloadPdfService: # PDF 다운로드 서비스
    def __init__(self):
        self.download_client = ApplyhomeDownloadClient()
        self.save_dir = Path("data/pdfs")
        self.save_dir.mkdir(parents=True, exist_ok=True)

    def download_pdf(self, download_url: str, file_name: str) -> str:
        """
        URL에서 PDF를 다운로드하여 로컬에 저장

        Args:
            pdf_url: PDF 다운로드 URL
            file_name: 저장 파일명 (ex: 2025000486_2025000486_01.pdf)

        Returns:
            PDF 저장 경로
        """

        # 1. 이미 저장된 파일인지 확인 (캐싱)
        file_path = self.save_dir / file_name
        if file_path.exists():
            print(f"이미 저장된 파일: {file_path}")
            return str(file_path.absolute())
        
        # 2. PDF 다운로드
        content = self.download_client.get_pdf(download_url)

        if not content:
            print(f"PDF 다운로드 실패: {download_url}")
            return None
        
        # 3. PDF 로컬 저장
        with open(file_path, "wb") as f:
            f.write(content)
        
        print(f"PDF 저장 완료: {file_path}")
        return str(file_path.absolute())