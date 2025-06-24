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

async def handle_chat(req: ChatRequest):
    """통일된 세션 키를 사용하는 채팅 핸들러 - 멀티턴 개선"""

    tone = getattr(req, 'tone', 'general')
    print(f"[DEBUG] ========== HANDLE_CHAT START ==========")
    print(f"[DEBUG] Input - tone: {tone}, message: '{req.message}'")

    # 🔥 세션에서 멀티턴 진행 상태 확인 - 통일된 키 사용
    session = get_session(req.session_id)
    print(f"[DEBUG] Current session keys: {list(session.keys())}")

    # 기존 키들을 통일된 키로 변환 (마이그레이션)
    _migrate_session_keys(session, req.session_id)

    # 현재 멀티턴 상태 확인
    phone_plan_step = session.get("phone_plan_flow_step", 0)
    subscription_step = session.get("subscription_flow_step", 0)

    print(f"[DEBUG] Multiturn status - phone_plan: {phone_plan_step}, subscription: {subscription_step}")

    # 🔥 멀티턴이 진행 중이면 해당 플로우 계속 진행
    if phone_plan_step > 0:
        print(f"[DEBUG] >>> CONTINUING PHONE PLAN MULTI-TURN (step: {phone_plan_step}) <<<")
        try:
            return await get_multi_turn_chain(req, "phone_plan_multi", tone)
        except Exception as e:
            print(f"[ERROR] Phone plan multi-turn failed: {e}")
            # 플로우 초기화 후 에러 응답
            _reset_multiturn_session(session, req.session_id, "phone_plan")
            return create_simple_stream("요금제 질문 중 오류가 발생했어요. 처음부터 다시 시작해주세요! 😅")

    elif subscription_step > 0:
        print(f"[DEBUG] >>> CONTINUING SUBSCRIPTION MULTI-TURN (step: {subscription_step}) <<<")
        try:
            return await get_multi_turn_chain(req, "subscription_multi", tone)
        except Exception as e:
            print(f"[ERROR] Subscription multi-turn failed: {e}")
            # 플로우 초기화 후 에러 응답
            _reset_multiturn_session(session, req.session_id, "subscription")
            return create_simple_stream("구독 서비스 질문 중 오류가 발생했어요. 처음부터 다시 시작해주세요! 😅")

    # 🔥 새로운 대화 - AI 기반 인텐트 감지 (컨텍스트 포함)
    print(f"[DEBUG] >>> STARTING NEW CONVERSATION - DETECTING INTENT <<<")
    try:
        # 세션 컨텍스트를 인텐트 분류에 전달
        intent = await detect_intent(req.message, user_context=session)
        print(f"[DEBUG] >>> AI DETECTED INTENT: '{intent}' with context <<<")
    except Exception as e:
        print(f"[ERROR] Intent detection failed: {e}")
        intent = "off_topic_unclear"

    # 🔥 인텐트별 처리 - multiturn_answer 우선 처리
    print(f"[DEBUG] >>> PROCESSING INTENT: '{intent}' <<<")

    try:
        # 멀티턴 답변 처리 (최우선)
        if intent == "multiturn_answer":
            print(f"[DEBUG] >>> HANDLING MULTITURN_ANSWER <<<")
            # 현재 진행 중인 플로우가 없다면 새로 시작
            if phone_plan_step == 0 and subscription_step == 0:
                # 답변 내용에 따라 적절한 플로우 시작
                if _should_start_plan_flow(req.message):
                    return await get_multi_turn_chain(req, "phone_plan_multi", tone)
                elif _should_start_subscription_flow(req.message):
                    return await get_multi_turn_chain(req, "subscription_multi", tone)
                else:
                    # 기본적으로 요금제 플로우 시작
                    return await get_multi_turn_chain(req, "phone_plan_multi", tone)
            else:
                # 이미 플로우가 진행 중이면 계속 진행 (위에서 처리됨)
                return create_simple_stream("멀티턴 처리 중 문제가 발생했어요. 😅")

        # 인사 처리 (최우선)
        elif intent == "greeting" or req.message.lower().strip() in ["안녕", "hi", "hello", "하이", "헬로"]:
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
지금은 일반 요금제 추천이라도 해볼까? 💜

네 현재 상황에 딱 맞는 요금제 추천해줄 수 있어! 🎯"""
            else:
                response_text = """현재 사용량 확인을 원하시는군요! 📊

사용량 기반 맞춤 추천은 별도 API를 이용해주세요.
'사용량 기반 추천받기' 버튼을 누르면 됩니다.
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
'타코시그널 분석받기' 버튼을 누르면
4단계 질문 받고 완전 찰떡인 타입 알려줄 수 있어~ 🐙

지금은 요금제나 구독 추천 얘기할까? 💜"""
            else:
                response_text = """UBTI 성향 분석에 관심 있으시군요! 🎯

UBTI는 전용 API를 통해 진행됩니다!
타코시그널 검사 버튼 눌러보세요!

현재는 요금제나 구독 서비스 상담을 도와드릴 수 있어요.
어떤 도움이 필요하신가요? 😊"""
            return create_simple_stream(response_text)

        # 기본 케이스 - 인사나 일반적인 대화
        else:
            print(f"[DEBUG] >>> HANDLING DEFAULT CASE FOR INTENT: {intent} <<<")
            if tone == "muneoz":
                response_text = """안뇽! 🤟 나는 무너야~ 🐙

요금제나 구독 서비스 관련해서 뭐든지 물어봐!
- 요금제 추천해줘
- 구독 서비스 추천해줘

뭘 도와줄까? 💜"""
            else:
                response_text = """안녕하세요! 😊 LG유플러스 상담 AI입니다.

다음과 같은 서비스를 도와드릴 수 있어요:
- 요금제 추천해주세요
- 구독 서비스 추천해주세요

어떤 도움이 필요하신가요?"""
            return create_simple_stream(response_text)

    except Exception as e:
        print(f"[ERROR] Intent handling failed: {e}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        return create_simple_stream(await handle_api_error_response(tone))

def _migrate_session_keys(session: dict, session_id: str):
    """기존 세션 키를 통일된 키로 마이그레이션"""
    migrated = False

    # 기존 키에서 통일된 키로 변환
    if "plan_step" in session and not session.get("phone_plan_flow_step"):
        session["phone_plan_flow_step"] = session.pop("plan_step")
        if "plan_info" in session:
            session["user_info"] = session.pop("plan_info")
        migrated = True

    if "subscription_step" in session and not session.get("subscription_flow_step"):
        session["subscription_flow_step"] = session.pop("subscription_step")
        if "subscription_info" in session:
            session["user_info"] = session.pop("subscription_info")
        migrated = True

    # 마이그레이션이 발생했으면 저장
    if migrated:
        save_session(session_id, session)
        print(f"[DEBUG] Session keys migrated successfully")

def _reset_multiturn_session(session: dict, session_id: str, flow_type: str):
    """멀티턴 세션 초기화"""
    if flow_type == "phone_plan":
        session.pop("phone_plan_flow_step", None)
        session.pop("plan_step", None)
    elif flow_type == "subscription":
        session.pop("subscription_flow_step", None)
        session.pop("subscription_step", None)

    session.pop("user_info", None)
    session.pop("plan_info", None)
    session.pop("subscription_info", None)

    save_session(session_id, session)
    print(f"[DEBUG] {flow_type} multiturn session reset")

def _should_start_plan_flow(message: str) -> bool:
    """메시지가 요금제 플로우를 시작해야 하는지 판단"""
    message_lower = message.lower()

    plan_indicators = [
        "gb", "데이터", "통화", "무제한", "5g", "lte",
        "만원", "요금", "통신비", "플랜", "너겟", "라이트", "프리미엄"
    ]

    return any(indicator in message_lower for indicator in plan_indicators)

def _should_start_subscription_flow(message: str) -> bool:
    """메시지가 구독 플로우를 시작해야 하는지 판단"""
    message_lower = message.lower()

    subscription_indicators = [
        "구독", "ott", "넷플릭스", "유튜브", "음악", "지니",
        "스포티파이", "웨이브", "드라마", "영화", "스타벅스"
    ]

    return any(indicator in message_lower for indicator in subscription_indicators)

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