from typing import Callable, Awaitable
import asyncio
from app.utils.langchain_client import get_chat_model
from langchain_core.output_parsers import StrOutputParser
from app.prompts.usage_prompt import get_usage_recommendation_prompt
from app.schemas.usage import CurrentUsageRequest, UserUsageInfo
from app.db.user_usage_db import get_user_current_usage
from app.db.plan_db import get_all_plans

async def get_usage_based_recommendation_chain(req: CurrentUsageRequest) -> Callable[[], Awaitable[str]]:
    """현재 사용량 기반 요금제 추천 체인"""

    # 1. 사용자 현재 사용량 정보 조회
    user_usage = get_user_current_usage(req.user_id)
    if not user_usage:
        async def error_stream():
            if req.tone == "muneoz":
                yield "앗! 사용자 정보를 찾을 수 없어! 😅 user_id 다시 확인해줘~"
            else:
                yield "죄송합니다. 사용자 정보를 찾을 수 없습니다. 😔"
        return error_stream

    # 2. 추천 로직 분석
    recommendation_type = _analyze_usage_pattern(user_usage)

    # 3. 전체 요금제 목록 조회
    all_plans = get_all_plans()

    # 4. 컨텍스트 구성
    context = {
        "current_plan": user_usage.current_plan_name,
        "current_price": f"{user_usage.current_plan_price:,}원",
        "remaining_data": f"{user_usage.remaining_data}MB",
        "remaining_voice": f"{user_usage.remaining_voice}분",
        "remaining_sms": f"{user_usage.remaining_sms}개",
        "usage_percentage": f"{user_usage.usage_percentage}%",
        "recommendation_type": recommendation_type,
        "available_plans": "\n".join([
            f"- {p.name} / {p.price:,}원 / {p.data} / {p.voice}"
            for p in all_plans
        ])
    }

    # 5. LangChain으로 추천 생성
    prompt = get_usage_recommendation_prompt(req.tone)
    model = get_chat_model()
    chain = prompt | model | StrOutputParser()

    async def stream():
        async for chunk in chain.astream(context):
            if chunk:
                yield chunk
                await asyncio.sleep(0.01)

    return stream

def _analyze_usage_pattern(usage: UserUsageInfo) -> str:
    """사용 패턴 분석"""
    if usage.usage_percentage >= 90:
        return "upgrade"  # 업그레이드 필요
    elif usage.usage_percentage >= 70:
        return "maintain"  # 현재 요금제 유지
    elif usage.usage_percentage <= 30:
        return "downgrade"  # 다운그레이드 고려
    else:
        return "alternative"  # 대안 제시