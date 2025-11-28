import json
from pathlib import Path
from src.client.api_client import ApplyhomeAPIClient


# 클라이언트 생성
client = ApplyhomeAPIClient()

# 공고 상세 조회
detail = client.get_detail(houseManageNo="2025000486", pblancNo="2025000486")

# 저장 경로 설정 (Path 객체로 변환!)
save_path = Path("data/response/get_detail.json")

# 디렉토리 생성 (없으면)
save_path.parent.mkdir(parents=True, exist_ok=True)

# JSON 파일로 저장
with open(save_path, "w", encoding="utf-8") as f:
    json.dump(detail, f, ensure_ascii=False, indent=2)

print(f"저장 완료: {save_path}")