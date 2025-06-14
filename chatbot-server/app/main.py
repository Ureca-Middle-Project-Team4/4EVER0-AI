from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api.chat import router as chat_router
from app.api.ubti import router as ubti_router
from app.api.chat_like import router as chat_like_router
from app.db.database import SessionLocal, engine, Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 테이블 생성
    Base.metadata.create_all(bind=engine)

    # 크롤링 제거
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
app.include_router(chat_like_router, prefix="/api")  # 라우터 등록