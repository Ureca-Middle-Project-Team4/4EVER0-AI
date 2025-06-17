from fastapi import APIRouter, HTTPException, Query
from app.schemas.chat import ChatRequest
from app.services.handle_usage import handle_usage_recommendation
from app.db.plan_db import get_all_plans
from app.db.subscription_db import get_products_from_db
from app.prompts.usage_prompt import get_usage_prompt
from app.utils.langchain_client import get_chat_model
from typing import Optional
import asyncio

router = APIRouter()

class UsageRecommendationRequest:
    def __init__(self, user_id: int, tone: str = "general"):
        self.user_id = user_id
        self.tone = tone

@router.post("/usage/recommend")
async def usage_based_recommendation(
    user_id: int = Query(..., description="사용자 ID"),
    tone: str = Query("general", description="응답 톤 (general/muneoz)")
):
    """
    사용자 사용량 기반 추천
    """
    try:
        print(f"[DEBUG] Usage recommendation request - user_id: {user_id}, tone: {tone}")
        
        # 요금제와 구독 서비스 데이터 조회
        plans = get_all_plans()
        subscriptions = get_products_from_db()
        
        # 사용량 기반 추천 로직
        recommendations = await generate_usage_recommendations(user_id, plans, subscriptions, tone)
        
        return {
            "success": True,
            "message": "사용량 기반 추천이 완료되었습니다.",
            "data": recommendations
        }
        
    except Exception as e:
        print(f"[ERROR] Usage recommendation failed: {e}")
        raise HTTPException(status_code=500, detail=f"추천 생성 실패: {str(e)}")

@router.get("/usage/{user_id}")
async def get_user_usage(user_id: int):
    """
    사용자 사용량 조회
    """
    try:
        # 실제 사용량 데이터는 없으므로 모의 데이터 반환
        usage_data = {
            "user_id": user_id,
            "data_usage": "7.2GB",
            "voice_usage": "180분",
            "sms_usage": "45건",
            "monthly_average": {
                "data": "6.8GB",
                "voice": "150분",
                "sms": "52건"
            },
            "usage_pattern": {
                "peak_hours": ["19:00-22:00", "07:00-09:00"],
                "most_used_services": ["YouTube", "Instagram", "카카오톡"],
                "data_trend": "증가"
            }
        }
        
        return {
            "success": True,
            "message": "사용량 조회 성공",
            "data": usage_data
        }
        
    except Exception as e:
        print(f"[ERROR] Usage data retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"사용량 조회 실패: {str(e)}")

async def generate_usage_recommendations(user_id: int, plans: list, subscriptions: list, tone: str = "general"):
    """
    사용량 기반 추천 생성
    """
    try:
        # 모의 사용량 데이터 생성 (실제로는 DB에서 조회)
        usage_data = {
            "data_usage": 7.2,  # GB
            "voice_usage": 180,  # 분
            "sms_usage": 45,     # 건
            "services": ["YouTube", "Instagram", "카카오톡"],
            "peak_time": "저녁시간",
            "trend": "데이터 사용량 증가"
        }
        
        # 요금제 데이터 포맷팅 (오류 방지를 위해 안전하게 처리)
        plans_text = "\n".join([
            f"- {p.name} / {format_price_safely(p.price)} / {p.data or '-'} / {p.voice or '-'}"
            for p in plans
        ])
        
        # 구독 서비스 데이터 포맷팅
        subs_text = "\n".join([
            f"- {s.title} ({s.category}) - {format_price_safely(s.price)}"
            for s in subscriptions
        ])
        
        # 사용량 정보 텍스트화
        usage_text = f"""
- 데이터 사용량: {usage_data['data_usage']}GB (월평균)
- 음성통화: {usage_data['voice_usage']}분
- 문자: {usage_data['sms_usage']}건
- 주요 사용 서비스: {', '.join(usage_data['services'])}
- 주 사용 시간대: {usage_data['peak_time']}
- 사용 패턴: {usage_data['trend']}
"""
        
        # 프롬프트 생성
        prompt = get_usage_prompt(tone).format(
            usage_info=usage_text,
            plans=plans_text,
            subscriptions=subs_text
        )
        
        # AI 모델 호출
        model = get_chat_model()
        response = await model.ainvoke(prompt)
        
        return {
            "user_id": user_id,
            "usage_analysis": usage_data,
            "recommendation": response.content,
            "tone": tone
        }
        
    except Exception as e:
        print(f"[ERROR] Recommendation generation failed: {e}")
        raise e

def format_price_safely(price):
    """
    가격을 안전하게 포맷팅하는 함수
    문자열/숫자 타입 모두 처리 가능
    """
    try:
        # 이미 문자열이고 '원'이 포함된 경우
        if isinstance(price, str):
            if '원' in price:
                return price
            # 숫자 문자열인 경우 정수로 변환 후 포맷팅
            try:
                price_num = int(price.replace(',', '').replace('원', ''))
                return f"{price_num:,}원"
            except ValueError:
                return price
        
        # 숫자인 경우
        elif isinstance(price, (int, float)):
            return f"{int(price):,}원"
        
        # 기타 경우
        else:
            return str(price)
            
    except Exception as e:
        print(f"[WARNING] Price formatting failed for {price}: {e}")
        return str(price)