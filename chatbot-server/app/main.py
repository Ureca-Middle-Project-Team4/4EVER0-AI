from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.api.chat import router as chat_router
from app.api.recommend import router as recommend_router
from crawler.parser import crawl_udok_products
from app.db.database import SessionLocal, engine, Base
from app.db.models import Subscription

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 테이블 생성
    Base.metadata.create_all(bind=engine)

    # 크롤링 + 저장
    db = SessionLocal()
    products = crawl_udok_products()
    if not products:
        print("저장할 상품 없음 (크롤링 실패 또는 스킵)")
    else:
        for p in products:
            try:
                exists = db.query(Subscription).filter_by(title=p["title"], category=p["category"]).first()
                if exists:
                    print(f"⚠이미 존재: {p['title']}")
                    continue
                db.add(Subscription(**p))
                print(f"저장 성공: {p['title']}")
            except Exception as e:
                print(f"저장 실패: {p['title']}, 이유: {e}")
        db.commit()
    db.close()
    yield

# lifespan 지정
app = FastAPI(lifespan=lifespan)

app.include_router(chat_router, prefix="/chat")
app.include_router(recommend_router, prefix="/api")
