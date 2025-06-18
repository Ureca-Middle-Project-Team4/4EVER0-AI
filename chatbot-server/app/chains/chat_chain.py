from typing import Callable, Awaitable
import asyncio
from app.utils.redis_client import get_session, save_session
from app.db.plan_db import get_all_plans
from app.db.subscription_db import get_products_from_db
from app.db.brand_db import get_life_brands_from_db
from app.utils.langchain_client import get_chat_model
from langchain_core.output_parsers import StrOutputParser
from app.schemas.chat import ChatRequest

# 4단계 플로우
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

def format_price(price):
    """가격을 안전하게 포맷팅"""
    try:
        if isinstance(price, (int, float)):
            return f"{int(price):,}원"
        elif isinstance(price, str):
            if "원" in price:
                return price
            try:
                return f"{int(price):,}원"
            except ValueError:
                return f"{price}원"
        else:
            return f"{price}원"
    except Exception:
        return str(price)

async def natural_streaming(text: str):
    """자연스러운 타이핑 효과를 위한 스트리밍"""
    words = text.split(' ')
    for i, word in enumerate(words):
        yield word
        if i < len(words) - 1:
            yield ' '
        await asyncio.sleep(0.05)

def get_chain_by_intent(intent: str, req: ChatRequest, tone: str = "general"):
    """인텐트별 체인 반환 - 기본 응답만"""
    print(f"[DEBUG] get_chain_by_intent - intent: {intent}, tone: {tone}")

    session = get_session(req.session_id)
    message = req.message
    session.setdefault("history", [])
    session["history"].append({"role": "user", "content": message})

    if intent == "default":
        if tone == "muneoz":
            default_text = """안뇽! 🤟 나는 LG유플러스 큐레이터 무너야~ 🐙

요금제나 구독 서비스 관련해서 뭐든지 물어봐!
• 요금제 추천해줘
• 구독 서비스 추천해줘

뭘 도와줄까? 💜"""
        else:
            default_text = """안녕하세요! 😊 LG유플러스 상담 AI입니다.

다음과 같은 서비스를 도와드릴 수 있어요:
• 요금제 추천해주세요
• 구독 서비스 추천해주세요

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
어떤 도움이 필요하신가요?"""
        return create_simple_stream(greeting_text)

    save_session(req.session_id, session)
    return create_simple_stream("안녕하세요! 무엇을 도와드릴까요? 😊")

async def get_multi_turn_chain(req: ChatRequest, intent: str, tone: str = "general") -> Callable[[], Awaitable[str]]:
    """통일된 세션 키를 사용하는 멀티턴 체인"""

    print(f"[DEBUG] ========== GET_MULTI_TURN_CHAIN START ==========")
    print(f"[DEBUG] Input - intent: '{intent}', tone: '{tone}', message: '{req.message}'")

    try:
        session = get_session(req.session_id)
        message = req.message.strip()

        # 통일된 세션 키 사용
        if intent == "phone_plan_multi":
            question_flow = PHONE_PLAN_FLOW.get(tone, PHONE_PLAN_FLOW["general"])
            step_key = "phone_plan_flow_step"
            user_info_key = "user_info"
            print(f"[DEBUG] Selected PHONE_PLAN_FLOW for tone '{tone}'")
        elif intent == "subscription_multi":
            question_flow = SUBSCRIPTION_FLOW.get(tone, SUBSCRIPTION_FLOW["general"])
            step_key = "subscription_flow_step"
            user_info_key = "user_info"
            print(f"[DEBUG] Selected SUBSCRIPTION_FLOW for tone '{tone}'")
        else:
            question_flow = PHONE_PLAN_FLOW.get(tone, PHONE_PLAN_FLOW["general"])
            step_key = "phone_plan_flow_step"
            user_info_key = "user_info"
            print(f"[DEBUG] Default to PHONE_PLAN_FLOW for unknown intent '{intent}'")

        print(f"[DEBUG] Using step_key: '{step_key}', user_info_key: '{user_info_key}'")

        # 현재 단계 확인 - 기존 키와 통합
        current_step = session.get(step_key, 0)

        # 기존 키에서 마이그레이션
        if current_step == 0:
            if intent == "phone_plan_multi" and session.get("plan_step", 0) > 0:
                current_step = session.get("plan_step", 0)
                session[step_key] = current_step
                session[user_info_key] = session.get("plan_info", {})
                # 기존 키 제거
                session.pop("plan_step", None)
                session.pop("plan_info", None)
            elif intent == "subscription_multi" and session.get("subscription_step", 0) > 0:
                current_step = session.get("subscription_step", 0)
                session[step_key] = current_step
                session[user_info_key] = session.get("subscription_info", {})
                # 기존 키 제거
                session.pop("subscription_step", None)
                session.pop("subscription_info", None)

        user_info = session.get(user_info_key, {})

        print(f"[DEBUG] Current step: {current_step}, user_info: {user_info}")

        # 첫 번째 질문 (step 0 → step 1)
        if current_step == 0:
            print(f"[DEBUG] >>> STARTING NEW MULTI-TURN FLOW <<<")

            # 첫 번째 질문 가져오기
            key, question = question_flow[0]
            print(f"[DEBUG] First question - key: '{key}', question: '{question}'")

            # 단계 증가: 0 → 1
            session[step_key] = 1
            session.setdefault("history", [])
            session["history"].append({"role": "user", "content": message})
            session["history"].append({"role": "assistant", "content": question})
            save_session(req.session_id, session)

            print(f"[DEBUG] Updated {step_key} to 1")

            async def stream():
                async for chunk in natural_streaming(question):
                    yield chunk
            return stream

        # 🔥 답변 받고 다음 질문 (step 1,2,3,4)
        elif 1 <= current_step <= len(question_flow):
            print(f"[DEBUG] >>> PROCESSING STEP {current_step} <<<")

            # 🔥 현재 답변 저장
            answer_index = current_step - 1
            if answer_index < len(question_flow):
                answer_key = question_flow[answer_index][0]
                user_info[answer_key] = message
                session[user_info_key] = user_info
                session.setdefault("history", [])
                session["history"].append({"role": "user", "content": message})

                print(f"[DEBUG] Saved answer for '{answer_key}': '{message}'")

            # 다음 질문이 있는지 확인
            if current_step < len(question_flow):
                # 다음 질문 가져오기
                next_key, next_question = question_flow[current_step]
                print(f"[DEBUG] Next question - key: '{next_key}', question: '{next_question}'")

                # 단계 증가
                session[step_key] = current_step + 1
                session["history"].append({"role": "assistant", "content": next_question})
                save_session(req.session_id, session)

                print(f"[DEBUG] Updated {step_key} to {current_step + 1}")

                async def stream():
                    async for chunk in natural_streaming(next_question):
                        yield chunk
                return stream
            else:
                # 모든 질문 완료 → 최종 추천
                print(f"[DEBUG] >>> ALL QUESTIONS COMPLETED - GENERATING FINAL RECOMMENDATION <<<")

                if intent == "phone_plan_multi":
                    print(f"[DEBUG] Calling get_final_plan_recommendation")
                    return await get_final_plan_recommendation(req, user_info, tone)
                elif intent == "subscription_multi":
                    print(f"[DEBUG] Calling get_final_subscription_recommendation")
                    return await get_final_subscription_recommendation(req, user_info, tone)

        # 플로우 완료 후 추가 메시지 처리
        else:
            print(f"[DEBUG] >>> FLOW COMPLETED, HANDLING NEW MESSAGE <<<")
            # 플로우 초기화하고 새로운 대화로 처리
            session.pop(step_key, None)
            session.pop(user_info_key, None)
            save_session(req.session_id, session)

            # 새로운 메시지를 다시 인텐트 분류로 보냄
            from app.utils.intent import detect_intent
            new_intent = await detect_intent(message)

            if new_intent in ["telecom_plan", "telecom_plan_direct"]:
                return await get_multi_turn_chain(req, "phone_plan_multi", tone)
            elif new_intent == "subscription":
                return await get_multi_turn_chain(req, "subscription_multi", tone)
            else:
                if tone == "muneoz":
                    response = "또 다른 얘기 하고 싶어? 🤟\n요금제나 구독 서비스 관련해서 물어봐~ 💜"
                else:
                    response = "새로운 문의가 있으시면 말씀해주세요! 😊\n요금제나 구독 서비스 상담을 도와드릴게요."
                return create_simple_stream(response)

    except Exception as e:
        print(f"[ERROR] Multi-turn chain failed: {e}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")

        # 에러 발생 시 플로우 초기화
        session = get_session(req.session_id)
        session.pop("phone_plan_flow_step", None)
        session.pop("subscription_flow_step", None)
        session.pop("plan_step", None)
        session.pop("subscription_step", None)
        session.pop("user_info", None)
        session.pop("plan_info", None)
        session.pop("subscription_info", None)
        save_session(req.session_id, session)

        error_text = "질문 과정에서 문제가 발생했어요. 처음부터 다시 시작해주세요! 😅" if tone == "general" else "앗! 뭔가 꼬였나봐! 처음부터 다시 해보자~ 😵"
        return create_simple_stream(error_text)

async def get_final_plan_recommendation(req: ChatRequest, user_info: dict, tone: str = "general"):
    """최종 요금제 추천"""
    print(f"[DEBUG] get_final_plan_recommendation - tone: {tone}")
    print(f"[DEBUG] user_info: {user_info}")

    try:
        session = get_session(req.session_id)
        plans = get_all_plans()

        merged_info = {
            "data_usage": "미설정", "call_usage": "미설정",
            "services": "미설정", "budget": "미설정",
            **user_info
        }

        # 간소화된 프롬프트
        plans_text = "\n".join([f"- {p.name} ({format_price(p.price)}, {p.data}, {p.voice})" for p in plans[:6]])

        if tone == "muneoz":
            prompt_text = f"""무너가 4단계 질문 답변 보고 완전 찰떡인 요금제 골라봤어! 🐙

답변:
- 데이터: {merged_info['data_usage']}
- 통화: {merged_info['call_usage']}
- 서비스: {merged_info['services']}
- 예산: {merged_info['budget']}

요금제:
{plans_text}

딱 맞는 요금제 1-2개 추천하고 "완전 추천!"으로 끝내줘."""

        else:
            prompt_text = f"""4단계 질문 답변을 바탕으로 최적 요금제를 추천드립니다.

고객님 답변:
- 데이터 사용량: {merged_info['data_usage']}
- 통화 사용량: {merged_info['call_usage']}
- 주요 서비스: {merged_info['services']}
- 예산: {merged_info['budget']}

추천 요금제:
{plans_text}

적합한 요금제 1-2개를 추천하고 "추천드립니다"로 마무리해주세요."""

        model = get_chat_model()

        async def stream():
            generated_response = ""
            try:
                async for chunk in model.astream(prompt_text):
                    if chunk and hasattr(chunk, 'content') and chunk.content:
                        generated_response += chunk.content
                        yield chunk.content
                        await asyncio.sleep(0.01)

                # 최종 추천 완료 처리
                session["history"].append({"role": "assistant", "content": generated_response})
                session["last_recommendation_type"] = "plan"
                # 플로우 완전 초기화
                session.pop("phone_plan_flow_step", None)
                session.pop("plan_step", None)
                session.pop("user_info", None)
                session.pop("plan_info", None)
                save_session(req.session_id, session)

                print(f"[DEBUG] Plan recommendation completed, flow reset")

            except Exception as e:
                print(f"[ERROR] Final plan recommendation failed: {e}")
                yield "요금제 추천 중 문제가 발생했어요. 😅"

        return stream

    except Exception as e:
        print(f"[ERROR] Final plan recommendation setup failed: {e}")
        error_text = "요금제 추천 준비 중 문제가 발생했어요. 😅"
        return create_simple_stream(error_text)

async def get_final_subscription_recommendation(req: ChatRequest, user_info: dict, tone: str = "general") -> Callable[[], Awaitable[str]]:
    """최종 구독 서비스 추천"""
    print(f"[DEBUG] get_final_subscription_recommendation - tone: {tone}")
    print(f"[DEBUG] user_info: {user_info}")

    try:
        session = get_session(req.session_id)
        main_items = get_products_from_db()
        life_items = get_life_brands_from_db()

        merged_info = {
            "content_type": "미설정", "device_usage": "미설정",
            "time_usage": "미설정", "preference": "미설정",
            **user_info
        }

        # 간소화된 프롬프트
        main_text = "\n".join([f"- {s.title} ({s.category}) - {format_price(s.price)}" for s in main_items[:4]])
        life_text = "\n".join([f"- {b.name}" for b in life_items[:4]])

        if tone == "muneoz":
            prompt_text = f"""무너가 4단계 답변 보고 완전 찰떡인 구독 조합 골라봤어! 🐙

답변:
- 콘텐츠: {merged_info['content_type']}
- 기기: {merged_info['device_usage']}
- 시간: {merged_info['time_usage']}
- 선호: {merged_info['preference']}

메인구독:
{main_text}

라이프브랜드:
{life_text}

메인 1개 + 라이프 1개 조합 추천하고 "완전 추천!"으로 끝내줘."""

        else:
            prompt_text = f"""4단계 질문 답변을 바탕으로 최적 구독 조합을 추천드립니다.

고객님 답변:
- 선호 콘텐츠: {merged_info['content_type']}
- 주요 기기: {merged_info['device_usage']}
- 이용 시간: {merged_info['time_usage']}
- 기타 선호: {merged_info['preference']}

메인 구독:
{main_text}

라이프 브랜드:
{life_text}

메인 구독 1개 + 라이프 브랜드 1개 조합을 추천하고 "추천드립니다"로 마무리해주세요."""

        model = get_chat_model()

        async def stream():
            generated_response = ""
            try:
                async for chunk in model.astream(prompt_text):
                    if chunk and hasattr(chunk, 'content') and chunk.content:
                        generated_response += chunk.content
                        yield chunk.content
                        await asyncio.sleep(0.01)

                # 최종 추천 완료 처리
                session["history"].append({"role": "assistant", "content": generated_response})
                session["last_recommendation_type"] = "subscription"
                # 플로우 완전 초기화
                session.pop("subscription_flow_step", None)
                session.pop("subscription_step", None)
                session.pop("user_info", None)
                session.pop("subscription_info", None)
                save_session(req.session_id, session)

                print(f"[DEBUG] Subscription recommendation completed, flow reset")

            except Exception as e:
                print(f"[ERROR] Final subscription recommendation failed: {e}")
                yield "구독 서비스 추천 중 문제가 발생했어요. 😅"

        return stream

    except Exception as e:
        print(f"[ERROR] Final subscription recommendation setup failed: {e}")
        error_text = "구독 서비스 추천 준비 중 문제가 발생했어요. 😅"
        return create_simple_stream(error_text)