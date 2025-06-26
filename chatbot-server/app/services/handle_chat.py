import asyncio
from app.schemas.chat import ChatRequest
from app.utils.intent import detect_intent
from app.chains.chat_chain import get_multi_turn_chain
from app.utils.redis_client import get_session, save_session

async def handle_chat(req: ChatRequest):
    """메모리 효율적 채팅 핸들러 - 챗봇 품질 유지"""

    tone = getattr(req, 'tone', 'general')
    print(f"[DEBUG] handle_chat: tone={tone}, msg_length={len(req.message)}")

    try:
        # 세션 로드 및 상태 확인
        session = get_session(req.session_id)

        # 멀티턴 상태 체크
        phone_step = session.get("phone_plan_flow_step", 0)
        sub_step = session.get("subscription_flow_step", 0)
        ubti_step = session.get("ubti_step", 0)

        print(f"[DEBUG] 멀티턴 상태: phone={phone_step}, sub={sub_step}, ubti={ubti_step}")

        # 멀티턴 진행 중이면 해당 체인으로 바로 이동
        if phone_step > 0:
            print(f"[DEBUG] 요금제 멀티턴 진행 중 (step: {phone_step})")
            return await get_multi_turn_chain(req, "phone_plan_multi", tone)

        elif sub_step > 0:
            print(f"[DEBUG] 구독 멀티턴 진행 중 (step: {sub_step})")
            return await get_multi_turn_chain(req, "subscription_multi", tone)

        elif ubti_step > 0:
            print(f"[DEBUG] UBTI 멀티턴 진행 중 (step: {ubti_step})")
            return await get_multi_turn_chain(req, "ubti", tone)

        # 새 대화 - 인텐트 감지 (컨텍스트 최소화)
        print(f"[DEBUG] 새 대화 시작 - 인텐트 감지")

        # 컨텍스트 간소화 (메모리 절약)
        minimal_context = {}
        if session:
            # 정말 필요한 정보만 전달
            for key in ['phone_plan_flow_step', 'subscription_flow_step']:
                if key in session and session[key] > 0:
                    minimal_context[key] = session[key]

        intent = await detect_intent(req.message, user_context=minimal_context)
        print(f"[DEBUG] 감지된 인텐트: {intent}")

        # 인텐트별 처리
        if intent == "greeting":
            return create_simple_stream(get_greeting_response(tone))

        elif intent in ["telecom_plan", "telecom_plan_direct"]:
            print(f"[DEBUG] 요금제 멀티턴 시작")
            return await get_multi_turn_chain(req, "phone_plan_multi", tone)

        elif intent == "subscription":
            print(f"[DEBUG] 구독 멀티턴 시작")
            return await get_multi_turn_chain(req, "subscription_multi", tone)

        elif intent == "ubti":
            print(f"[DEBUG] UBTI 멀티턴 시작")
            return await get_multi_turn_chain(req, "ubti", tone)

        elif intent == "current_usage":
            return create_simple_stream(get_usage_guide_response(tone))

        elif intent.startswith("off_topic") or intent == "nonsense":
            return create_simple_stream(get_off_topic_response(tone))

        else:
            return create_simple_stream(get_default_response(tone))

    except Exception as e:
        print(f"[ERROR] handle_chat 실패: {e}")
        return create_simple_stream(get_error_response(tone))

def create_simple_stream(text: str):
    """효율적 텍스트 스트리밍"""
    async def stream():
        words = text.split(' ')
        for i, word in enumerate(words):
            yield word + (" " if i < len(words) - 1 else "")
            await asyncio.sleep(0.04)  # 적절한 속도
    return stream

def get_greeting_response(tone: str) -> str:
    """인사 응답"""
    if tone == "muneoz":
        return """안뇽! 🤟 나는 LG유플러스 큐레이터 무너야~ 🐙

요금제나 구독 서비스 관련해서 뭐든지 물어봐!
• 요금제 추천해줘
• 구독 서비스 추천해줘

뭘 도와줄까? 💜"""
    else:
        return """안녕하세요! 😊 LG유플러스 상담 AI입니다.

다음과 같은 서비스를 도와드릴 수 있어요:
• 요금제 추천해주세요
• 구독 서비스 추천해주세요

어떤 도움이 필요하신가요?"""

def get_usage_guide_response(tone: str) -> str:
    """사용량 관련 안내"""
    if tone == "muneoz":
        return """현재 사용량 확인하고 싶구나! 📊

그런데 사용량 기반 추천은 다른 기능을 써야 해~
지금은 일반 요금제 추천이라도 해볼까? 💜

네 현재 상황에 딱 맞는 요금제 추천해줄 수 있어! 🎯"""
    else:
        return """현재 사용량 확인을 원하시는군요! 📊

사용량 기반 맞춤 추천은 별도 기능을 이용해주세요.
현재는 일반적인 요금제 상담을 도와드릴 수 있습니다.

원하시는 서비스가 있으시면 말씀해주세요! 😊"""

def get_off_topic_response(tone: str) -> str:
    """오프토픽 응답"""
    if tone == "muneoz":
        return """그건 나도 잘 모르겠어! 😅

나는 요금제랑 구독 서비스만 완전 자신 있거든~
이런 거 도와줄 수 있어:
• 럭키비키한 요금제 찾기
• 구독 추천

나한테 뭔가 물어봐~ 🤟💜"""
    else:
        return """죄송해요, 그 분야는 제가 도움드리기 어려워요. 😔

저는 다음과 같은 서비스를 전문적으로 제공합니다:
• 요금제 추천 및 상담
• 구독 서비스 추천

통신 관련해서 궁금한 점이 있으시면 언제든 말씀해주세요! 😊"""

def get_default_response(tone: str) -> str:
    """기본 응답"""
    if tone == "muneoz":
        return """뭔가 물어보고 싶은 게 있구나! 🤔

나는 이런 거 도와줄 수 있어:
• 요금제 추천
• 구독 서비스 추천

구체적으로 뭘 도와줄까? 💜"""
    else:
        return """무엇을 도와드릴까요? 😊

저는 다음과 같은 서비스를 제공합니다:
• 요금제 상담 및 추천
• 구독 서비스 추천

구체적인 질문을 해주시면 더 정확한 도움을 드릴 수 있어요!"""

def get_error_response(tone: str) -> str:
    """에러 응답"""
    if tone == "muneoz":
        return """어머! 뭔가 삐끗했나봐! 😵‍💫

잠깐만 기다렸다가 다시 말해봐줘~
요금제나 구독 관련 질문이면 완전 자신 있어! 🐙💜"""
    else:
        return """죄송해요, 일시적인 문제가 발생했어요. 😔

잠시 후 다시 시도해주시거나
요금제, 구독 서비스 관련 질문을 해주세요!"""