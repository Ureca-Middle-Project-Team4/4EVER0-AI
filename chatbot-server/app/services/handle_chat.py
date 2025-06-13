from app.schemas.chat import ChatRequest
from app.utils.intent import detect_intent
from app.chains.chat_chain import get_chain_by_intent, get_multi_turn_chain
from app.utils.redis_client import get_session

async def handle_chat(req: ChatRequest):
    # tone 파라미터 추출 및 디버깅
    tone = getattr(req, 'tone', 'general')
    print(f"[DEBUG] handle_chat - received tone: {tone}")

    # 먼저 세션에서 멀티턴 진행 상태 확인
    session = get_session(req.session_id)

    # 요금제 멀티턴이 진행 중인지 확인
    phone_plan_step = session.get("phone_plan_flow_step", 0)
    subscription_step = session.get("subscription_flow_step", 0)

    print(f"[DEBUG] Session check - phone_plan_step: {phone_plan_step}, subscription_step: {subscription_step}")

    # 멀티턴이 진행 중이면 해당 플로우 계속 진행
    if phone_plan_step > 0:
        print(f"[DEBUG] Continuing phone_plan_multi flow with tone: {tone}")
        return await get_multi_turn_chain(req, "phone_plan_multi", tone)  # tone 추가!
    elif subscription_step > 0:
        print(f"[DEBUG] Continuing subscription_multi flow with tone: {tone}")
        return await get_multi_turn_chain(req, "subscription_multi", tone)  # tone 추가!

    # 새로운 대화 시작 - 인텐트 감지
    intent = await detect_intent(req.message)
    print(f"[DEBUG] New conversation - detected intent: {intent}, tone: {tone}")

    # 멀티턴 인텐트들은 get_multi_turn_chain 사용
    if intent in ["phone_plan_multi", "subscription_multi"]:
        print(f"[DEBUG] Starting multiturn with intent: {intent}, tone: {tone}")
        return await get_multi_turn_chain(req, intent, tone)  # tone 추가!

    # 일반 대화는 get_chain_by_intent 사용
    print(f"[DEBUG] Single turn conversation with intent: {intent}, tone: {tone}")
    return get_chain_by_intent(intent, req, tone)  # tone 추가!