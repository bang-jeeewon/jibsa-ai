from pathlib import Path
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