import requests # HTTP 요청 라이브러리
from bs4 import BeautifulSoup # HTML 및 XML 문서 파싱 라이브러리
from src.config.config import PDF_BASE_URL

class ApplyhomeCrawlClient:
    def __init__(self, base_url=None):
        """
        초기화

        Args:
            base_url
        """
        self.base_url = base_url or PDF_BASE_URL
        self.sessiont = requests.Session()
        # applyhome.co.kr이 일반적인 requests.get() 방식의 크롤링을 차단하고 있음
        # applyhome.co.kr은 서버 측에서 특정 조건(예: 브라우저에서 보낸 요청인지, 봇인지)을 확인하여 응답을 다르게 보냄
        # 브라우저 접속 시: 정상적인 HTML 페이지가 로드됨
        # requests 라이브러리로 접속 시: 서버가 요청을 차단하거나 빈 페이지를 반환합니다.
        # 해결책 : User-Agent 헤더 추가
        # 서버를 속여서 Python 스크립트가 실제 웹 브라우저에서 보낸 요청인 것처럼 보이게 하려면 HTTP 요청 헤더에 User-Agent를 추가해야 함
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
        }
    
    # 분양정보 상세조회 response에서 PBLANC_URL로 모집공고문 PDF 다운로드 URL 조회
    def get_pdf_url_by_pblanc_url(self, pblanc_url: str) -> str:
        """
        모집공고문 PDF 다운로드 URL 조회

        Args:
            pblanc_url: 모집공고문 URL
        """
        response = self.sessiont.get(pblanc_url, headers=self.headers)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            btn_tags = soup.select('a.radius_btn')
            if btn_tags:
                for btn in btn_tags:
                    if '모집공고문 보기' in btn.get_text(strip=True):
                        return btn['href']
                        break
            else:
                return None
        else:
            return None
        return None
    
    # # houseManageNo, pblancNo, houseSecd를 이용하여 모집공고문 PDF 다운로드 URL 조회
    # def get_pdf_url_by_params(self, house_manage_no: str, pblanc_no: str, house_secd: str) -> str:
    #     """
    #     모집공고문 PDF 다운로드 URL 조회

    #     Args:
    #         house_manage_no: 주택관리번호
    #         pblanc_no: 공고번호
    #         house_secd: 주택구분코드
        
    #     Returns:
    #         모집공고문 PDF 다운로드 URL
    #     """
    #     endpoint = f"{self.base_url}/ai/aia/selectAPTLttotPblancDetail.do"

    #     params = {
    #         "houseManageNo": house_manage_no,
    #         "pblancNo": pblanc_no,
    #         "houseSecd": house_secd,
    #         "gvPgmId": "AIB01M01"
    #     }

    #     response = self.sessiont.get(endpoint, params=params, headers=self.headers)

    #     if response.status_code == 200:
    #         soup = BeautifulSoup(response.text, 'html.parser')
    #         btn_tags = soup.select('a.radius_btn')
    #         if btn_tags:
    #             for btn in btn_tags:
    #                 if '모집공고문 보기' in btn.get_text(strip=True):
    #                     return btn['href']
    #                     break
    #         else:
    #             return None
    #     else:
    #         return None

    #     return None