from typing import Callable, Awaitable
from app.utils.redis_client import get_session, save_session
from app.db.plan_db import get_all_plans

from app.prompts.base_prompt import get_prompt_template
from app.utils.langchain_client import get_chat_model
from langchain_core.output_parsers import StrOutputParser
from app.schemas.chat import ChatRequest

QUESTION_FLOW = [
    ("data_usage", "데이터는 얼마나 사용하시나요?"),
    ("call_usage", "통화는 얼마나 사용하시나요?"),
    ("services", "자주 사용하는 서비스가 있나요? (예: 유튜브, 게임 등)"),
    ("budget", "예산은 어느 정도로 생각하고 계신가요? (예: 4만원대)")
]

def detect_intent(message: str) -> str:
    lowered = message.lower()

    if "구독" in lowered:
        return "subscription_recommend"

    if any(word in lowered for word in ["추천"]) and any(w in lowered for w in ["데이터", "통화", "서비스", "예산"]):
        return "phone_plan_multi"

    if any(word in lowered for word in ["요금제", "무제한", "5g", "lte", "영상", "전화", "얼마"]):
        return "phone_plan_recommend"

    return "default"

def get_chain_by_intent(intent: str, req: ChatRequest) -> Callable[[], Awaitable[str]]:
    session = get_session(req.session_id)
    message = req.message

    session.setdefault("history", [])
    session["history"].append({"role": "user", "content": message})

    if intent == "phone_plan_multi":
        return get_multi_turn_chain(req)

    save_session(req.session_id, session)

    user_info = session.get("user_info", {})
    if user_info:
        # 기본값 설정
        default_info = {
            "data_usage": "미설정",
            "call_usage": "미설정",
            "services": "미설정",
            "budget": "미설정"
        }
        # 기본값과 실제 값 병합
        merged_info = {**default_info, **user_info}
        user_info_text = """
- 데이터 사용량: {data_usage}
- 통화 사용량: {call_usage}
- 선호 서비스: {services}
- 예산: {budget}
        """.format(**merged_info)
    else:
        user_info_text = "사용자 정보 없음 (단발성 질문)"

    context = {
        "message": message,
        "user_info": user_info_text,
        "history": "\n".join([f"{m['role']}: {m['content']}" for m in session["history"]])
    }

    plans = get_all_plans()
    context = {
        "message": message,
        "user_info": user_info_text,
        "plans": "\n".join([f"- {p.name} / {p.price} / {p.data} / {p.voice}" for p in plans]),
        "history": "\n".join([f"{m['role']}: {m['content']}" for m in session["history"]])
    }

    # 구독 서비스 추천인 경우 products 변수 추가
    if intent == "subscription_recommend":
        from app.db.subscription_db import get_products_from_db
        products = get_products_from_db()
        context["products"] = "\n".join([f"- {p.title} / {p.price} / {p.description}" for p in products])

    prompt = get_prompt_template(intent)
    model = get_chat_model()
    chain = prompt | model | StrOutputParser()

    async def stream():
        generated_response = ""
        async for chunk in chain.astream(context):
            if chunk:
                generated_response += chunk
                yield chunk
        session["history"].append({"role": "assistant", "content": generated_response})
        save_session(req.session_id, session)

    return stream

async def get_multi_turn_chain(req: ChatRequest) -> Callable[[], Awaitable[str]]:
    session = get_session(req.session_id)
    info = session.get("user_info", {})
    message = req.message

    session.setdefault("history", [])
    session["history"].append({"role": "user", "content": message})

    for key, question in QUESTION_FLOW:
        if key not in info:
            info[key] = message
            session["user_info"] = info
            session["history"].append({"role": "assistant", "content": question})
            save_session(req.session_id, session)

            async def stream(q=question):
                for char in q:
                    yield char

            return stream

    plans = get_all_plans()
    # 기본값 설정
    default_info = {
        "data_usage": "미설정",
        "call_usage": "미설정",
        "services": "미설정",
        "budget": "미설정"
    }
    # 기본값과 실제 값 병합
    merged_info = {**default_info, **info}
    user_info_text = """
- 데이터 사용량: {data_usage}
- 통화 사용량: {call_usage}
- 선호 서비스: {services}
- 예산: {budget}
    """.format(**merged_info)

    context = {
        "user_info": user_info_text,
        "plans": "\n".join([f"- {p.name} / {p.price} / {p.data} / {p.voice}" for p in plans]),
        "message": message,
        "history": "\n".join([f"{m['role']}: {m['content']}" for m in session["history"]])
    }

    prompt = get_prompt_template("phone_plan_recommend")
    model = get_chat_model()
    chain = prompt | model | StrOutputParser()

    async def stream():
        generated_response = ""
        async for chunk in chain.astream(context):
            if chunk:
                generated_response += chunk
                yield chunk
        session["history"].append({"role": "assistant", "content": generated_response})
        save_session(req.session_id, session)

    return stream