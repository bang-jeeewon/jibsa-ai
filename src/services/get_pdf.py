from pathlib import Path
from src.client.download_client import ApplyhomeDownloadClient

client = ApplyhomeDownloadClient()

# PDF 다운로드
pdf_content = client.get_pdf(downloadUrl="https://static.applyhome.co.kr/ai/aia/getAtchmnfl.do?houseManageNo=2025000486&pblancNo=2025000486&atchmnflSeqNo=1608345&atchmnflSn=1")

if pdf_content:
    # 저장 경로 설정
    save_path = Path("data/pdfs/recruitment_notice.pdf")
    
    # 디렉토리 생성 (없으면)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 파일로 저장
    with open(save_path, "wb") as f:
        f.write(pdf_content)
    
    print(f"PDF 저장 완료: {save_path}")
else:
    print("PDF 다운로드 실패")
