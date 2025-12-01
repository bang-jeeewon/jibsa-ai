from src.client.crawl_client import ApplyhomeCrawlClient

# client = ApplyhomeCrawlClient()
# # houseManageNo - 주택관리 번호호
# # houseSecd - 주택구분코드 - 01: APT, 09: 민간사전청약, 10: 신혼희망타운
# # pblancNo - 공고번호
# # gvPgmId - 
# pblanc_url = "https://www.applyhome.co.kr/ai/aia/selectAPTLttotPblancDetail.do?houseManageNo=2025000486&pblancNo=2025000486&houseSecd=01&gvPgmId=AIB01M01"
# pdf_url = client.get_pdf_url_by_pblanc_url(pblanc_url)

class CrawlUrlService: # 모집공고문 URL 크롤링 서비스
    def __init__(self):
        self.crawl_client = ApplyhomeCrawlClient()

    def crawl_url(self, pblanc_url: str) -> str:
        """
        모집공고문 상세 URL에서 PDF 다운로드 URL 크롤링

        Args:
            pblanc_url: 모집공고문 상세 URL

        Returns:
            모집공고문 PDF 다운로드 URL
        """
        print(pblanc_url)
        return self.crawl_client.get_pdf_url_by_pblanc_url(pblanc_url)
