from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.chat import router as chat_router
from crawler.parser import crawl_udok_products
from app.db.database import SessionLocal, engine, Base
from app.db.models import Subscription
from app.api.ubti import router as ubti_router

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

# FastAPI 인스턴스
app = FastAPI(lifespan=lifespan)

# CORS 설정 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # 프론트엔드 개발 서버 주소
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
app.include_router(chat_router, prefix="/api")
app.include_router(ubti_router, prefix="/api")