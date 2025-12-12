import requests

class ApplyhomeDownloadClient:
    def __init__(self):
        """
        초기화
        """
    
    def get_pdf(self, downloadUrl):
        """

        Args:
            downloadUrl: 다운로드 URL   (ApplyhomeCrawlClient.get_pdf_url_by_pblanc_url() return value)
        """
        response = requests.get(downloadUrl)
        if response.status_code == 200:
            return response.content
        else:
            return None