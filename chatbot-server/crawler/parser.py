from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import time

def crawl_udok_products():
    url = "https://www.lguplus.com/pogg/category/전체상품"
    print(f"🔍 Crawling {url}")

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    service = Service("/opt/homebrew/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=options)
    driver.get(url)
    time.sleep(3)

    html = driver.page_source
    driver.quit()
    soup = BeautifulSoup(html, "html.parser")

    all_products = []
    product_items = soup.select(".pg-prod-item")
    print(f"🔍 Found {len(product_items)} items")

    for i, item in enumerate(product_items[:5], 1):
        print(f"\n🔎 구독 상품 {i} 디버깅")
        pi_tit = item.select_one(".pi-tit h4 span")
        if pi_tit:
            print("🛍️ 추출된 구독 상품 타이틀:", pi_tit.get_text(strip=True))
        else:
            print("❌ 제목 못 찾음")

    return []
