# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api.chat import router as chat_router
from app.api.ubti import router as ubti_router
from app.api.chat_like import router as chat_like_router
from app.api.usage import router as usage_router  # 🆕 새로 추가
from app.db.database import SessionLocal, engine, Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 테이블 생성
    Base.metadata.create_all(bind=engine)
    print("✅ 데이터베이스 테이블 생성 완료")
    
    yield
    
    print("🔄 애플리케이션 종료 중...")

# FastAPI 인스턴스
app = FastAPI(
    title="LG U+ AI 챗봇 API v2.0",
    description="Enhanced Template-based LangChain System AI with Smart Intent Detection",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc"  # ReDoc
)

# CORS 설정 확장
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite 개발 서버
        "http://localhost:3000",   # React 개발 서버
        "http://127.0.0.1:5173",   # 로컬 IP
        "http://127.0.0.1:3000"    # 로컬 IP
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
app.include_router(chat_router, prefix="/api", tags=["💬 Chat"])
app.include_router(ubti_router, prefix="/api", tags=["🎯 UBTI"])
app.include_router(chat_like_router, prefix="/api", tags=["💜 Likes"])
app.include_router(usage_router, prefix="/api", tags=["📊 Usage"])  # 🆕 새로 추가

# 루트 엔드포인트
@app.get("/", tags=["🏠 Info"])
async def root():
    """API 정보 및 기능 소개"""
    return {
        "message": "🚀 LG U+ AI 챗봇 API v2.0",
        "description": "Enhanced Template-based LangChain System AI",
        "version": "2.0.0",
        "features": [
            "🧠 AI-powered Intent Detection",
            "🛡️ Natural Conversation Guard Rails", 
            "📊 Usage-based Smart Recommendations",
            "🎯 4-step Multi-turn Conversations",
            "💜 Personalized Tone Support (General/Muneoz)",
            "🔧 Cross-platform Compatibility"
        ],
        "endpoints": {
            "chat": "/api/chat",
            "usage_recommend": "/api/usage/recommend",
            "usage_check": "/api/usage/{user_id}",
            "ubti_question": "/api/ubti/question",
            "ubti_result": "/api/ubti/result", 
            "likes_recommend": "/api/chat/likes"
        },
        "docs": "/docs",
        "redoc": "/redoc"
    }

# 헬스체크 엔드포인트
@app.get("/health", tags=["🏠 Info"])
async def health_check():
    """서버 상태 확인"""
    return {
        "status": "healthy",
        "message": "🎉 LG U+ AI 챗봇 서버가 정상 작동 중입니다!",
        "version": "2.0.0",
        "services": {
            "chat": "✅ 활성",
            "intent_detection": "✅ 활성", 
            "usage_analysis": "✅ 활성",
            "ubti": "✅ 활성",
            "conversation_guard": "✅ 활성"
        }
    }

# API 상태 확인
@app.get("/api/status", tags=["🏠 Info"])
async def api_status():
    """API 서비스별 상태 확인"""
    return {
        "api_version": "2.0.0",
        "services": {
            "enhanced_chat": {
                "status": "active",
                "description": "AI 기반 인텐트 감지 + 자연스러운 대화"
            },
            "usage_recommendation": {
                "status": "active", 
                "description": "현재 사용량 기반 스마트 추천"
            },
            "ubti_analysis": {
                "status": "active",
                "description": "4단계 성향 분석 및 맞춤 추천"
            },
            "likes_curation": {
                "status": "active",
                "description": "좋아요 브랜드 기반 구독 큐레이션"
            }
        },
        "ai_models": {
            "intent_classifier": "GPT-4o-mini",
            "conversation_engine": "GPT-4o-mini",
            "recommendation_engine": "Template-based LangChain"
        }
    }

# 개발 환경 전용 디버그 엔드포인트
@app.get("/debug/session/{session_id}", tags=["🔧 Debug"])
async def debug_session(session_id: str):
    """세션 상태 디버깅 (개발용)"""
    from app.utils.redis_client import get_session
    
    session_data = get_session(session_id)
    return {
        "session_id": session_id,
        "data": session_data,
        "has_data": bool(session_data),
        "keys": list(session_data.keys()) if session_data else []
    }

# 에러 핸들링
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return {
        "error": "Not Found",
        "message": "요청하신 엔드포인트를 찾을 수 없습니다.",
        "suggestion": "API 문서를 확인해보세요: /docs"
    }

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return {
        "error": "Internal Server Error", 
        "message": "서버 내부 오류가 발생했습니다.",
        "suggestion": "잠시 후 다시 시도해주세요."
    }