from typing import Callable, Awaitable
import asyncio
import re
from app.utils.redis_client import get_session, save_session
from app.db.plan_db import get_all_plans
from app.db.subscription_db import get_products_from_db
from app.db.brand_db import get_life_brands_from_db

from app.utils.langchain_client import get_chat_model
from langchain_core.output_parsers import StrOutputParser
from app.schemas.chat import ChatRequest
from app.prompts.plan_prompt import PLAN_PROMPTS
from app.prompts.subscription_prompt import SUBSCRIPTION_PROMPT

# 4단계 플로우 (기존 유지)
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

UBTI_FLOW = [
    ("situation", "어떤 상황에서 제일 활발하게 활동하시나요? (예: 출근길, 저녁시간, 주말 등)"),
    ("hobby", "어떤 활동이나 취미를 가장 즐기시나요? (예: 드라마, 운동, 독서 등)"),
    ("preference", "서비스를 고를 때 가장 중요한 요소는 무엇인가요? (예: 가격, 속도, 브랜드 등)"),
    ("style", "선호하는 소통 스타일은 어떤가요? (예: 빠른 응답, 여유로운 대화 등)")
]


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

def extract_budget_from_text(text: str) -> tuple[int, int]:
    """텍스트에서 예산 범위 추출 - 개선된 한국어 처리"""
    if not text:
        return 0, 100000

    text_lower = text.lower()

    # GB/기가 관련 처리는 제거 (이 함수는 예산 전용)
    # 데이터 요구사항은 extract_data_requirement에서 처리

    # 1. 한국어 숫자 변환
    korean_numbers = {
        '일': 1, '이': 2, '삼': 3, '사': 4, '오': 5,
        '육': 6, '칠': 7, '팔': 8, '구': 9, '십': 10
    }

    # 한국어 숫자를 아라비아 숫자로 변환
    for kr, num in korean_numbers.items():
        text_lower = text_lower.replace(kr, str(num))

    print(f"[DEBUG] Budget text processing: '{text_lower}'")

    # 2. 다양한 패턴 매칭
    patterns = [
        # "5만원 이상", "50000원 넘게" - 이상 패턴 먼저
        r'(\d+)만\s*원?\s*(이상|넘|초과)',
        r'(\d{4,6})\s*원?\s*(이상|넘|초과)',
        # "5만원 이하", "50000원 미만" - 이하 패턴
        r'(\d+)만\s*원?\s*(이하|미만|까지)',
        r'(\d{4,6})\s*원?\s*(이하|미만|까지)',
        # "5만원", "50000원", "5만", "50000" - 기본 패턴
        r'(\d+)만\s*원?',
        r'(\d{4,6})\s*원?',
        # "3-5만원", "30000-50000원" - 범위 패턴
        r'(\d+)[\-~]\s*(\d+)만\s*원?',
        r'(\d{4,6})[\-~]\s*(\d{4,6})\s*원?',
    ]

    # 패턴 매칭 시도
    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            print(f"[DEBUG] Pattern matched: {pattern}")

            if len(match.groups()) == 2 and match.group(2) in ['이상', '넘', '초과']:
                # 이상 처리
                amount = int(match.group(1))
                if '만' in pattern or amount < 100:
                    amount *= 10000
                print(f"[DEBUG] '이상' detected: {amount:,}원 이상")
                return amount, 200000

            elif len(match.groups()) == 2 and match.group(2) in ['이하', '미만', '까지']:
                # 이하 처리
                amount = int(match.group(1))
                if '만' in pattern or amount < 100:
                    amount *= 10000
                print(f"[DEBUG] '이하' detected: {amount:,}원 이하")
                return 0, amount

            elif len(match.groups()) == 1:
                # 단일 숫자
                amount = int(match.group(1))
                if '만' in pattern or amount < 100:
                    amount *= 10000
                print(f"[DEBUG] Basic amount: {amount:,}원 ±5000원")
                return max(0, amount - 5000), amount + 10000

            elif len(match.groups()) >= 2:
                # 범위 지정
                min_amount = int(match.group(1))
                max_amount = int(match.group(2))
                if '만' in pattern:
                    min_amount *= 10000
                    max_amount *= 10000
                print(f"[DEBUG] Range: {min_amount:,}원 - {max_amount:,}원")
                return min_amount, max_amount

    # 3. 키워드 기반 추정
    if any(word in text_lower for word in ['저렴', '싸', '가성비', '절약']):
        print(f"[DEBUG] Keyword: 저렴")
        return 0, 35000
    elif any(word in text_lower for word in ['비싸', '프리미엄', '좋은', '고급']):
        print(f"[DEBUG] Keyword: 고급")
        return 50000, 200000
    elif any(word in text_lower for word in ['보통', '적당', '일반']):
        print(f"[DEBUG] Keyword: 보통")
        return 30000, 50000

    # 기본값: 전체 범위
    print(f"[DEBUG] Using default range")
    return 0, 100000

def extract_data_requirement(text: str) -> str:
    """텍스트에서 데이터 요구사항 추출"""
    if not text:
        return "보통"

    text_lower = text.lower()

    if any(word in text_lower for word in ['무제한', '많이', '넉넉', '여유', '빵빵', '대용량']):
        return "많이"
    elif any(word in text_lower for word in ['적게', '조금', '가볍게', '기본']):
        return "적게"
    elif re.search(r'(\d+)\s*gb', text_lower):
        gb_match = re.search(r'(\d+)\s*gb', text_lower)
        gb_amount = int(gb_match.group(1))
        if gb_amount >= 10:
            return "많이"
        elif gb_amount <= 3:
            return "적게"
        else:
            return "보통"

    return "보통"

def smart_plan_recommendation(user_info: dict, plans: list) -> list:
    """개선된 스마트 요금제 추천 - 예산과 요구사항 고려"""

    # 1. 예산 범위 추출
    budget_text = user_info.get('budget', '')
    min_budget, max_budget = extract_budget_from_text(budget_text)

    # 2. 데이터 요구사항 분석
    data_text = user_info.get('data_usage', '')
    data_need = extract_data_requirement(data_text)

    print(f"[DEBUG] Budget range: {min_budget:,}원 - {max_budget:,}원")
    print(f"[DEBUG] Data need: {data_need}")
    print(f"[DEBUG] User info: {user_info}")

    # 3. 요금제 필터링 및 점수 계산
    scored_plans = []

    for plan in plans:
        try:
            # 가격 파싱
            if isinstance(plan.price, str):
                price_clean = plan.price.replace(',', '').replace('원', '').strip()
                plan_price = int(price_clean)
            else:
                plan_price = int(plan.price)

            # 기본 점수
            score = 0

            # 예산 적합성 (50점)
            if min_budget <= plan_price <= max_budget:
                score += 60  # 예산 범위 내 = 최고점
            else:
                # 예산 범위 밖이면 거리에 따라 감점
                if plan_price < min_budget:
                    # 예산보다 싸도 너무 싸면 안 좋음 (기능 부족 가능성)
                    gap = min_budget - plan_price
                    if gap <= 5000:  # 5000원 차이까지는 OK
                        score += 40
                    else:
                        score += 20  # 너무 싸면 감점
                else:
                    # 예산 초과 시
                    gap = plan_price - max_budget
                    if gap <= 10000:  # 1만원 초과까지는 어느정도 허용
                        score += 30
                    else:
                        score += 10  # 너무 비싸면 큰 감점

            # 데이터 요구사항 (30점)
            plan_data = plan.data.lower() if plan.data else ""

            if data_need == "많이":
                if any(word in plan_data for word in ['무제한', '20gb', '15gb']):
                    score += 30
                elif any(word in plan_data for word in ['12gb', '10gb']):
                    score += 20
            elif data_need == "적게":
                if any(word in plan_data for word in ['3gb', '5gb', '8gb']):
                    score += 30
                elif '무제한' in plan_data:
                    score += 5  # 오버스펙
            if "500" in data_text or "대용량" in data_text:
                    data_need = "많이"
            else:  # 보통
                if any(word in plan_data for word in ['8gb', '10gb', '12gb']):
                    score += 30
                elif any(word in plan_data for word in ['5gb', '15gb']):
                    score += 20

            # 통화 요구사항 (10점)
            call_text = user_info.get('call_usage', '').lower()
            plan_voice = plan.voice.lower() if plan.voice else ""

            if '많이' in call_text and '무제한' in plan_voice:
                score += 10
            elif '안' in call_text and '기본' in plan_voice:
                score += 10
            else:
                score += 5

            # 인기도 보정 (10점) - 너겟 시리즈 우대
            if '너겟' in plan.name:
                score += 10
            elif '라이트' in plan.name:
                score += 5

            scored_plans.append((plan, score, plan_price))

        except Exception as e:
            print(f"[WARNING] Plan scoring failed for {plan.name}: {e}")
            scored_plans.append((plan, 0, 50000))

    # 4. 점수순 정렬 후 상위 2개 선택
    scored_plans.sort(key=lambda x: x[1], reverse=True)

    print(f"[DEBUG] Top 3 scored plans:")
    for i, (plan, score, price) in enumerate(scored_plans[:3]):
        print(f"  {i+1}. {plan.name} - Score: {score}, Price: {price:,}원")

    return [plan for plan, score, price in scored_plans[:2]]

async def natural_streaming(text: str):
    """자연스러운 타이핑 효과를 위한 스트리밍"""
    # 마크다운 파싱을 위한 줄바꿈 처리
    formatted_text = text.replace('\\n', '\n')

    words = formatted_text.split(' ')
    for i, word in enumerate(words):
        yield word
        if i < len(words) - 1:
            yield ' '
        await asyncio.sleep(0.04)  # 살짝 빠르게

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

        elif intent == "ubti":
            question_flow = UBTI_FLOW
            step_key = "ubti_step"
            user_info_key = "ubti_info"
            print(f"[DEBUG] Selected UBTI_FLOW")
        else:
            # fallback to default phone plan
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

            return create_simple_stream(question)

        # 답변 받고 다음 질문 (step 1,2,3,4)
        elif 1 <= current_step <= len(question_flow):
            print(f"[DEBUG] >>> PROCESSING STEP {current_step} <<<")

            # 현재 답변 저장
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

                return create_simple_stream(next_question)
            else:
                # 모든 질문 완료 → 최종 추천
                print(f"[DEBUG] >>> ALL QUESTIONS COMPLETED - GENERATING FINAL RECOMMENDATION <<<")

                if intent == "phone_plan_multi":
                    print(f"[DEBUG] Calling get_final_plan_recommendation")
                    return await get_final_plan_recommendation(req, user_info, tone)
                elif intent == "subscription_multi":
                    print(f"[DEBUG] Calling get_final_subscription_recommendation")
                    return await get_final_subscription_recommendation(req, user_info, tone)
                elif intent == "ubti":
                    print(f"[DEBUG] Calling get_final_ubti_result")
                    return await get_final_ubti_result(req, user_info, tone)

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
    """최종 요금제 추천 - 프롬프트 템플릿 사용 + 마크다운 줄바꿈 수정"""
    print(f"[DEBUG] get_final_plan_recommendation - tone: {tone}")
    print(f"[DEBUG] user_info: {user_info}")

    try:
        session = get_session(req.session_id)
        plans = get_all_plans()

        # 스마트 추천 적용
        recommended_plans = smart_plan_recommendation(user_info, plans)

        merged_info = {
            "data_usage": "미설정", "call_usage": "미설정",
            "services": "미설정", "budget": "미설정",
            **user_info
        }

        plans_text = "\n\n".join([f"- {p.name} ({format_price(p.price)}, {p.data}, {p.voice})" for p in recommended_plans])

        # 프롬프트 템플릿 사용
        from app.prompts.get_prompt_template import get_prompt_template
        prompt_template = get_prompt_template("phone_plan_multi", tone)

        prompt_text = prompt_template.format(
            data_usage=merged_info['data_usage'],
            call_usage=merged_info['call_usage'],
            services=merged_info['services'],
            budget=merged_info['budget'],
            plans=plans_text
        )

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
                error_msg = "요금제 추천 중 문제가 발생했어요. 😅" if tone == "general" else "앗! 추천하다가 뭔가 꼬였어! 😅"
                yield error_msg

        return stream

    except Exception as e:
        print(f"[ERROR] Final plan recommendation setup failed: {e}")
        error_text = "요금제 추천 준비 중 문제가 발생했어요. 😅"
        return create_simple_stream(error_text)

async def get_final_subscription_recommendation(req: ChatRequest, user_info: dict, tone: str = "general") -> Callable[[], Awaitable[str]]:
    """최종 구독 서비스 추천 - 프롬프트 템플릿 사용 + 마크다운 줄바꿈 수정"""
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

        main_text = "\n\n".join([f"- {s.title} ({s.category}) - {format_price(s.price)}" for s in main_items[:4]])
        life_text = "\n\n".join([f"- {b.name}" for b in life_items[:4]])

        # 프롬프트 템플릿 사용 (subscription_prompt.py에서 가져옴)
        from app.prompts.subscription_prompt import SUBSCRIPTION_PROMPT

        prompt_text = SUBSCRIPTION_PROMPT[tone].format(
            message="\n\n".join([f"- {k}: {v}" for k, v in merged_info.items()]),
            main=main_text,
            life=life_text,
            history=""
        )

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
                error_msg = "구독 서비스 추천 중 문제가 발생했어요. 😅" if tone == "general" else "앗! 추천하다가 뭔가 꼬였어! 😅"
                yield error_msg

        return stream

    except Exception as e:
        print(f"[ERROR] Final subscription recommendation setup failed: {e}")
        error_text = "구독 서비스 추천 준비 중 문제가 발생했어요. 😅"
        return create_simple_stream(error_text)

async def get_final_ubti_result(req: ChatRequest, user_info: dict, tone: str = "general"):
    print(f"[DEBUG] get_final_ubti_result - tone: {tone}")
    print(f"[DEBUG] user_info: {user_info}")

    try:
        session = get_session(req.session_id)

        # UBTI 프롬프트 준비
        from app.prompts.ubti_prompt import UBTI_PROMPT
        prompt_template = UBTI_PROMPT[tone]

        message = "\n".join([f"- {k}: {v}" for k, v in user_info.items()])

        # 데이터 준비
        ubti_types = get_all_ubti_types()
        plans = get_all_plans()
        subscriptions = get_products_from_db()
        brands = get_life_brands_from_db()

        plans_text = "\n".join([f"- ID: {p.id}, {p.name}: {p.price}원 / {p.data} / {p.voice}" for p in plans])
        subs_text = "\n".join([f"- ID: {s.id}, {s.title}: {s.category} - {s.price}원" for s in subscriptions])

        prompt_text = prompt_template.format(
            message=message,
            ubti_types="\n".join(f"{u.emoji} {u.code} - {u.name}" for u in ubti_types),
            plans=plans_text,
            subscriptions=subs_text
        )

        model = get_chat_model()

        async def stream():
            result_text = ""
            try:
                async for chunk in model.astream(prompt_text):
                    if chunk and hasattr(chunk, 'content') and chunk.content:
                        result_text += chunk.content
                        yield chunk.content
                        await asyncio.sleep(0.01)

                # 세션 정리
                session["history"].append({"role": "assistant", "content": result_text})
                session["last_recommendation_type"] = "ubti"
                session.pop("ubti_step", None)
                session.pop("ubti_info", None)
                save_session(req.session_id, session)

            except Exception as e:
                print(f"[ERROR] UBTI final recommendation failed: {e}")
                yield "UBTI 추천 중 오류가 발생했어요. 😢"

        return stream

    except Exception as e:
        print(f"[ERROR] get_final_ubti_result setup failed: {e}")
        return create_simple_stream("UBTI 추천을 준비하는 중 오류가 발생했어요.")
