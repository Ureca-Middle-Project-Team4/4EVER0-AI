import asyncio
import re
import json
from app.schemas.chat import ChatRequest
from app.utils.intent import detect_intent, handle_off_topic_response, handle_tech_issue_response, handle_greeting_response
from app.chains.chat_chain import get_chain_by_intent, get_multi_turn_chain
from app.utils.redis_client import get_session, save_session
from app.db.user_usage_db import get_user_current_usage
from app.db.plan_db import get_all_plans
from app.db.coupon_like_db import get_liked_brand_ids
from app.db.subscription_db import get_products_from_db
from app.db.brand_db import get_life_brands_from_db

def create_simple_stream(text: str):
    """간단한 텍스트를 스트리밍으로 변환"""
    async def stream():
        words = text.split(' ')
        for i, word in enumerate(words):
            yield word
            if i < len(words) - 1:
                yield ' '
            await asyncio.sleep(0.05)
    return stream

def extract_user_id_from_message(message: str) -> int:
    """메시지에서 user_id 추출"""
    # "user_id: 1", "사용자 1", "유저 1" 등의 패턴에서 숫자 추출
    patterns = [
        r'user_?id[:\s]*(\d+)',
        r'사용자[:\s]*(\d+)',
        r'유저[:\s]*(\d+)',
        r'아이디[:\s]*(\d+)',
        r'(\d+)번?\s*사용자',
        r'(\d+)번?\s*유저'
    ]

    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return int(match.group(1))

    return None

async def handle_usage_based_recommendation_in_chat(req: ChatRequest) -> callable:
    """채팅에서 사용량 기반 추천 처리"""
    tone = getattr(req, 'tone', 'general')

    # 메시지에서 user_id 추출
    user_id = extract_user_id_from_message(req.message)

    if not user_id:
        # user_id가 없으면 안내 메시지
        if tone == "muneoz":
            response_text = """사용량 기반 추천 원해? 완전 지리는 아이디어야! 🔥

근데 user_id를 알려줘야 해!
이런 식으로 말해봐:
• "내 사용량으로 추천해줘 (user_id: 1)"
• "사용자 1 사용량 기반 추천"
• "유저 2 사용 패턴 분석해줘"

그럼 완전 찰떡인 요금제 찾아줄게~ 🎯"""
        else:
            response_text = """사용량 기반 추천 서비스를 이용하시려면 사용자 ID가 필요합니다! 😊

다음과 같은 형태로 말씀해주세요:
• "내 사용량으로 추천해줘 (user_id: 1)"
• "사용자 1 사용량 기반 추천"
• "유저 2 사용 패턴 분석해줘"

사용자 ID를 확인 후 맞춤 요금제를 추천해드리겠습니다! 📊"""

        return create_simple_stream(response_text)

    # 사용량 정보 조회
    user_usage = get_user_current_usage(user_id)
    if not user_usage:
        if tone == "muneoz":
            response_text = f"앗! {user_id}번 사용자 정보를 찾을 수 없어! 😅\nuser_id 다시 확인해줘~"
        else:
            response_text = f"죄송합니다. 사용자 {user_id}의 정보를 찾을 수 없습니다. 😔\n올바른 사용자 ID인지 확인해주세요."

        return create_simple_stream(response_text)

    # 추천 로직 실행
    async def usage_recommendation_stream():
        # 1. 사용량 분석 정보 표시
        usage_info = f"""📊 {user_id}번 사용자 사용량 분석:
• 현재 요금제: {user_usage.current_plan_name} ({user_usage.current_plan_price:,}원)
• 남은 데이터: {user_usage.remaining_data}MB
• 남은 통화: {user_usage.remaining_voice}분
• 남은 문자: {user_usage.remaining_sms}건
• 사용률: {user_usage.usage_percentage:.1f}%

"""

        for char in usage_info:
            yield char
            await asyncio.sleep(0.01)

        # 2. 추천 요금제 찾기
        recommendation_type = _analyze_usage_pattern(user_usage)
        all_plans = get_all_plans()
        recommended_plans = _filter_plans_by_usage(all_plans, user_usage, recommendation_type)

        # 3. 추천 설명
        explanation = _generate_usage_explanation(user_usage, recommendation_type, recommended_plans, tone)

        for char in explanation:
            yield char
            await asyncio.sleep(0.01)

        # 4. 추천 요금제 목록
        if recommended_plans:
            plans_text = "\n\n📋 추천 요금제:\n"
            for i, plan in enumerate(recommended_plans[:3], 1):
                plans_text += f"{i}. {plan.name} - {_safe_price_format(plan.price)}\n"
                plans_text += f"   └ {plan.data} / {plan.voice}\n"

            for char in plans_text:
                yield char
                await asyncio.sleep(0.01)

    return usage_recommendation_stream

async def handle_likes_based_recommendation_in_chat(req: ChatRequest) -> callable:
    """채팅에서 좋아요 기반 추천 처리"""
    tone = getattr(req, 'tone', 'general')

    # 좋아요 브랜드 조회
    liked_brand_ids = get_liked_brand_ids(req.session_id)

    if not liked_brand_ids:
        # 좋아요가 없으면 안내
        if tone == "muneoz":
            response_text = """아직 좋아요한 브랜드가 없네! 😅

먼저 브랜드에 좋아요를 눌러줘~
그럼 네 취향에 완전 찰떡인 구독 서비스 조합 추천해줄게! 💜

좋아요 누르고 다시 말해봐! ✨"""
        else:
            response_text = """아직 좋아요를 누른 브랜드가 없으시네요! 😊

먼저 관심 있는 브랜드에 좋아요를 눌러주시면,
고객님의 취향에 맞는 구독 서비스를 추천해드릴게요!

좋아요 설정 후 다시 요청해주세요! ⭐"""

        return create_simple_stream(response_text)

    # 좋아요 기반 추천 로직 실행
    async def likes_recommendation_stream():
        # 1. 좋아요 정보 표시
        brands = get_life_brands_from_db()
        liked_brands = [b for b in brands if b.id in liked_brand_ids]

        likes_info = f"💜 좋아요한 브랜드 ({len(liked_brands)}개):\n"
        for brand in liked_brands[:3]:  # 최대 3개만 표시
            likes_info += f"• {brand.name}\n"
        likes_info += "\n"

        for char in likes_info:
            yield char
            await asyncio.sleep(0.01)

        # 2. 구독 서비스 추천
        subscriptions = get_products_from_db()

        # 간단한 추천 로직 (실제로는 더 복잡할 수 있음)
        recommended_main = subscriptions[0] if subscriptions else None
        recommended_brand = liked_brands[0] if liked_brands else None

        if tone == "muneoz":
            explanation = f"""네 취향 보니까 이런 조합이 완전 럭키비키할 것 같아! 🔥

✅ 메인 구독: {recommended_main.title if recommended_main else '없음'}
→ 네 스타일에 딱 맞는 콘텐츠 가득! ✨

✅ 라이프 브랜드: {recommended_brand.name if recommended_brand else '없음'}
→ 이미 좋아요 눌렀으니까 완전 찰떡이지! 💜

이 조합 어때? 느좋임? 🤟"""
        else:
            explanation = f"""고객님의 취향을 바탕으로 맞춤 조합을 추천드립니다! 😊

✅ 추천 메인 구독: {recommended_main.title if recommended_main else '없음'}
→ 고객님이 선호하실만한 콘텐츠를 제공합니다

✅ 추천 라이프 브랜드: {recommended_brand.name if recommended_brand else '없음'}
→ 이미 관심을 보이신 브랜드로 만족도가 높을 것 같습니다

이 조합이 어떠신가요? 😊"""

        for char in explanation:
            yield char
            await asyncio.sleep(0.01)

    return likes_recommendation_stream

def _analyze_usage_pattern(usage) -> str:
    """사용 패턴 분석"""
    usage_pct = usage.usage_percentage

    if usage_pct >= 95:
        return "urgent_upgrade"
    elif usage_pct >= 85:
        return "upgrade"
    elif usage_pct >= 70:
        return "maintain"
    elif usage_pct <= 20:
        return "downgrade"
    elif usage_pct <= 40:
        return "cost_optimize"
    else:
        return "alternative"

def _filter_plans_by_usage(all_plans: list, usage, recommendation_type: str) -> list:
    """사용 패턴에 따른 요금제 필터링"""
    current_price = usage.current_plan_price

    def safe_price(plan):
        try:
            if isinstance(plan.price, str):
                price_str = plan.price.replace(',', '').replace('원', '').strip()
                return int(price_str)
            return int(plan.price)
        except (ValueError, TypeError):
            return 0

    if recommendation_type == "urgent_upgrade":
        return [p for p in all_plans if safe_price(p) > current_price][:3]
    elif recommendation_type == "upgrade":
        return [p for p in all_plans if current_price < safe_price(p) <= current_price + 20000][:2]
    elif recommendation_type == "maintain":
        return [p for p in all_plans if abs(safe_price(p) - current_price) <= 10000][:2]
    elif recommendation_type == "downgrade":
        return [p for p in all_plans if safe_price(p) < current_price][:3]
    elif recommendation_type == "cost_optimize":
        return [p for p in all_plans if safe_price(p) <= current_price][:3]
    else:  # alternative
        return [p for p in all_plans if abs(safe_price(p) - current_price) <= 15000][:3]

def _generate_usage_explanation(usage, recommendation_type: str, recommended_plans: list, tone: str) -> str:
    """사용량 기반 추천 설명"""
    usage_pct = usage.usage_percentage

    if tone == "muneoz":
        if recommendation_type == "urgent_upgrade":
            return f"헉! 사용률이 {usage_pct:.1f}%나 돼서 완전 위험해! 🚨\n지금 당장 상위 요금제로 바꿔야겠어~ 🔥"
        elif recommendation_type == "upgrade":
            return f"사용률이 {usage_pct:.1f}%라서 좀 더 넉넉한 게 좋을 것 같아! 💪\n이런 요금제들 어때? ✨"
        elif recommendation_type == "maintain":
            return f"사용률 {usage_pct:.1f}%로 딱 적당해! 😊\n비슷한 가격대로 이런 것들 있어~ 🤟"
        elif recommendation_type == "downgrade":
            return f"사용률이 {usage_pct:.1f}%밖에 안 돼서 돈 아까워! 💸\n더 저렴한 걸로 바꿔봐~ 싹싹김치! ✨"
        else:
            return f"사용률 {usage_pct:.1f}%보니까 이런 요금제들이 느좋할 것 같아! 🎯"
    else:
        if recommendation_type == "urgent_upgrade":
            return f"현재 사용률이 {usage_pct:.1f}%로 매우 높습니다. 🚨\n상위 요금제로 변경을 권장드립니다."
        elif recommendation_type == "upgrade":
            return f"사용률 {usage_pct:.1f}%로 여유가 필요해 보입니다. 📈\n다음 요금제들을 고려해보세요."
        elif recommendation_type == "maintain":
            return f"사용률 {usage_pct:.1f}%로 적절합니다. ✅\n비슷한 수준의 요금제들을 추천드립니다."
        elif recommendation_type == "downgrade":
            return f"사용률이 {usage_pct:.1f}%로 낮아 비용 절약이 가능합니다. 💰"
        else:
            return f"사용률 {usage_pct:.1f}%를 고려한 맞춤 요금제들입니다. 🎯"

def _safe_price_format(price) -> str:
    """가격을 안전하게 포맷팅"""
    try:
        if isinstance(price, str):
            if '원' in price:
                return price
            price_num = int(price.replace(',', '').replace('원', ''))
            return f"{price_num:,}원"
        return f"{int(price):,}원"
    except:
        return str(price)

async def handle_chat(req: ChatRequest):
    """통일된 세션 키를 사용하는 채팅 핸들러"""

    tone = getattr(req, 'tone', 'general')
    print(f"[DEBUG] ========== HANDLE_CHAT START ==========")
    print(f"[DEBUG] Input - tone: {tone}, message: '{req.message}'")

    # 세션에서 멀티턴 진행 상태 확인 - 통일된 키 사용
    session = get_session(req.session_id)

    # 기존 키들을 통일된 키로 변환
    phone_plan_step = session.get("phone_plan_flow_step", 0) or session.get("plan_step", 0)
    subscription_step = session.get("subscription_flow_step", 0) or session.get("subscription_step", 0)

    # 통일된 키로 저장
    if session.get("plan_step") and not session.get("phone_plan_flow_step"):
        session["phone_plan_flow_step"] = session.pop("plan_step")
        session["user_info"] = session.pop("plan_info", {})
        save_session(req.session_id, session)

    if session.get("subscription_step") and not session.get("subscription_flow_step"):
        session["subscription_flow_step"] = session.pop("subscription_step")
        session["user_info"] = session.pop("subscription_info", {})
        save_session(req.session_id, session)

    print(f"[DEBUG] Session state - phone_plan_step: {phone_plan_step}, subscription_step: {subscription_step}")
    print(f"[DEBUG] Session keys: {list(session.keys())}")

    # 🔥 멀티턴이 진행 중이면 해당 플로우 계속 진행
    if phone_plan_step > 0:
        print(f"[DEBUG] >>> CONTINUING PHONE PLAN MULTI-TURN (step: {phone_plan_step}) <<<")
        try:
            return await get_multi_turn_chain(req, "phone_plan_multi", tone)
        except Exception as e:
            print(f"[ERROR] Phone plan multi-turn failed: {e}")
            # 플로우 초기화 후 에러 응답
            session.pop("phone_plan_flow_step", None)
            session.pop("plan_step", None)
            session.pop("user_info", None)
            session.pop("plan_info", None)
            save_session(req.session_id, session)
            return create_simple_stream("요금제 질문 중 오류가 발생했어요. 처음부터 다시 시작해주세요! 😅")

    elif subscription_step > 0:
        print(f"[DEBUG] >>> CONTINUING SUBSCRIPTION MULTI-TURN (step: {subscription_step}) <<<")
        try:
            return await get_multi_turn_chain(req, "subscription_multi", tone)
        except Exception as e:
            print(f"[ERROR] Subscription multi-turn failed: {e}")
            # 플로우 초기화 후 에러 응답
            session.pop("subscription_flow_step", None)
            session.pop("subscription_step", None)
            session.pop("user_info", None)
            session.pop("subscription_info", None)
            save_session(req.session_id, session)
            return create_simple_stream("구독 서비스 질문 중 오류가 발생했어요. 처음부터 다시 시작해주세요! 😅")

    # 🔥 새로운 대화 - AI 기반 인텐트 감지
    print(f"[DEBUG] >>> STARTING NEW CONVERSATION - DETECTING INTENT <<<")
    try:
        intent = await detect_intent(req.message)
        print(f"[DEBUG] >>> AI DETECTED INTENT: '{intent}' <<<")
    except Exception as e:
        print(f"[ERROR] Intent detection failed: {e}")
        intent = "off_topic_unclear"

    # 🔥 인텐트별 처리
    print(f"[DEBUG] >>> PROCESSING INTENT: '{intent}' <<<")

    try:
        # 🔥 인사 처리 (최우선)
        if intent == "greeting" or req.message.lower().strip() in ["안녕", "hi", "hello", "하이", "헬로"]:
            print(f"[DEBUG] >>> HANDLING GREETING <<<")
            response_text = await handle_greeting_response(req.message, tone)
            return create_simple_stream(response_text)

        # 🔥 새로 추가: 사용량 기반 추천
        elif intent == "usage_based_recommendation":
            print(f"[DEBUG] >>> HANDLING USAGE_BASED_RECOMMENDATION <<<")
            return await handle_usage_based_recommendation_in_chat(req)

        # 🔥 새로 추가: 좋아요 기반 추천
        elif intent == "likes_based_recommendation":
            print(f"[DEBUG] >>> HANDLING LIKES_BASED_RECOMMENDATION <<<")
            return await handle_likes_based_recommendation_in_chat(req)

        # 오프토픽 처리 (nonsense 포함)
        elif intent in ["nonsense", "off_topic", "off_topic_interesting", "off_topic_boring", "off_topic_unclear"]:
            print(f"[DEBUG] >>> HANDLING OFF_TOPIC/NONSENSE: {intent} <<<")
            response_text = await handle_off_topic_response(req.message, tone)
            return create_simple_stream(response_text)

        # 기술 문제
        elif intent == "tech_issue":
            print(f"[DEBUG] >>> HANDLING TECH_ISSUE <<<")
            response_text = await handle_tech_issue_response(req.message, tone)
            return create_simple_stream(response_text)

        # 현재 사용량
        elif intent == "current_usage":
            print(f"[DEBUG] >>> HANDLING CURRENT_USAGE <<<")
            if tone == "muneoz":
                response_text = """현재 사용량 확인하고 싶구나! 📊

그런데 사용량 기반 추천은 다른 API를 써야 해~
POST /api/usage/recommend 로 user_id 보내주면
네 현재 상황에 딱 맞는 요금제 추천해줄 수 있어! 🎯

지금은 일반 요금제 추천이라도 해볼까? 💜"""
            else:
                response_text = """현재 사용량 확인을 원하시는군요! 📊

사용량 기반 맞춤 추천은 별도 API를 이용해주세요:
• POST /api/usage/recommend (user_id 필요)

현재는 일반적인 요금제 상담을 도와드릴 수 있습니다.
원하시는 서비스가 있으시면 말씀해주세요! 😊"""
            return create_simple_stream(response_text)

        # 요금제 관련 - 멀티턴 시작
        elif intent in ["telecom_plan", "telecom_plan_direct"]:
            print(f"[DEBUG] >>> HANDLING TELECOM_PLAN - STARTING MULTI-TURN <<<")
            return await get_multi_turn_chain(req, "phone_plan_multi", tone)

        # 구독 서비스 관련 - 멀티턴 시작
        elif intent == "subscription":
            print(f"[DEBUG] >>> HANDLING SUBSCRIPTION - STARTING MULTI-TURN <<<")
            return await get_multi_turn_chain(req, "subscription_multi", tone)

        # UBTI
        elif intent == "ubti":
            print(f"[DEBUG] >>> HANDLING UBTI <<<")
            if tone == "muneoz":
                response_text = """오오! UBTI 하고 싶구나? 🎯

UBTI는 별도 API에서 진행해야 해!
POST /api/ubti/question 으로 시작하면
4단계 질문 받고 완전 찰떡인 타입 알려줄 수 있어~ 🐙

지금은 요금제나 구독 추천 얘기할까? 💜"""
            else:
                response_text = """UBTI 성향 분석에 관심 있으시군요! 🎯

UBTI는 전용 API를 통해 진행됩니다:
• POST /api/ubti/question (시작)
• POST /api/ubti/result (완료)

현재는 요금제나 구독 서비스 상담을 도와드릴 수 있어요.
어떤 도움이 필요하신가요? 😊"""
            return create_simple_stream(response_text)

        # 기본 케이스 - 인사나 일반적인 대화
        else:
            print(f"[DEBUG] >>> HANDLING DEFAULT CASE FOR INTENT: {intent} <<<")
            if tone == "muneoz":
                response_text = """안뇽! 🤟 나는 무너야~ 🐙

요금제나 구독 서비스 관련해서 뭐든지 물어봐!
• 요금제 추천해줘
• 구독 서비스 추천해줘
• 내 사용량으로 추천해줘 (user_id: 1)
• 내 취향에 맞는 구독 추천해줘

뭘 도와줄까? 💜"""
            else:
                response_text = """안녕하세요! 😊 LG유플러스 상담 AI입니다.

다음과 같은 서비스를 도와드릴 수 있어요:
• 요금제 추천해주세요
• 구독 서비스 추천해주세요
• 내 사용량으로 추천해주세요 (user_id: 1)
• 내 취향에 맞는 구독 추천해주세요

어떤 도움이 필요하신가요?"""
            return create_simple_stream(response_text)

    except Exception as e:
        print(f"[ERROR] Intent handling failed: {e}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        return create_simple_stream(await handle_api_error_response(tone))

async def handle_api_error_response(tone: str = "general") -> str:
    """API 오류 시 응답"""
    if tone == "muneoz":
        return """어머 뭔가 서버가 삐끗했나봐! 😱
내가 아니라 시스템 문제야!

잠깐만 기다렸다가 다시 물어봐줘~ 🐙"""
    else:
        return """죄송합니다. 일시적인 시스템 오류가 발생했어요. 😔
잠시 후 다시 시도해주시면 정상적으로 도움드릴 수 있습니다.

불편을 드려 죄송해요! 🙏"""