

from src.client.crawl_client import ApplyhomeCrawlClient

client = ApplyhomeCrawlClient()

# pdf_url = client.get_pdf_url(houseManageNo="2025000486", pblancNo="2025000486", houseSecd="01")

pblanc_url = "https://www.applyhome.co.kr/ai/aia/selectAPTLttotPblancDetail.do?houseManageNo=2025000486&pblancNo=2025000486&houseSecd=01&gvPgmId=AIB01M01"
pdf_url = client.get_pdf_url_by_pblanc_url(pblanc_url)

print(pdf_url)