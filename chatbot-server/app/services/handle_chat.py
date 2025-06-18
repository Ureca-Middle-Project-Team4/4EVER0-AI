# app/services/handle_chat.py - 완전 수정된 최종 버전
import asyncio
from app.schemas.chat import ChatRequest
from app.utils.intent import detect_intent, handle_off_topic_response, handle_tech_issue_response
from app.chains.chat_chain import get_chain_by_intent, get_multi_turn_chain
from app.utils.redis_client import get_session

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
    """향상된 채팅 핸들러 - 완전 수정 버전"""

    tone = getattr(req, 'tone', 'general')
    print(f"[DEBUG] ========== HANDLE_CHAT START ==========")
    print(f"[DEBUG] Input - tone: {tone}, message: '{req.message}'")

    # 1. 세션에서 멀티턴 진행 상태 확인
    session = get_session(req.session_id)
    phone_plan_step = session.get("phone_plan_flow_step", 0)
    subscription_step = session.get("subscription_flow_step", 0)

    print(f"[DEBUG] Session state - phone_plan_step: {phone_plan_step}, subscription_step: {subscription_step}")

    # 2. 멀티턴이 진행 중이면 해당 플로우 계속 진행
    if phone_plan_step > 0:
        print(f"[DEBUG] >>> CONTINUING PHONE PLAN MULTI-TURN (step: {phone_plan_step}) <<<")
        try:
            return await get_multi_turn_chain(req, "phone_plan_multi", tone)
        except Exception as e:
            print(f"[ERROR] Phone plan multi-turn failed: {e}")
            # 플로우 초기화 후 에러 응답
            session.pop("phone_plan_flow_step", None)
            from app.utils.redis_client import save_session
            save_session(req.session_id, session)
            return create_simple_stream(await handle_loading_error_response(tone))

    elif subscription_step > 0:
        print(f"[DEBUG] >>> CONTINUING SUBSCRIPTION MULTI-TURN (step: {subscription_step}) <<<")
        try:
            return await get_multi_turn_chain(req, "subscription_multi", tone)
        except Exception as e:
            print(f"[ERROR] Subscription multi-turn failed: {e}")
            # 플로우 초기화 후 에러 응답
            session.pop("subscription_flow_step", None)
            from app.utils.redis_client import save_session
            save_session(req.session_id, session)
            return create_simple_stream(await handle_loading_error_response(tone))

    # 3. 새로운 대화 - AI 기반 인텐트 감지
    print(f"[DEBUG] >>> STARTING NEW CONVERSATION - DETECTING INTENT <<<")
    try:
        intent = await detect_intent(req.message)
        print(f"[DEBUG] >>> AI DETECTED INTENT: '{intent}' <<<")
    except Exception as e:
        print(f"[ERROR] Intent detection failed: {e}")
        intent = "off_topic_unclear"

    # 4. 인텐트별 처리 - 최종 수정!
    print(f"[DEBUG] >>> PROCESSING INTENT: '{intent}' <<<")

    try:
        if intent == "off_topic" or intent.startswith("off_topic_"):
            print(f"[DEBUG] >>> HANDLING OFF_TOPIC <<<")
            response_text = await handle_off_topic_response(req.message, tone)
            return create_simple_stream(response_text)

        elif intent == "tech_issue":
            print(f"[DEBUG] >>> HANDLING TECH_ISSUE <<<")
            response_text = await handle_tech_issue_response(req.message, tone)
            return create_simple_stream(response_text)

        elif intent == "greeting":
            print(f"[DEBUG] >>> HANDLING GREETING <<<")
            return get_chain_by_intent("greeting", req, tone)

        elif intent == "current_usage":
            print(f"[DEBUG] >>> HANDLING CURRENT_USAGE <<<")
            # 현재 사용량 확인 안내
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

        elif intent == "telecom_plan":
            print(f"[DEBUG] >>> HANDLING TELECOM_PLAN - STARTING MULTI-TURN <<<")
            print(f"[DEBUG] Message: '{req.message}'")
            print(f"[DEBUG] About to call get_multi_turn_chain with intent='phone_plan_multi'")
            # 일반적인 요금제 문의 → 항상 멀티턴 진행
            result = await get_multi_turn_chain(req, "phone_plan_multi", tone)
            print(f"[DEBUG] get_multi_turn_chain returned: {type(result)}")
            return result

        elif intent == "telecom_plan_direct":
            print(f"[DEBUG] >>> HANDLING TELECOM_PLAN_DIRECT - DIRECT RECOMMENDATION <<<")
            # 매우 구체적인 요금제 요청 → 바로 추천
            return get_chain_by_intent("phone_plan_recommend", req, tone)

        elif intent == "subscription":
            print(f"[DEBUG] >>> HANDLING SUBSCRIPTION - STARTING MULTI-TURN <<<")
            return await get_multi_turn_chain(req, "subscription_multi", tone)

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

        else:
            print(f"[DEBUG] >>> HANDLING DEFAULT CASE <<<")
            # 기본 응답
            return get_chain_by_intent("default", req, tone)

    except Exception as e:
        print(f"[ERROR] Intent handling failed: {e}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        # 에러 발생 시 적절한 응답
        return create_simple_stream(await handle_api_error_response(tone))

# 에러 응답 함수들
async def handle_loading_error_response(tone: str = "general") -> str:
    """로딩 실패 시 응답"""
    if tone == "muneoz":
        return """앗! 뭔가 삐끗했나봐! 😵
잠깐만 기다려줘~ 금방 다시 시도해볼게!

칠가이하게 기다려줘! 🐙💜"""
    else:
        return """죄송해요, 잠시 로딩에 문제가 발생했어요. 😔
조금만 기다려주시면 다시 시도해보겠습니다!

잠시만요~ ⏳"""

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