# app/chains/chat_chain.py (완전 재작성)
from typing import Callable, Awaitable
import asyncio
from app.utils.redis_client import get_session, save_session
from app.db.plan_db import get_all_plans
from app.prompts.get_prompt_template import get_prompt_template
from app.utils.langchain_client import get_chat_model
from langchain_core.output_parsers import StrOutputParser
from app.schemas.chat import ChatRequest

PHONE_PLAN_FLOW = {
    "general": [
        ("data_usage", "데이터는 얼마나 사용하시나요?\n\n(예: 5GB, 무제한, 많이 사용해요)"),
        ("call_usage", "통화는 얼마나 사용하시나요?\n\n(예: 거의 안해요, 1시간 정도, 많이 해요)"),
        ("services", "자주 사용하는 서비스가 있나요?\n\n(예: 유튜브, 게임, SNS, 업무용)"),
        ("budget", "예산은 어느 정도로 생각하고 계신가요?\n\n(예: 3만원대, 5만원 이하)")
    ],
    "muneoz": [
        ("data_usage", "데이터 얼마나 써? 🤟\n\n(예: 5GB, 무제한, 많이 써요)"),
        ("call_usage", "통화는 얼마나 해? 📞\n\n(예: 거의 안해, 1시간 정도, 많이 해)"),
        ("services", "자주 쓰는 서비스 있어? 📱\n\n(예: 유튜브, 게임, SNS, 업무용)"),
        ("budget", "예산은 얼마 정도 생각하고 있어? 💰\n\n(예: 3만원대, 5만원 이하)")
    ]
}

SUBSCRIPTION_FLOW = {
    "general": [
        ("content_type", "어떤 콘텐츠를 주로 즐기시나요?\n\n(예: 드라마, 영화, 음악, 스포츠)"),
        ("device_usage", "주로 어떤 기기로 보시나요?\n\n(예: 스마트폰, TV, 태블릿)"),
        ("time_usage", "언제 주로 시청하시나요?\n\n(예: 출퇴근시간, 저녁시간, 주말)"),
        ("preference", "선호하는 장르나 특별히 관심있는 브랜드가 있나요?\n\n(예: 액션, 로맨스, 특정 채널)")
    ],
    "muneoz": [
        ("content_type", "뭘 주로 봐? 🎬\n\n(예: 드라마, 영화, 음악, 스포츠)"),
        ("device_usage", "주로 뭘로 봐? 📱\n\n(예: 스마트폰, TV, 태블릿)"),
        ("time_usage", "언제 주로 봐? ⏰\n\n(예: 출퇴근시간, 저녁시간, 주말)"),
        ("preference", "좋아하는 장르나 특별히 관심있는 브랜드 있어? 💜\n\n(예: 액션, 로맨스, 특정 채널)")
    ]
}

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

async def natural_streaming(text: str):
    """자연스러운 타이핑 효과를 위한 스트리밍"""
    words = text.split(' ')
    for i, word in enumerate(words):
        yield word
        if i < len(words) - 1:
            yield ' '
        # 자연스러운 타이핑 속도
        await asyncio.sleep(0.05)

def get_chain_by_intent(intent: str, req: ChatRequest, tone: str = "general"):
    """인텐트별 체인 반환"""
    print(f"[DEBUG] get_chain_by_intent - intent: {intent}, tone: {tone}")

    session = get_session(req.session_id)
    message = req.message
    session.setdefault("history", [])
    session["history"].append({"role": "user", "content": message})

    # 기본 응답들 처리
    if intent == "default":
        if tone == "muneoz":
            default_text = """안뇽! 🤟 나는 LG유플러스 큐레이터 무너야~ 🐙

요금제나 구독 서비스 관련해서 뭐든지 물어봐!
• 요금제 추천
• 구독 서비스 추천  
• UBTI 성향 분석
• 현재 사용량 체크

뭘 도와줄까? 💜"""
        else:
            default_text = """안녕하세요! 😊 LG유플러스 상담 AI입니다.

다음과 같은 서비스를 도와드릴 수 있어요:
• 요금제 추천 상담
• 구독 서비스 추천
• UBTI 성향 분석 안내
• 현재 사용량 기반 추천 안내

어떤 도움이 필요하신가요?"""
        return create_simple_stream(default_text)

    elif intent == "greeting":
        if tone == "muneoz":
            greeting_text = """안뇽! 🤟 나는 무너야~ 🐙

요금제랑 구독 전문가라서 완전 자신 있어!

뭐든지 편하게 물어봐~ 💜"""
        else:
            greeting_text = """안녕하세요, 고객님! 😊

저는 LG유플러스 AI 상담사입니다.

요금제 추천부터 구독 서비스까지 도와드릴 수 있어요!

어떤 도움이 필요하신가요?"""
        return create_simple_stream(greeting_text)

    # 기존 로직 계속
    save_session(req.session_id, session)

    user_info = session.get("user_info", {})
    default_info = {"data_usage": "미설정", "call_usage": "미설정", "services": "미설정", "budget": "미설정"}
    merged_info = {**default_info, **user_info}
    user_info_text = f"""- 데이터 사용량: {merged_info['data_usage']}\\n\\n- 통화 사용량: {merged_info['call_usage']}\\n\\n- 선호 서비스: {merged_info['services']}\\n\\n- 예산: {merged_info['budget']}"""

    context = {
        "message": message,
        "user_info": user_info_text,
        "history": "\\n\\n".join([f"{m['role']}: {m['content']}" for m in session["history"]])
    }

    if intent.startswith("phone_plan"):
        plans = get_all_plans()
        context["plans"] = "\\n\\n".join([f"- {p.name} / {p.price} / {p.data} / {p.voice}" for p in plans])

    elif intent == "subscription_recommend":
        from app.db.subscription_db import get_products_from_db
        from app.db.brand_db import get_life_brands_from_db

        main_items = get_products_from_db()
        life_items = get_life_brands_from_db()

        context["main"] = "\\n\\n".join([
            f"- {p.title} ({p.category}) - {p.price}원" for p in main_items
        ])
        context["life"] = "\\n\\n".join([
            f"- {b.name}" for b in life_items
        ])

    # tone을 고려한 프롬프트 선택
    prompt = get_prompt_template(intent, tone)
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

async def get_multi_turn_chain(req: ChatRequest, intent: str, tone: str = "general") -> Callable[[], Awaitable[str]]:
    """멀티턴 체인 처리"""
    print(f"[DEBUG] get_multi_turn_chain - intent: {intent}, tone: {tone}")

    session = get_session(req.session_id)
    message = req.message

    # 인텐트별 질문 플로우 선택
    if intent == "phone_plan_multi":
        question_flow = PHONE_PLAN_FLOW.get(tone, PHONE_PLAN_FLOW["general"])
        flow_key = "phone_plan_flow"
    elif intent == "subscription_multi":
        question_flow = SUBSCRIPTION_FLOW.get(tone, SUBSCRIPTION_FLOW["general"])
        flow_key = "subscription_flow"
    else:
        question_flow = PHONE_PLAN_FLOW.get(tone, PHONE_PLAN_FLOW["general"])
        flow_key = "phone_plan_flow"

    # 현재 단계 확인
    current_step = session.get(f"{flow_key}_step", 0)
    user_info = session.get("user_info", {})

    print(f"[DEBUG] Intent: {intent}, Current Step: {current_step}, Message: {message}")

    # 첫 번째 메시지가 멀티턴 시작인 경우
    if current_step == 0:
        key, question = question_flow[0]
        session[f"{flow_key}_step"] = 1
        session.setdefault("history", [])
        session["history"].append({"role": "user", "content": message})
        session["history"].append({"role": "assistant", "content": question})
        save_session(req.session_id, session)

        print(f"[DEBUG] Starting multiturn flow, asking first question")

        async def stream():
            async for chunk in natural_streaming(question):
                yield chunk
        return stream

    # 이전 답변 저장하고 다음 질문
    elif current_step > 0 and current_step <= len(question_flow):
        # 이전 질문의 답변 저장
        prev_key = question_flow[current_step - 1][0]
        user_info[prev_key] = message
        session["user_info"] = user_info
        session.setdefault("history", [])
        session["history"].append({"role": "user", "content": message})

        print(f"[DEBUG] Saved {prev_key}: {message}")

        # 다음 질문이 있는지 확인
        if current_step < len(question_flow):
            key, question = question_flow[current_step]
            session[f"{flow_key}_step"] = current_step + 1
            session["history"].append({"role": "assistant", "content": question})
            save_session(req.session_id, session)

            print(f"[DEBUG] Asking next question (step {current_step + 1})")

            async def stream():
                async for chunk in natural_streaming(question):
                    yield chunk
            return stream
        else:
            # 모든 질문 완료 → 최종 추천
            print(f"[DEBUG] All questions completed. Generating final recommendation...")

            if intent == "phone_plan_multi":
                return await get_final_plan_recommendation(req, user_info, tone)
            elif intent == "subscription_multi":
                return await get_final_subscription_recommendation(req, user_info, tone)

    # 안전장치
    print(f"[DEBUG] Unexpected flow state - falling back to final recommendation")
    if intent == "phone_plan_multi":
        return await get_final_plan_recommendation(req, user_info, tone)
    elif intent == "subscription_multi":
        return await get_final_subscription_recommendation(req, user_info, tone)

async def get_final_plan_recommendation(req: ChatRequest, user_info: dict, tone: str = "general"):
    """최종 요금제 추천"""
    print(f"[DEBUG] get_final_plan_recommendation - tone: {tone}")

    session = get_session(req.session_id)
    plans = get_all_plans()

    merged_info = {
        "data_usage": "미설정", "call_usage": "미설정",
        "services": "미설정", "budget": "미설정",
        **user_info
    }

    user_info_text = f"""- 데이터 사용량: {merged_info['data_usage']}\\n\\n- 통화 사용량: {merged_info['call_usage']}\\n\\n- 선호 서비스: {merged_info['services']}\\n\\n- 예산: {merged_info['budget']}"""

    context = {
        "user_info": user_info_text,
        "plans": "\\n\\n".join([f"- {p.name} / {p.price} / {p.data} / {p.voice}" for p in plans]),
        "message": req.message,
        "history": "\\n\\n".join([f"{m['role']}: {m['content']}" for m in session["history"]])
    }

    prompt = get_prompt_template("phone_plan_multi", tone)
    model = get_chat_model()
    chain = prompt | model | StrOutputParser()

    async def stream():
        generated_response = ""
        async for chunk in chain.astream(context):
            if chunk:
                generated_response += chunk
                yield chunk
                await asyncio.sleep(0.01)

        session["history"].append({"role": "assistant", "content": generated_response})
        # 플로우 완료 후 초기화
        session.pop("phone_plan_flow_step", None)
        save_session(req.session_id, session)

    return stream

async def get_final_subscription_recommendation(req: ChatRequest, user_info: dict, tone: str = "general") -> Callable[[], Awaitable[str]]:
    """최종 구독 서비스 추천"""
    print(f"[DEBUG] get_final_subscription_recommendation - tone: {tone}")

    session = get_session(req.session_id)

    from app.db.subscription_db import get_products_from_db
    from app.db.brand_db import get_life_brands_from_db

    main_items = get_products_from_db()
    life_items = get_life_brands_from_db()

    merged_info = {
        "content_type": "미설정", "device_usage": "미설정",
        "time_usage": "미설정", "preference": "미설정",
        **user_info
    }

    user_info_text = f"""- 선호 콘텐츠: {merged_info['content_type']}\\n\\n- 사용 기기: {merged_info['device_usage']}\\n\\n- 시청 시간: {merged_info['time_usage']}\\n\\n- 선호 장르/브랜드: {merged_info['preference']}"""

    context = {
        "main": "\\n\\n".join([f"- {p.title} ({p.category}) - {p.price}원" for p in main_items]),
        "life": "\\n\\n".join([f"- {b.name}" for b in life_items]),
        "user_info": user_info_text,
        "message": req.message,
        "history": "\\n\\n".join([f"{m['role']}: {m['content']}" for m in session["history"]])
    }

    prompt = get_prompt_template("subscription_recommend", tone)
    model = get_chat_model()
    chain = prompt | model | StrOutputParser()

    async def stream():
        generated_response = ""
        async for chunk in chain.astream(context):
            if chunk:
                generated_response += chunk
                yield chunk
                await asyncio.sleep(0.01)

        session["history"].append({"role": "assistant", "content": generated_response})
        # 플로우 완료 후 초기화
        session.pop("subscription_flow_step", None)
        save_session(req.session_id, session)

    return stream