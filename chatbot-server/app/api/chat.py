from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.schemas.chat import ChatRequest
from app.services.handle_chat import handle_chat
from app.db.database import SessionLocal
from app.db.models import Plan, Subscription, Brand
from app.utils.redis_client import get_session
import json
import asyncio
import re

router = APIRouter()

def is_plan_recommendation(ai_response: str) -> bool:
    """AI 응답이 요금제 추천인지 판단 - 강화된 버전"""

    # 구독 서비스 키워드가 있으면 요금제가 아님
    subscription_keywords = ["구독", "메인 구독", "라이프 브랜드", "조합", "넷플릭스", "유튜브", "스타벅스", "OTT"]
    if any(keyword in ai_response for keyword in subscription_keywords):
        print(f"[DEBUG] Contains subscription keywords, not a plan recommendation")
        return False

    # 요금제 관련 키워드 확인
    plan_keywords = ["요금제", "너겟", "라이트", "프리미엄", "플랜", "통신비", "데이터", "통화"]
    recommendation_keywords = ["추천드립니다", "추천해드릴게", "찰떡 요금제", "완전 추천", "지리고", "럭키비키", "추천!", "딱 맞"]

    has_plan_keywords = any(keyword in ai_response for keyword in plan_keywords)
    has_recommendation_keywords = any(keyword in ai_response for keyword in recommendation_keywords)

    result = has_plan_keywords and has_recommendation_keywords
    print(f"[DEBUG] is_plan_recommendation: {result} (plan: {has_plan_keywords}, rec: {has_recommendation_keywords})")
    return result

def is_subscription_recommendation(ai_response: str) -> bool:
    """AI 응답이 구독 서비스 추천인지 판단 - 강화된 버전"""

    # 요금제 키워드가 있으면 구독 서비스가 아님
    plan_keywords = ["요금제", "너겟", "라이트", "프리미엄", "플랜", "통신비", "GB", "데이터", "통화"]
    if any(keyword in ai_response for keyword in plan_keywords):
        print(f"[DEBUG] Contains plan keywords, not a subscription recommendation")
        return False

    # 구독 서비스 관련 키워드 확인
    subscription_keywords = ["구독", "메인 구독", "라이프 브랜드", "조합", "넷플릭스", "유튜브", "스타벅스", "OTT"]
    recommendation_keywords = ["추천드립니다", "추천해드릴게", "찰떡", "완전 추천", "조합", "위 조합을 추천", "이 조합 완전", "추천!", "딱 맞"]

    has_sub_keywords = any(keyword in ai_response for keyword in subscription_keywords)
    has_recommendation_keywords = any(keyword in ai_response for keyword in recommendation_keywords)

    result = has_sub_keywords and has_recommendation_keywords
    print(f"[DEBUG] is_subscription_recommendation: {result} (sub: {has_sub_keywords}, rec: {has_recommendation_keywords})")
    return result

def extract_budget_from_text(text: str) -> tuple[int, int]:
    """텍스트에서 예산 범위 추출 - 개선된 한국어 처리"""
    if not text:
        return 0, 100000

    text_lower = text.lower().strip()

    # 1. 한국어 숫자 변환
    korean_numbers = {
        '일': 1, '이': 2, '삼': 3, '사': 4, '오': 5,
        '육': 6, '칠': 7, '팔': 8, '구': 9, '십': 10
    }

    for kr, num in korean_numbers.items():
        text_lower = text_lower.replace(kr, str(num))

    # 2. 다양한 패턴 매칭
    patterns = [
        r'(\d+)만\s*원?',          # "5만원", "5만"
        r'(\d{4,6})\s*원?',        # "50000원", "50000"
        r'(\d+)[\-~]\s*(\d+)만\s*원?',    # "3-5만원"
        r'(\d+)만\s*원?\s*(이하|미만|까지)',  # "5만원 이하"
        r'(\d+)만\s*원?\s*(이상|넘|초과)',   # "5만원 이상"
    ]

    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            if len(match.groups()) == 1:
                amount = int(match.group(1))
                if '만' in pattern:
                    amount *= 10000

                if any(word in text_lower for word in ['이하', '미만', '까지']):
                    return 0, amount
                elif any(word in text_lower for word in ['이상', '넘', '초과']):
                    return amount, 200000
                else:
                    return max(0, amount - 5000), amount + 10000

            elif len(match.groups()) >= 2:
                min_amount = int(match.group(1))
                max_amount = int(match.group(2))
                if '만' in pattern:
                    min_amount *= 10000
                    max_amount *= 10000
                return min_amount, max_amount

    # 키워드 기반 추정
    if any(word in text_lower for word in ['저렴', '싸', '가성비']):
        return 0, 35000
    elif any(word in text_lower for word in ['비싸', '프리미엄', '좋은']):
        return 50000, 200000
    elif any(word in text_lower for word in ['보통', '적당']):
        return 30000, 50000

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

def smart_plan_recommendation(ai_response: str, req: ChatRequest) -> list:
    """AI 응답과 사용자 정보를 종합한 스마트 추천"""

    db = SessionLocal()
    try:
        # 1. AI 응답에서 특정 요금제 언급 확인
        plan_mentions = []
        ai_lower = ai_response.lower()

        # AI가 구체적으로 언급한 요금제들 찾기
        plan_patterns = [
            r'너겟\s*(\d+)',
            r'라이트\s*(\d+)',
            r'프리미엄\s*(\d+)'
        ]

        # 순서를 보장하는 파싱
        mentioned_plans_ordered = []
        for pattern in plan_patterns:
            for match in re.finditer(pattern, ai_response):
                if pattern.startswith(r'너겟'):
                    plan_name = f"너겟 {match.group(1)}"
                elif pattern.startswith(r'라이트'):
                    plan_name = f"라이트 {match.group(1)}"
                else:
                    plan_name = f"프리미엄 {match.group(1)}"

                if plan_name not in mentioned_plans_ordered:
                    mentioned_plans_ordered.append(plan_name)

        if mentioned_plans_ordered:
            # AI가 언급한 순서대로 DB에서 조회
            mentioned_plans = []
            for plan_name in mentioned_plans_ordered:
                plan = db.query(Plan).filter(Plan.name == plan_name).first()
                if plan:
                    mentioned_plans.append(plan)

            if mentioned_plans:
                print(f"[DEBUG] AI mentioned specific plans in order: {[p.name for p in mentioned_plans]}")
                return mentioned_plans[:2]


        if plan_mentions:
            # AI가 구체적으로 언급한 요금제들 조회
            mentioned_plans = db.query(Plan).filter(Plan.name.in_(plan_mentions)).all()
            if mentioned_plans:
                print(f"[DEBUG] AI mentioned specific plans: {[p.name for p in mentioned_plans]}")
                return mentioned_plans[:2]

        # 2. 세션에서 사용자 정보 가져와서 스마트 추천
        session = get_session(req.session_id)
        user_info = session.get("user_info", {})

        # 메시지에서도 힌트 추출
        message_lower = req.message.lower()

        # 예산 추출
        budget_text = user_info.get('budget', '') + " " + req.message
        min_budget, max_budget = extract_budget_from_text(budget_text)

        # 데이터 요구사항 추출
        data_text = user_info.get('data_usage', '') + " " + req.message
        data_need = extract_data_requirement(data_text)

        print(f"[DEBUG] Smart recommendation - Budget: {min_budget:,}-{max_budget:,}원, Data: {data_need}")

        # 3. 모든 요금제 조회 및 점수 계산
        all_plans = db.query(Plan).all()
        scored_plans = []

        for plan in all_plans:
            try:
                # 가격 파싱
                if isinstance(plan.price, str):
                    price_clean = plan.price.replace(',', '').replace('원', '').strip()
                    plan_price = int(price_clean)
                else:
                    plan_price = int(plan.price)

                score = 0

                # 예산 적합성 (60점)
                budget_keyword = user_info.get('budget', '').lower()

                if '이상' in budget_keyword or '넘' in budget_keyword or '초과' in budget_keyword:
                    # "5만원 이상" - 더 비싼 요금제 선호
                    if plan_price >= min_budget:
                        if plan_price <= min_budget * 1.6:  # 1.6배까지는 매우 좋음
                            score += 60
                        elif plan_price <= min_budget * 2:  # 2배까지는 괜찮음
                            score += 40
                        else:
                            score += 20  # 너무 비싸면 적당히
                    else:
                        score += 10  # 예산보다 싸면 큰 감점
                elif '이하' in budget_keyword or '미만' in budget_keyword or '까지' in budget_keyword:
                    # "5만원 이하" - 더 저렴한 요금제 선호
                    if plan_price <= max_budget:
                        if plan_price >= max_budget * 0.7:  # 70% 이상이면 매우 좋음
                            score += 60
                        elif plan_price >= max_budget * 0.5:  # 50% 이상이면 괜찮음
                            score += 50
                        else:
                            score += 30  # 너무 싸면 기능 부족 우려
                    else:
                        score += 5   # 예산 초과면 큰 감점
                elif '정도' in budget_keyword or '쯤' in budget_keyword or '근처' in budget_keyword:
                    # "5만원 정도" - 정확한 예산 근처 선호
                    if min_budget <= plan_price <= max_budget:
                        score += 60  # 범위 내 최고점
                    else:
                        gap = min(abs(plan_price - min_budget), abs(plan_price - max_budget))
                        if gap <= 10000:  # 1만원 차이까지는 좋음
                            score += 45
                        elif gap <= 20000:  # 2만원 차이까지는 괜찮음
                            score += 25
                        else:
                            score += 10
                else:
                    # 일반적인 예산 범위 (키워드 없음)
                    if min_budget <= plan_price <= max_budget:
                        score += 60
                    elif plan_price < min_budget:
                        gap = min_budget - plan_price
                        if gap <= 10000:
                            score += 40
                        else:
                            score += 20
                    else:
                        over_ratio = (plan_price - max_budget) / max_budget
                        if over_ratio <= 0.3:
                            score += 30
                        else:
                            score += 10

                # 데이터 요구사항 (25점)
                plan_data = plan.data.lower() if plan.data else ""

                if data_need == "많이":
                    if any(word in plan_data for word in ['무제한', '20gb', '15gb']):
                        score += 25
                    elif any(word in plan_data for word in ['12gb', '10gb']):
                        score += 15
                elif data_need == "적게":
                    if any(word in plan_data for word in ['3gb', '5gb', '8gb']):
                        score += 25
                    elif '무제한' in plan_data:
                        score += 5  # 오버스펙
                else:  # 보통
                    if any(word in plan_data for word in ['8gb', '10gb', '12gb']):
                        score += 25

                # 인기도 및 브랜드 보정 (15점)
                if '너겟' in plan.name:
                    score += 15
                elif '라이트' in plan.name:
                    score += 10

                scored_plans.append((plan, score, plan_price))

            except Exception as e:
                print(f"[WARNING] Plan scoring failed for {plan.name}: {e}")
                scored_plans.append((plan, 0, 50000))

        # 점수순 정렬 후 상위 2개 선택
        scored_plans.sort(key=lambda x: x[1], reverse=True)

        print(f"[DEBUG] Top 3 smart recommendations:")
        for i, (plan, score, price) in enumerate(scored_plans[:3]):
            print(f"  {i+1}. {plan.name} - Score: {score}, Price: {price:,}원")

        return [plan for plan, score, price in scored_plans[:2]]

    finally:
        db.close()

def get_recommended_plans(req: ChatRequest, ai_response: str = ""):
    """스마트 요금제 추천 - AI 응답과 사용자 정보 종합"""

    print(f"[DEBUG] get_recommended_plans - analyzing: {ai_response[:200]}...")

    # 스마트 추천 적용
    recommended_plans = smart_plan_recommendation(ai_response, req)

    if recommended_plans:
        print(f"[DEBUG] Smart recommendation result: {[p.name for p in recommended_plans]}")
        return recommended_plans

    # 폴백: 기본 인기 요금제
    db = SessionLocal()
    try:
        default_plans = db.query(Plan).filter(Plan.name.in_(["너겟 30", "너겟 32"])).all()
        print(f"[DEBUG] Using default popular plans: {[p.name for p in default_plans]}")
        return default_plans
    finally:
        db.close()

def get_recommended_subscriptions(req: ChatRequest, ai_response: str):
    """AI 응답에서 구독 서비스 추천 정보 추출 - 개선된 버전"""

    db = SessionLocal()
    try:
        print(f"[DEBUG] get_recommended_subscriptions - analyzing: {ai_response[:200]}...")

        # AI 응답에서 구독 서비스와 브랜드 추출
        subscription_matches = re.findall(r'(리디|지니|왓챠|넷플릭스|유튜브|스포티파이|U\+모바일tv)', ai_response)
        brand_matches = re.findall(r'(교보문고|스타벅스|올리브영|CGV|롯데시네마)', ai_response)

        recommended_subscriptions = []

        # 1. 메인 구독 찾기
        main_subscription = None
        if subscription_matches:
            subscription_name = subscription_matches[0]
            main_subscription = db.query(Subscription).filter(
                Subscription.title.contains(subscription_name)
            ).first()

        # AI가 특정 구독을 언급하지 않았다면 메시지 기반 추천
        if not main_subscription:
            message_lower = req.message.lower()
            if any(word in message_lower for word in ["영화", "드라마", "TV"]):
                main_subscription = db.query(Subscription).filter(
                    Subscription.title.contains("넷플릭스")
                ).first()
            elif any(word in message_lower for word in ["음악", "노래"]):
                main_subscription = db.query(Subscription).filter(
                    Subscription.title.contains("지니")
                ).first()
            elif any(word in message_lower for word in ["스포츠", "축구", "야구"]):
                main_subscription = db.query(Subscription).filter(
                    Subscription.title.contains("U+모바일tv")
                ).first()
            else:
                # 기본 추천 → 넷플릭스
                main_subscription = db.query(Subscription).filter(
                    Subscription.title.contains("넷플릭스")
                ).first() or db.query(Subscription).first()

        if main_subscription:
            recommended_subscriptions.append({
                "id": main_subscription.id,
                "title": main_subscription.title,
                "image_url": main_subscription.image_url,
                "category": main_subscription.category,
                "price": main_subscription.price,
                "type": "main_subscription"
            })

        # 2. 라이프 브랜드 찾기
        life_brand = None
        if brand_matches:
            brand_name = brand_matches[0]
            life_brand = db.query(Brand).filter(
                Brand.name.contains(brand_name)
            ).first()

        if not life_brand:
            message_lower = req.message.lower()
            if any(word in message_lower for word in ["커피", "카페", "음료"]):
                life_brand = db.query(Brand).filter(
                    Brand.name.contains("스타벅스")
                ).first()
            elif any(word in message_lower for word in ["영화", "시네마"]):
                life_brand = db.query(Brand).filter(
                    Brand.name.contains("CGV")
                ).first()
            elif any(word in message_lower for word in ["책", "독서"]):
                life_brand = db.query(Brand).filter(
                    Brand.name.contains("교보문고")
                ).first()
            else:
                # 기본 추천 → 스타벅스
                life_brand = db.query(Brand).filter(
                    Brand.name.contains("스타벅스")
                ).first() or db.query(Brand).first()

        if life_brand:
            recommended_subscriptions.append({
                "id": life_brand.id,
                "name": life_brand.name,
                "image_url": life_brand.image_url,
                "description": life_brand.description,
                "type": "life_brand"
            })

        print(f"[DEBUG] Subscription combination: main={main_subscription.title if main_subscription else None}, brand={life_brand.name if life_brand else None}")

        return recommended_subscriptions if recommended_subscriptions else None

    finally:
        db.close()

@router.post("/chat")
async def chat(req: ChatRequest):
    async def generate_stream():
        # 1. handle_chat에서 스트리밍 함수 받기
        ai_stream_fn = await handle_chat(req)

        # 2. AI 응답을 모두 수집해서 분석
        full_ai_response = ""
        ai_chunks = []

        async for chunk in ai_stream_fn():
            full_ai_response += chunk
            ai_chunks.append(chunk)

        print(f"[DEBUG] Full AI response collected: '{full_ai_response[:200]}...'")

        # 3. 추천 타입 확인 및 카드 데이터 전송 (상호 배타적)
        session = get_session(req.session_id)
        last_recommendation_type = session.get("last_recommendation_type")

        print(f"[DEBUG] Last recommendation type from session: {last_recommendation_type}")

        # 4. 요금제 추천 확인 및 전송
        if (last_recommendation_type == "plan" or is_plan_recommendation(full_ai_response)):
            print(f"[DEBUG] >>> SENDING PLAN RECOMMENDATIONS <<<")
            recommended_plans = get_recommended_plans(req, full_ai_response)

            if recommended_plans:
                plan_data = {
                    "type": "plan_recommendations",
                    "plans": [
                        {
                            "id": plan.id,
                            "name": plan.name,
                            "price": plan.price,
                            "data": plan.data,
                            "voice": plan.voice,
                            "speed": plan.speed,
                            "share_data": plan.share_data,
                            "sms": plan.sms,
                            "description": plan.description
                        }
                        for plan in recommended_plans
                    ]
                }
                print(f"[DEBUG] Sending plan recommendations: {len(recommended_plans)} plans")
                yield f"data: {json.dumps(plan_data, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.1)

        # 5. 구독 서비스 추천 확인 및 전송 (요금제와 완전 분리)
        elif (last_recommendation_type == "subscription" or is_subscription_recommendation(full_ai_response)):
            print(f"[DEBUG] >>> SENDING SUBSCRIPTION RECOMMENDATIONS <<<")
            recommended_subscriptions = get_recommended_subscriptions(req, full_ai_response)

            if recommended_subscriptions:
                subscription_data = {
                    "type": "subscription_recommendations",
                    "subscriptions": recommended_subscriptions
                }
                print(f"[DEBUG] Sending subscription recommendations: {len(recommended_subscriptions)} items")
                yield f"data: {json.dumps(subscription_data, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.1)

        # 6. 스트리밍 시작 신호
        yield f"data: {json.dumps({'type': 'message_start'}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.05)

        # 7. 전체 응답을 단어 단위로 자연스럽게 스트리밍 (마크다운 파싱 지원)
        # 줄바꿈 처리
        formatted_response = full_ai_response.replace('\\n', '\n')
        words = formatted_response.split()

        for i, word in enumerate(words):
            chunk_data = {
                "type": "message_chunk",
                "content": word + (" " if i < len(words) - 1 else "")
            }
            yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.04)  # 조금 더 빠르게

        # 8. 스트리밍 완료 신호
        yield f"data: {json.dumps({'type': 'message_end'}, ensure_ascii=False)}\n\n"

        # 9. 세션 정리 (추천 타입 리셋)
        session.pop("last_recommendation_type", None)
        from app.utils.redis_client import save_session
        save_session(req.session_id, session)

    return StreamingResponse(generate_stream(), media_type="text/event-stream")