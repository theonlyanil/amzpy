from amzpy import AmazonScraper
import json

def test_url():
    url = "https://www.amazon.co.jp/%E3%82%BB%E3%82%A4%E3%83%AF-SEIWA-%E3%83%80%E3%83%83%E3%82%B7%E3%83%A5%E3%83%9C%E3%83%BC%E3%83%89%E3%83%88%E3%83%AC%E3%82%A4-IMP193-%E7%BD%AE%E3%81%8F%E3%81%A0%E3%81%91%E7%B0%A1%E5%8D%98%E5%8F%96%E3%82%8A%E4%BB%98%E3%81%91/dp/B0C3C8JGCP/ref=sr_1_3?__mk_ja_JP=%E3%82%AB%E3%82%BF%E3%82%AB%E3%83%8A&crid=JO4JF2AFOJVM&dib=eyJ2IjoiMSJ9.N5buMnPyl30FJw0YgLkBbkyTxygFNXRVVCNOHa2MAsb5hQhEgGY1fsa9EDhVDMud6LFnlYijHg5Y_YptGsVvfhQCHBq6g4Iozxkex9MXndx2eK1nY1Qna6zChkldvwug0242fKU_llDTbZ5YOGyjjYJOjOiexb49LE59ultTZz2BnRuXCtQo6g8WlVOVIspjZQEbmV34xk00uA_GZijG6bdU0AEtbOzhQEbv_Mm98TUZ95tEeY5S_q6tisRR6ofwV03fs9JNv5fooJz3td82UmFKa_TJksUlyUc92u8Dv0k.ECzK_FxTWv4y4WocV0D0JzXVGpid8k6qtawy8BZqJWU&dib_tag=se&keywords=seiwa%2Bjimny&qid=1769952781&s=automotive&sprefix=seiwa%2Bjimn%2Cautomotive%2C599&sr=1-3&th=1"
    
    # Initialize with jp country code
    scraper = AmazonScraper(country_code="co.jp")
    
    print(f"Testing URL: {url}")
    product = scraper.get_product_details(url)
    
    if product:
        print("\nProduct details successfully fetched:")
        print(json.dumps(product, indent=4, ensure_ascii=False))
    else:
        print("\nFailed to fetch product details.")

if __name__ == "__main__":
    test_url()
