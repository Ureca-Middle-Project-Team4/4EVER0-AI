from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from urllib.parse import quote
import time
import os

FLAG_PATH = ".crawler_once_done"

CATEGORY_URLS = {
    "전체상품": "전체상품",
    "OTT_뮤직": "ott-뮤직",
    "도서_아티클": "도서-아티클",
    "자기개발": "자기개발",
    "식품": "식품",
    "생활_편의": "생활-편의",
    "패션_뷰티": "패션-뷰티",
    "키즈": "키즈",
    "반려동물": "반려동물"
}

def crawl_udok_products():
    if os.path.exists(FLAG_PATH):
        print("✅ 이미 크롤링 완료됨. 재실행 안함.")
        return []

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    service = Service("/opt/homebrew/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=options)

    all_products = []

    for display_name, slug in CATEGORY_URLS.items():
        url = f"https://www.lguplus.com/pogg/category/{slug}"
        print(f"🔍 Crawling {url}")

        driver.get(url)
        time.sleep(3)
        soup = BeautifulSoup(driver.page_source, "html.parser")

        product_items = soup.select(".pg-prod-item")
        print(f"📦 {display_name}: {len(product_items)} items found")

        for item in product_items:
            title_el = item.select_one(".pi-tit h4 span")
            if not title_el:
                continue
            title_text = title_el.get_text(strip=True)

            desc_el = item.select_one(".pi-stit")
            description = desc_el.get_text(strip=True) if desc_el else ""

            img_el = item.select_one("img")
            image_url = img_el["src"] if img_el and img_el.has_attr("src") and (".png" in img_el["src"] or ".jpg" in img_el["src"]) else ""
            if image_url and not image_url.startswith("http"):
                image_url = "https://www.lguplus.com" + image_url

            encoded_title = quote(title_text.strip().replace(" ", "-"))
            detail_url = f"https://www.lguplus.com/pogg/product/{encoded_title}" if title_text else ""

            price_el = item.select_one(".p-prcs .prc")
            price = price_el.get_text(strip=True).replace("월", "").strip() if price_el else ""

            all_products.append({
                "title": title_text,
                "description": description,
                "image_url": image_url,
                "detail_url": detail_url,
                "category": display_name,
                "price": price
            })

            print("✅ 파싱 완료:", title_text, description, image_url, detail_url, display_name, price)

    driver.quit()

    with open(FLAG_PATH, "w") as f:
        f.write("done")

    return all_products