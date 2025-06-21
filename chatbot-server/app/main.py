from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.api.chat import router as chat_router
from app.api.usage import router as usage_router
from app.api.chat_like import router as chat_like_router
from app.api.ubti import router as ubti_router
from app.api.user import router as user_router
from app.db.database import engine, Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 애플리케이션 시작 시 테이블 자동 생성
    Base.metadata.create_all(bind=engine)
    print("데이터베이스 테이블 생성 완료")
    yield
    print("애플리케이션 종료 중...")

app = FastAPI(
    title="4EVER0-AI 챗봇 API",
    description="인텐트 감지 기반 채팅, 요금제·구독 추천, 사용량 분석 기능 제공",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(chat_router, prefix="/api/chat", tags=["채팅"])
app.include_router(usage_router, prefix="/api/chat/usage", tags=["사용량 기반 추천"])
app.include_router(chat_like_router, prefix="/api/chat/likes", tags=["좋아요 기반 추천"])
app.include_router(ubti_router, prefix="/api/ubti", tags=["UBTI 분석"])
app.include_router(user_router, prefix="/api/users", tags=["사용자 관리"])

@app.get("/", tags=["기본정보"])
async def root():
    """API 기본 정보 및 엔드포인트 안내"""
    return {
        "message": "4EVER0-AI 챗봇 API v2.0",
        "description": "채팅, 요금제·구독 추천, 사용량 분석, UBTI 분석을 지원합니다.",
        "version": "2.0.0",
        "endpoints": {
            "채팅 시작": "/api/chat",
            "사용량 추천": "/api/chat/usage/recommend",
            "사용량 조회": "/api/chat/usage/{user_id}",
            "좋아요 추천": "/api/chat/likes",
            "UBTI 질문": "/api/ubti/question",
            "UBTI 결과": "/api/ubti/result",
            "사용자 조회": "/api/users/{user_id}",
        },
    }

@app.get("/health", tags=["기본정보"])
async def health_check():
    """서버 상태 확인용 헬스체크"""
    return {"status": "healthy", "message": "서버가 정상 작동 중입니다.", "version": app.version}

@app.get("/api/status", tags=["기본정보"])
async def api_status():
    """서비스별 상태 정보 반환"""
    return {
        "api_version": app.version,
        "services": {
            "채팅": "active",
            "사용량 기반 추천": "active",
            "좋아요 기반 추천": "active",
            "UBTI 분석": "active",
            "Redis 세션": "active",
        },
    }

# 예외 처리: 404 Not Found
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": "요청하신 엔드포인트를 찾을 수 없습니다.",
            "docs": "/docs"
        },
    )

# 예외 처리: 500 Internal Server Error
@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "서버 내부 오류가 발생했습니다. 관리자에게 문의해주세요."
        },
    )
