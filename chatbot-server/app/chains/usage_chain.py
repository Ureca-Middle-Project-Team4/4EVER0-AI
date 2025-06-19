from typing import Callable, Awaitable
import asyncio
from app.utils.langchain_client import get_chat_model
from app.schemas.usage import CurrentUsageRequest, UserUsageInfo
from app.db.user_usage_db import get_user_current_usage
from app.db.plan_db import get_all_plans
from app.prompts.usage_prompt import get_usage_prompt

async def get_usage_based_recommendation_chain(req: CurrentUsageRequest) -> Callable[[], Awaitable[str]]:
    """현재 사용량 기반 요금제 추천 체인 - 요금제만 추천"""

    # 1. 사용자 현재 사용량 정보 조회 (CSV id 기반)
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

    # 4. 사용 패턴에 맞는 요금제 필터링
    recommended_plans = _filter_plans_by_usage(all_plans, user_usage, recommendation_type)

    # 5. 컨텍스트 구성 (구독 서비스 제외)
    context = {
        "user_id": req.user_id,
        "current_plan": user_usage.current_plan_name,
        "current_price": f"{user_usage.current_plan_price:,}원",
        "remaining_data": user_usage.remaining_data,
        "remaining_voice": user_usage.remaining_voice,
        "remaining_sms": user_usage.remaining_sms,
        "usage_percentage": f"{user_usage.usage_percentage:.1f}%",
        "recommendation_type": recommendation_type,
        "recommended_plans": "\n".join([
            f"- {p.name} / {_format_price_safely(p.price)} / {p.data} / {p.voice}"
            for p in recommended_plans
        ]),
        "usage_analysis": _get_usage_analysis(user_usage)
    }

    # 6. LangChain으로 추천 생성 (요금제만)
    prompt_text = get_usage_prompt(req.tone).format(**context)
    model = get_chat_model()

    async def stream():
        async for chunk in model.astream(prompt_text):
            if chunk and hasattr(chunk, 'content') and chunk.content:
                yield chunk.content
                await asyncio.sleep(0.01)

    return stream

def _analyze_usage_pattern(usage: UserUsageInfo) -> str:
    """사용 패턴 분석 - 개선된 로직"""
    usage_pct = usage.usage_percentage

    # 현재 요금제 가격대 분석
    current_price = usage.current_plan_price

    if usage_pct >= 95:
        return "urgent_upgrade"  # 긴급 업그레이드 필요
    elif usage_pct >= 85:
        return "upgrade"  # 업그레이드 권장
    elif usage_pct >= 70:
        return "maintain"  # 현재 요금제 유지 적절
    elif usage_pct <= 20:
        return "downgrade"  # 다운그레이드 고려
    elif usage_pct <= 40:
        return "cost_optimize"  # 비용 최적화 가능
    else:
        return "alternative"  # 대안 제시

def _filter_plans_by_usage(all_plans: list, usage: UserUsageInfo, recommendation_type: str) -> list:
    """사용 패턴에 따른 요금제 필터링"""
    current_price = usage.current_plan_price

    # 🔥 Plan.price가 문자열일 수 있으므로 안전하게 정수 변환
    def safe_price(plan):
        try:
            if isinstance(plan.price, str):
                # "30,000원" 형태에서 숫자만 추출
                price_str = plan.price.replace(',', '').replace('원', '').strip()
                return int(price_str)
            return int(plan.price)
        except (ValueError, TypeError):
            return 0

    if recommendation_type == "urgent_upgrade":
        # 현재보다 상위 요금제 (데이터 더 많은)
        return [p for p in all_plans if safe_price(p) > current_price][:3]

    elif recommendation_type == "upgrade":
        # 현재보다 약간 상위 요금제
        return [p for p in all_plans if current_price < safe_price(p) <= current_price + 20000][:2]

    elif recommendation_type == "maintain":
        # 현재와 비슷한 가격대
        return [p for p in all_plans if abs(safe_price(p) - current_price) <= 10000][:2]

    elif recommendation_type == "downgrade":
        # 현재보다 저렴한 요금제
        return [p for p in all_plans if safe_price(p) < current_price][:3]

    elif recommendation_type == "cost_optimize":
        # 비용 효율적인 요금제들
        return [p for p in all_plans if safe_price(p) <= current_price][:3]

    else:  # alternative
        # 다양한 옵션 제시
        return [p for p in all_plans if abs(safe_price(p) - current_price) <= 15000][:3]

def _get_usage_analysis(usage: UserUsageInfo) -> str:
    """사용량 분석 텍스트 생성"""
    data_used_mb = _estimate_data_used(usage)
    voice_used_min = _estimate_voice_used(usage)
    sms_used_count = _estimate_sms_used(usage)

    return f"""현재 사용량 분석:
- 데이터: 약 {data_used_mb/1000:.1f}GB 사용 (남은 용량: {usage.remaining_data}MB)
- 음성통화: 약 {voice_used_min}분 사용 (남은 시간: {usage.remaining_voice}분)
- 문자: 약 {sms_used_count}건 사용 (남은 건수: {usage.remaining_sms}건)
- 전체 사용률: {usage.usage_percentage:.1f}%"""

def _estimate_data_used(usage: UserUsageInfo) -> int:
    """사용한 데이터량 추정 (MB)"""
    # 일반적인 요금제 데이터량에서 남은 용량을 빼서 추정
    plan_name = usage.current_plan_name.lower()

    if "라이트" in plan_name:
        if "23" in plan_name:
            total_mb = 3000  # 3GB
        else:
            total_mb = 5000  # 기본 5GB
    elif "너겟" in plan_name:
        if "30" in plan_name:
            total_mb = 8000  # 8GB
        elif "32" in plan_name:
            total_mb = 12000  # 12GB
        elif "34" in plan_name:
            total_mb = 15000  # 15GB
        elif "36" in plan_name:
            total_mb = 20000  # 20GB
        else:
            total_mb = 10000  # 기본
    else:
        total_mb = 10000  # 기본값

    return max(0, total_mb - usage.remaining_data)

def _estimate_voice_used(usage: UserUsageInfo) -> int:
    """사용한 음성통화 시간 추정 (분)"""
    # 일반적으로 300분 기본 제공이라고 가정
    base_voice = 300
    return max(0, base_voice - usage.remaining_voice)

def _format_price_safely(price) -> str:
    """가격을 안전하게 포맷팅하는 함수"""
    try:
        if isinstance(price, str):
            if '원' in price:
                return price
            try:
                price_num = int(price.replace(',', '').replace('원', ''))
                return f"{price_num:,}원"
            except ValueError:
                return price
        elif isinstance(price, (int, float)):
            return f"{int(price):,}원"
        else:
            return str(price)
    except Exception as e:
        print(f"[WARNING] Price formatting failed for {price}: {e}")
        return str(price)

def _estimate_sms_used(usage: UserUsageInfo) -> int:
    """사용한 문자 건수 추정"""
    # SMS는 보통 무제한이므로 사용량 기반으로 추정하기 어려움
    # 평균적인 사용량으로 가정
    if usage.usage_percentage > 70:
        return 50  # 많이 사용
    elif usage.usage_percentage > 30:
        return 20  # 보통 사용
    else:
        return 5   # 적게 사용