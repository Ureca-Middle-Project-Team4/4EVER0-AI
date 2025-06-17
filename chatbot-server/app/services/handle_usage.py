from app.db.plan_db import get_all_plans
from app.db.subscription_db import get_products_from_db
from app.prompts.usage_prompt import get_usage_prompt
from app.utils.langchain_client import get_chat_model
import asyncio

async def handle_usage_recommendation(user_id: int, tone: str = "general"):
    """
    사용량 기반 추천 처리
    """
    try:
        print(f"[DEBUG] Handling usage recommendation for user {user_id} with tone {tone}")

        # 1. 모의 사용량 데이터 생성 (실제로는 DB에서 조회)
        usage_data = get_mock_usage_data(user_id)

        # 2. 요금제와 구독 서비스 데이터 조회
        plans = get_all_plans()
        subscriptions = get_products_from_db()

        # 3. 데이터 포맷팅
        usage_text = format_usage_data(usage_data)
        plans_text = format_plans_data(plans)
        subs_text = format_subscriptions_data(subscriptions)

        # 4. 프롬프트 생성 및 AI 호출
        prompt = get_usage_prompt(tone).format(
            usage_info=usage_text,
            plans=plans_text,
            subscriptions=subs_text
        )

        model = get_chat_model()
        response = await model.ainvoke(prompt)

        return {
            "user_id": user_id,
            "usage_analysis": usage_data,
            "recommendation": response.content,
            "tone": tone,
            "success": True
        }

    except Exception as e:
        print(f"[ERROR] Usage recommendation failed for user {user_id}: {e}")
        raise e

def get_mock_usage_data(user_id: int):
    """
    모의 사용량 데이터 생성 (실제로는 DB에서 조회)
    """
    # user_id에 따라 다른 패턴 생성
    patterns = {
        1: {
            "data_usage": 3.2,
            "voice_usage": 45,
            "sms_usage": 12,
            "services": ["카카오톡", "네이버"],
            "peak_time": "출퇴근시간",
            "trend": "가벼운 사용"
        },
        2: {
            "data_usage": 7.2,
            "voice_usage": 180,
            "sms_usage": 45,
            "services": ["YouTube", "Instagram", "카카오톡"],
            "peak_time": "저녁시간",
            "trend": "데이터 사용량 증가"
        },
        3: {
            "data_usage": 15.8,
            "voice_usage": 320,
            "sms_usage": 89,
            "services": ["YouTube", "Netflix", "게임", "화상회의"],
            "peak_time": "하루종일",
            "trend": "헤비 사용자"
        }
    }

    # user_id가 패턴에 없으면 기본값 사용
    return patterns.get(user_id, patterns[2])

def format_usage_data(usage_data):
    """
    사용량 데이터를 텍스트로 포맷팅
    """
    return f"""
- 데이터 사용량: {usage_data['data_usage']}GB (월평균)
- 음성통화: {usage_data['voice_usage']}분
- 문자: {usage_data['sms_usage']}건
- 주요 사용 서비스: {', '.join(usage_data['services'])}
- 주 사용 시간대: {usage_data['peak_time']}
- 사용 패턴: {usage_data['trend']}
"""

def format_plans_data(plans):
    """
    요금제 데이터를 안전하게 포맷팅
    """
    formatted_plans = []
    for plan in plans:
        try:
            # 가격을 안전하게 포맷팅
            if isinstance(plan.price, (int, float)):
                price_str = f"{int(plan.price):,}원"
            elif isinstance(plan.price, str):
                # 이미 포맷된 문자열인 경우
                price_str = plan.price if '원' in plan.price else f"{plan.price}원"
            else:
                price_str = str(plan.price)

            formatted_plans.append(
                f"- {plan.name} / {price_str} / {plan.data or '-'} / {plan.voice or '-'}"
            )
        except Exception as e:
            print(f"[WARNING] Plan formatting error for {plan.name}: {e}")
            formatted_plans.append(f"- {plan.name} / 가격정보오류 / {plan.data or '-'} / {plan.voice or '-'}")

    return "\n".join(formatted_plans)

def format_subscriptions_data(subscriptions):
    """
    구독 서비스 데이터를 안전하게 포맷팅
    """
    formatted_subs = []
    for sub in subscriptions:
        try:
            # 가격을 안전하게 포맷팅
            if isinstance(sub.price, (int, float)):
                price_str = f"{int(sub.price):,}원"
            elif isinstance(sub.price, str):
                price_str = sub.price if '원' in sub.price else f"{sub.price}원"
            else:
                price_str = str(sub.price)

            formatted_subs.append(f"- {sub.title} ({sub.category}) - {price_str}")
        except Exception as e:
            print(f"[WARNING] Subscription formatting error for {sub.title}: {e}")
            formatted_subs.append(f"- {sub.title} ({sub.category}) - 가격정보오류")

    return "\n".join(formatted_subs)