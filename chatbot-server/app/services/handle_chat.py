# app/services/handle_chat.py
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
    """향상된 채팅 핸들러 - 자연스러운 대화 플로우"""
    
    tone = getattr(req, 'tone', 'general')
    print(f"[DEBUG] Enhanced handle_chat - tone: {tone}, message: {req.message}")

    # 1. 세션에서 멀티턴 진행 상태 확인
    session = get_session(req.session_id)
    phone_plan_step = session.get("phone_plan_flow_step", 0)
    subscription_step = session.get("subscription_flow_step", 0)

    # 2. 멀티턴이 진행 중이면 해당 플로우 계속 진행
    if phone_plan_step > 0:
        print(f"[DEBUG] Continuing phone_plan_multi flow")
        return await get_multi_turn_chain(req, "phone_plan_multi", tone)
    elif subscription_step > 0:
        print(f"[DEBUG] Continuing subscription_multi flow")
        return await get_multi_turn_chain(req, "subscription_multi", tone)

    # 3. 새로운 대화 - AI 기반 인텐트 감지
    intent = await detect_intent(req.message)
    print(f"[DEBUG] AI detected intent: {intent}")

    # 4. 인텐트별 처리
    if intent == "off_topic":
        response_text = await handle_off_topic_response(req.message, tone)
        return create_simple_stream(response_text)
        
    elif intent == "tech_issue":
        response_text = await handle_tech_issue_response(req.message, tone)
        return create_simple_stream(response_text)
        
    elif intent == "greeting":
        return get_chain_by_intent("greeting", req, tone)
        
    elif intent == "current_usage":
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
        
    elif intent in ["telecom_plan", "telecom_plan_direct"]:
        # telecom_plan_direct면 바로 추천, telecom_plan이면 멀티턴
        if intent == "telecom_plan_direct":
            return get_chain_by_intent("phone_plan_recommend", req, tone)
        else:
            return await get_multi_turn_chain(req, "phone_plan_multi", tone)
            
    elif intent == "subscription":
        return get_chain_by_intent("subscription_recommend", req, tone)
        
    elif intent == "ubti":
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
        # 기본 응답
        return get_chain_by_intent("default", req, tone)