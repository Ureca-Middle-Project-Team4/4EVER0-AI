from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import time
import os

# 크롤링 1회만 실행되도록 체크 파일 설정
FLAG_PATH = ".crawler_once_done"

def crawl_udok_products():
    if os.path.exists(FLAG_PATH):
        print("이미 크롤링 완료됨. 재실행 안함.")
        return []

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

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    all_products = []
    product_items = soup.select(".pg-prod-item")
    for item in product_items:
        title_el = item.select_one(".pi-tit h4 span")
        if not title_el:
            continue
        title_text = title_el.get_text(strip=True)

        desc_el = item.select_one(".pi-stit")
        description = desc_el.get_text(strip=True) if desc_el else ""

        img_el = item.select_one("img")
        image_url = img_el["src"] if img_el and img_el.has_attr("src") else ""

        detail_el = item.select_one("a")
        detail_url = "https://www.lguplus.com" + detail_el["href"] if detail_el and detail_el.has_attr("href") else ""

        tags_el = item.select(".tag")
        tags = ", ".join(tag.get_text(strip=True) for tag in tags_el)

        category = item.get("data-ec-category") or "unknown"
        category = category.replace("/", "_")

        all_products.append({
            "title": title_text,
            "description": description,
            "image_url": image_url,
            "detail_url": detail_url,
            "category": category,
            "tags": tags
        })

    # 크롤링 1회 완료 플래그 생성
    with open(FLAG_PATH, "w") as f:
        f.write("done")

    return all_products
