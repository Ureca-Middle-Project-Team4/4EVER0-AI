from fastapi import FastAPI
from app.api.chat import router as chat_router
from app.api.recommend import router as recommend_router
from crawler.parser import crawl_udok_products
from app.db.database import SessionLocal
from app.db.models import Subscription
from sqlalchemy.exc import IntegrityError

app = FastAPI()

# GPT chat API
app.include_router(chat_router, prefix="/chat")

# 크롤링 및 추천 API 추가
app.include_router(recommend_router, prefix="/api")

# 서버 실행 시 유독 상품 크롤링 + DB 저장
@app.on_event("startup")
def load_udok_products_on_startup():
    db = SessionLocal()
    products = crawl_udok_products()
    for p in products:
        if not db.query(Subscription).filter_by(title=p["title"]).first():
            try:
                db.add(Subscription(**p))
            except IntegrityError:
                pass
    db.commit()
    db.close()
