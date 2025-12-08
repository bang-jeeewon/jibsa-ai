import requests
from src.config.config import API_BASE_URL, API_KEY

class ApplyhomeAPIClient:
    def __init__(self, base_url=None, api_key=None):
        """
        초기화

        Args:
            base_url
            api_key
        """
        self.base_url = base_url or API_BASE_URL
        self.api_key = api_key or API_KEY
        self.session = requests.Session()

    def get_detail(self, houseDtlSecd="01", start_date=None, end_date=None, page=1):
        """
        공고 상세 정보 조회
        
        Args:
            houseDtlSecd: 주택구분코드 (01: 민영, 03: 국민)
            start_date: 검색 시작일 (YYYY-MM-DD)
            end_date: 검색 종료일 (YYYY-MM-DD)
            page: 페이지 번호
        """
        endpoint = f"{self.base_url}/ApplyhomeInfoDetailSvc/v1/getAPTLttotPblancDetail"

        params = {
            "serviceKey": self.api_key,  # 인증키 추가!
            # "houseManageNo": houseManageNo,
            # "pblancNo": pblancNo,
            "cond[HOUSE_DTL_SECD::EQ]": houseDtlSecd,
            "page": page,
            "perPage": 100
        }

        # 날짜 필터 추가 (모집공고일 기준)
        if start_date:
            params["cond[RCRIT_PBLANC_DE::GTE]"] = start_date
        
        if end_date:
            params["cond[RCRIT_PBLANC_DE::LTE]"] = end_date

        # [디버깅] 요청 로그 출력
        print("\n" + "="*50)
        print(f"API 요청 시작")
        print(f"URL: {endpoint}")
        print(f"Params: {params}")
        print("="*50 + "\n")

        response = self.session.get(endpoint, params=params)

        print(f"응답 코드: {response.status_code}")

        return response.json()

    