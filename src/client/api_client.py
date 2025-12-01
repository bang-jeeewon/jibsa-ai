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

    def get_detail(self, houseManageNo, pblancNo, houseSecd="01"):
        """
        공고 상세 정보 조회

        Args:
            houseManageNo: 주택관리번호
            pblancNo: 공고번호
            houseSecd: 주택구분코드

        Returns:
            JSON
        """
        endpoint = f"{self.base_url}/ApplyhomeInfoDetailSvc/v1/getAPTLttotPblancDetail"

        params = {
            "serviceKey": self.api_key,  # 인증키 추가!
            "houseManageNo": houseManageNo,
            "pblancNo": pblancNo,
            "houseSecd": houseSecd,
            "page": 2
        }

        response = self.session.get(endpoint, params=params)

        return response.json()

    