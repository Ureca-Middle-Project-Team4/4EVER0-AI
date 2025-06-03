from app.schemas.chat import ChatRequest
from app.utils.intent import detect_intent
from app.chains.chat_chain import get_chain_by_intent, get_multi_turn_chain

async def handle_chat(req: ChatRequest):
    intent = await detect_intent(req.message)
    if intent == "phone_plan_multi":
        return await get_multi_turn_chain(req)
    return get_chain_by_intent(intent, req)
