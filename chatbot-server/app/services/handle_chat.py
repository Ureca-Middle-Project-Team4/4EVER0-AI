import asyncio
from app.schemas.chat import ChatRequest
from app.utils.intent import detect_intent, handle_off_topic_response, handle_tech_issue_response, handle_greeting_response
from app.chains.chat_chain import get_chain_by_intent, get_multi_turn_chain
from app.utils.redis_client import get_session, save_session

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

뭘 도와줄까? 💜"""
            else:
                response_text = """안녕하세요! 😊 LG유플러스 상담 AI입니다.

다음과 같은 서비스를 도와드릴 수 있어요:
• 요금제 추천해주세요
• 구독 서비스 추천해주세요

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