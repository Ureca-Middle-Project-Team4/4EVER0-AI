# app/services/handle_chat.py
from typing import Callable, Awaitable
from app.schemas.chat import ChatRequest
from app.utils.intent import detect_intent, handle_off_topic_response, handle_greeting_response, handle_tech_issue_response, handle_unknown_response
from app.chains.chat_chain import get_chain_by_intent, get_multi_turn_chain
from app.utils.redis_client import get_session, save_session

async def handle_chat(req: ChatRequest) -> Callable[[], Awaitable[str]]:
    """메인 채팅 핸들러 - 인텐트 기반 체인 선택"""

    # 1. AI 기반 인텐트 감지
    intent = await detect_intent(req.message)
    tone = req.tone or "general"

    print(f"[DEBUG] Detected intent: {intent}, Tone: {tone}")

    # 2. 세션에 현재 인텐트 저장
    session = get_session(req.session_id)
    session["current_intent"] = intent
    save_session(req.session_id, session)

    # 3. 오프토픽 처리
    if intent == "off_topic":
        response_text = await handle_off_topic_response(req.message, tone)
        async def stream():
            words = response_text.split()
            for word in words:
                yield word + " "
        return stream

    # 4. 인사 처리
    elif intent == "greeting":
        response_text = await handle_greeting_response(req.message, tone)
        async def stream():
            words = response_text.split()
            for word in words:
                yield word + " "
        return stream

    # 5. 기술 문제 처리
    elif intent == "tech_issue":
        response_text = await handle_tech_issue_response(req.message, tone)
        async def stream():
            words = response_text.split()
            for word in words:
                yield word + " "
        return stream

    # 6. 알 수 없는 요청 처리
    elif intent == "unknown":
        response_text = await handle_unknown_response(req.message, tone)
        async def stream():
            words = response_text.split()
            for word in words:
                yield word + " "
        return stream

    # 7. 요금제 관련 처리
    elif intent.startswith("telecom_plan"):
        # telecom_plan_direct → 바로 추천
        if intent == "telecom_plan_direct":
            return get_chain_by_intent("phone_plan_recommend", req, tone)
        # telecom_plan → 멀티턴
        else:
            session["current_intent"] = "phone_plan"  # 정규화
            save_session(req.session_id, session)
            return await get_multi_turn_chain(req, "phone_plan_multi", tone)

    # 8. 구독 서비스 처리
    elif intent in ["subscription", "subscription_recommend"]:
        session["current_intent"] = "subscription"  # 정규화
        save_session(req.session_id, session)
        return await get_multi_turn_chain(req, "subscription_multi", tone)

    # 9. 현재 사용량 안내
    elif intent == "current_usage":
        if tone == "muneoz":
            response_text = """현재 사용량은 /api/usage/{user_id} 로 확인할 수 있어! 🐙

사용량 기반 맞춤 추천도 받을 수 있으니까
언제든지 말해줘~ 💜"""
        else:
            response_text = """현재 사용량은 /api/usage/{user_id} 엔드포인트에서 확인하실 수 있습니다. 😊

사용량 기반 맞춤 추천 서비스도 제공하고 있으니
필요하시면 언제든 말씀해주세요!"""

        async def stream():
            words = response_text.split()
            for word in words:
                yield word + " "
        return stream

    # 10. UBTI 안내
    elif intent == "ubti":
        if tone == "muneoz":
            response_text = """UBTI 타코시그널 테스트 하고 싶구나! 🐙

/api/ubti/question 으로 시작하면 되고
4단계 질문 거쳐서 네 성향 분석해줄게!

완전 재밌을 거야~ 🔥"""
        else:
            response_text = """UBTI 성향 분석에 관심이 있으시군요! 😊

/api/ubti/question 엔드포인트에서 시작하실 수 있어요.
4단계 질문을 통해 개인 맞춤 분석을 제공합니다.

언제든 체험해보세요!"""

        async def stream():
            words = response_text.split()
            for word in words:
                yield word + " "
        return stream

    # 11. 기본 처리
    else:
        return get_chain_by_intent("default", req, tone)