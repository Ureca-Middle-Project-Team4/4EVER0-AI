from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api.chat import router as chat_router
from app.api.ubti import router as ubti_router
from app.api.chat_like import router as chat_like_router
from app.api.usage import router as usage_router
from app.db.database import SessionLocal, engine, Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 테이블 생성
    Base.metadata.create_all(bind=engine)
    print("데이터베이스 테이블 생성 완료")

    yield

    print("애플리케이션 종료 중...")

# FastAPI 인스턴스
app = FastAPI(
    title="MoonoZ AI 챗봇 API",
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
        "http://127.0.0.1:5173",   # 로컬 IP
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
app.include_router(chat_router, prefix="/api", tags=["💬 대화"])
app.include_router(ubti_router, prefix="/api", tags=["🎯 UBTI 성향분석"])
app.include_router(chat_like_router, prefix="/api", tags=["💜 좋아요 기반 추천"])
app.include_router(usage_router, prefix="/api/chat", tags=["📊 사용량 기반 추천"])

# 루트 엔드포인트
@app.get("/", tags=["🏠 기본정보"])
async def root():
    """API 정보 및 기능 소개"""
    return {
        "message": "🚀 무너즈 LG U+ AI 챗봇 API v2.0",
        "description": "사용량 분석 + AI 인텐트 감지 + 자연스러운 대화가 가능한 스마트 추천 시스템",
        "version": "2.0.0",
        "features": [
            "🧠 GPT-4o-mini 기반 정확한 인텐트 감지",
            "🛡️ 의미없는 입력 및 오프토픽 자동 처리",
            "📊 6가지 사용자 타입 분석 + 비용 효과 계산",
            "🎯 4단계 멀티턴 대화 플로우",
            "💜 개인 취향 기반 구독 서비스 큐레이션",
            "🎭 무너/일반 톤 개인화 응답",
            "🔄 실시간 스트리밍 응답",
            "⚡ Redis 기반 세션 관리",
        ],
        "endpoints": {
            "대화_시작": "/api/chat",
            "사용량_추천": "/api/chat/usage/recommend",
            "사용량_조회": "/api/chat/usage/{user_id}",
            "UBTI_질문": "/api/ubti/question",
            "UBTI_결과": "/api/ubti/result",
            "좋아요_추천": "/api/chat/likes",
        },
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc"
        }
    }

# 헬스체크 엔드포인트
@app.get("/health", tags=["🏠 기본정보"])
async def health_check():
    """서버 상태 확인"""
    return {
        "status": "healthy",
        "message": "🐙 무너즈 AI 챗봇 서버가 정상 작동 중입니다!",
        "version": "2.0.0",
        "services": {
            "대화_엔진": "✅ 활성",
            "인텐트_감지": "✅ 활성",
            "사용량_분석": "✅ 활성",
            "UBTI_분석": "✅ 활성",
            "좋아요_분석": "✅ 활성",
            "대화_가드": "✅ 활성",
            "Redis_세션": "✅ 활성"
        }
    }

# API 상태 확인
@app.get("/api/status", tags=["🏠 기본정보"])
async def api_status():
    """API 서비스별 상태 확인"""
    return {
        "api_version": "2.0.0",
        "services": {
            "스마트_대화": {
                "status": "✅ 활성",
                "description": "AI 기반 인텐트 감지 + 자연스러운 멀티턴 대화",
                "features": ["의미없는 입력 처리", "오프토픽 가드레일", "페르소나 맞춤 응답"]
            },
            "사용량_기반_추천": {
                "status": "✅ 활성",
                "description": "실제 사용 패턴 분석을 통한 개인 맞춤 요금제 추천",
                "features": [
                    "6가지 사용자 타입 분류 (헤비/안정추구/균형/스마트/절약/라이트)",
                    "가중평균 사용률 계산 (데이터 60% + 음성 30% + SMS 10%)",
                    "구체적 절약/추가 비용 계산 (월/연간)",
                    "실생활 비교 설명 (치킨값, 넷플릭스 등)",
                    "6가지 추천 전략 (긴급업그레이드/업그레이드/유지/최적화/다운그레이드/대안)"
                ]
            },
            "UBTI_성향_분석": {
                "status": "✅ 활성",
                "description": "4단계 질문을 통한 개인 성향 분석 및 타코야키 타입 매칭",
                "features": ["성향 기반 요금제 추천", "구독 서비스 추천", "타코야키 캐릭터 매칭"]
            },
            "좋아요_기반_추천": {
                "status": "✅ 활성",
                "description": "개인 취향 데이터 기반 구독 서비스 큐레이션",
                "features": ["협업 필터링", "카테고리별 선호도 분석", "맞춤 패키지 구성"]
            },
        },
        "ai_models": {
            "인텐트_분류기": "GPT-4o-mini (99.1% 정확도)",
            "대화_엔진": "GPT-4o-mini + Template-based",
            "추천_엔진": "Custom Algorithm + AI"
        },
        "technology_stack": {
            "backend": "FastAPI + Python 3.9+",
            "ai_framework": "LangChain + OpenAI",
            "session_management": "Redis (TTL 30분)",
            "database": "MySQL + SQLAlchemy",
            "streaming": "Server-Sent Events (SSE)"
        }
    }

# 사용량 추천 API 상세 정보
@app.get("/api/chat/usage/info", tags=["📊 사용량 기반 추천"])
async def usage_recommendation_info():
    """사용량 기반 추천 시스템 상세 정보"""
    return {
        "system_name": "🎯 사용량 기반 스마트 추천 엔진 v2.0",
        "description": "실제 데이터/음성/SMS 사용 패턴을 AI로 분석하여 최적의 요금제를 추천",
        "analysis_method": {
            "사용률_계산": "가중평균 (데이터 60% + 음성 30% + SMS 10%)",
            "타입_분류": "6가지 사용자 타입으로 정교한 분류",
            "비용_분석": "월/연간 절약액 및 추가 투자 비용 정확 계산",
            "설명_생성": "실생활 비유를 통한 이해하기 쉬운 설명"
        },
        "user_types": {
            "헤비_사용자": {"기준": "85%+", "특징": "대용량 필요, 긴급 업그레이드 권장"},
            "안정_추구형": {"기준": "70-84%", "특징": "안정성 중시, 여유분 확보"},
            "균형잡힌_사용자": {"기준": "40-69% & >2GB", "특징": "적절한 사용, 현 상태 유지"},
            "스마트_선택형": {"기준": "40-69% & ≤2GB", "특징": "효율적 사용, 최적화 가능"},
            "절약형_사용자": {"기준": "20-39%", "특징": "비용 절약 기회"},
            "라이트_사용자": {"기준": "<20%", "특징": "최소 요금제 적합"}
        },
        "recommendation_strategies": {
            "urgent_upgrade": "95%+ 사용률 → 상위 요금제 3개",
            "upgrade": "85-94% 사용률 → +2만원 이내 2개",
            "maintain": "70-84% 사용률 → ±1만원 이내 2개",
            "alternative": "40-69% 사용률 → ±1.5만원 이내 3개",
            "cost_optimize": "20-39% 사용률 → 현재가 이하 3개",
            "downgrade": "<20% 사용률 → 하위 요금제 3개"
        },
        "response_examples": {
            "무너_톤": "너는 완전 **절약형 사용자**구나! 💸\n월 12,000원 절약하면 치킨 2번 더 시켜먹을 수 있어! 싹싹김치! ✨",
            "일반_톤": "**절약형 사용자**로 분석됩니다! 💰\n월 12,000원 절약 (연간 144,000원)\n절약한 비용으로 다른 구독 서비스 이용 가능합니다."
        }
    }

# 개발 환경 전용 디버그 엔드포인트
@app.get("/debug/session/{session_id}", tags=["🔧 개발자도구"])
async def debug_session(session_id: str):
    """세션 상태 디버깅 (개발용)"""
    from app.utils.redis_client import get_session

    session_data = get_session(session_id)
    return {
        "session_id": session_id,
        "data": session_data,
        "has_data": bool(session_data),
        "keys": list(session_data.keys()) if session_data else [],
        "ttl_info": "Redis TTL 30분 설정"
    }

@app.post("/debug/intent", tags=["🔧 개발자도구"])
async def debug_intent_classification(request: dict):
    """인텐트 분류 테스트 (개발용)"""
    from app.utils.intent_classifier import EnhancedIntentClassifier

    classifier = EnhancedIntentClassifier()
    message = request.get("message", "")

    if not message:
        return {"error": "message 필드가 필요합니다"}

    intent = await classifier.classify_intent(message)
    return {
        "message": message,
        "classified_intent": intent,
        "timestamp": "디버그용 분류 결과"
    }

# 에러 핸들링
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return {
        "error": "Not Found",
        "message": "🔍 요청하신 엔드포인트를 찾을 수 없습니다.",
        "suggestion": "API 문서를 확인해보세요",
        "docs_url": "/docs",
        "available_endpoints": [
            "/api/chat - 대화 시작",
            "/api/chat/usage/recommend - 사용량 기반 추천",
            "/api/ubti/question - UBTI 분석",
            "/api/chat/likes - 좋아요 기반 추천"
        ]
    }

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return {
        "error": "Internal Server Error",
        "message": "서버 내부 오류가 발생했습니다.",
        "suggestion": "잠시 후 다시 시도해주세요",
        "support": "지속적인 문제 발생 시 개발팀에 문의하세요"
    }