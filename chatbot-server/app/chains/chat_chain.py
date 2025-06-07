from typing import Callable, Awaitable
from app.utils.redis_client import get_session, save_session
from app.db.plan_db import get_all_plans
from app.prompts.get_prompt_template import get_prompt_template
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
    default_info = {"data_usage": "미설정", "call_usage": "미설정", "services": "미설정", "budget": "미설정"}
    merged_info = {**default_info, **user_info}
    user_info_text = f"""\
- 데이터 사용량: {merged_info['data_usage']}
- 통화 사용량: {merged_info['call_usage']}
- 선호 서비스: {merged_info['services']}
- 예산: {merged_info['budget']}
"""

    context = {
        "message": message,
        "user_info": user_info_text,
        "history": "\n".join([f"{m['role']}: {m['content']}" for m in session["history"]])
    }

    if intent.startswith("phone_plan"):
        plans = get_all_plans()
        context["plans"] = "\n".join([f"- {p.name} / {p.price} / {p.data} / {p.voice}" for p in plans])

    elif intent == "subscription_recommend":
        from app.db.subscription_db import get_products_from_db
        from app.db.brand_db import get_life_brands_from_db

        # 1. 메인 구독 상품 전체 조회
        main_items = get_products_from_db()

        # 2. 라이프 브랜드 전체 조회
        life_items = get_life_brands_from_db()

        # 3. LangChain 컨텍스트에 문자열로 포맷
        context["main"] = "\n".join([
            f"- {p.title} ({p.category}) - {p.price}원" for p in main_items
        ])
        context["life"] = "\n".join([
            f"- {b.name}" for b in life_items
        ])


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

    next_question = None

    for key, question in QUESTION_FLOW:
        if key not in info or info[key].lower() in ["요금제추천", "추천", "몰라요", ""]:
            if key not in info:
                session["history"].append({"role": "assistant", "content": question})
            else:
                question = f"조금 더 구체적으로 알려주실 수 있나요? {question}"
                session["history"].append({"role": "assistant", "content": question})
            save_session(req.session_id, session)
            next_question = question
            break
        else:
            info[key] = message
            session["user_info"] = info

    # 중간에 재질문이 필요했다면
    if next_question:
        async def stream():
            for char in next_question:
                yield char
        return stream

    # 모든 질문 완료 → 요금제 추천
    plans = get_all_plans()
    merged_info = {**{"data_usage": "미설정", "call_usage": "미설정", "services": "미설정", "budget": "미설정"}, **info}
    user_info_text = f"""\
- 데이터 사용량: {merged_info['data_usage']}
- 통화 사용량: {merged_info['call_usage']}
- 선호 서비스: {merged_info['services']}
- 예산: {merged_info['budget']}
"""
    context = {
        "user_info": user_info_text,
        "plans": "\n".join([f"- {p.name} / {p.price} / {p.data} / {p.voice}" for p in plans]),
        "message": message,
        "history": "\n".join([f"{m['role']}: {m['content']}" for m in session["history"]])
    }

    prompt = get_prompt_template("phone_plan_multi")
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



    # 모든 질문 완료 후 요금제 추천
    plans = get_all_plans()
    merged_info = {**{"data_usage": "미설정", "call_usage": "미설정", "services": "미설정", "budget": "미설정"}, **info}
    user_info_text = f"""\
- 데이터 사용량: {merged_info['data_usage']}
- 통화 사용량: {merged_info['call_usage']}
- 선호 서비스: {merged_info['services']}
- 예산: {merged_info['budget']}
"""

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
