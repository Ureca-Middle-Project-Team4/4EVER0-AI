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

def is_final_recommendation(req: ChatRequest, ai_response: str) -> bool:
    """최종 추천 결과인지 판단 - 멀티턴 완료 감지 개선"""
    session = get_session(req.session_id)

    # 세션에서 최종 추천 플래그 확인
    is_final_from_session = session.get("is_final_recommendation", False)
    if is_final_from_session:
        print(f"[DEBUG] Final recommendation detected from session flag")
        # 플래그 초기화
        session.pop("is_final_recommendation", None)
        from app.utils.redis_client import save_session
        save_session(req.session_id, session)
        return True

    # 멀티턴 플로우 진행 중인지 확인
    phone_plan_step = session.get("phone_plan_flow_step", 0)
    subscription_step = session.get("subscription_flow_step", 0)

    print(f"[DEBUG] is_final_recommendation - phone_plan_step: {phone_plan_step}, subscription_step: {subscription_step}")
    print(f"[DEBUG] AI response preview: {ai_response[:100]}...")

    # 멀티턴이 진행 중이면서 질문이 있으면 최종 추천이 아님
    if phone_plan_step > 0 or subscription_step > 0:
        # 다음 질문이 있는지 확인 (4단계 질문이 끝났는지)
        question_keywords = [
            "데이터는 얼마나", "통화는 얼마나", "서비스가 있나요", "예산은 어느",
            "콘텐츠를 주로", "어떤 기기로", "언제 주로", "선호하는 장르",
            "사용하시나요", "생각하고 계신가요", "있나요", "어떤"
        ]

        # 질문 키워드가 있으면 아직 최종 추천이 아님
        if any(keyword in ai_response for keyword in question_keywords):
            print(f"[DEBUG] Still asking questions, not final recommendation")
            return False

    # 최종 추천 키워드가 있는지 확인
    final_keywords = [
        "추천드립니다", "추천해드릴게", "추천 요금제", "추천 메인 구독",
        "찰떡 요금제", "완전 추천", "위 요금제들을 추천드립니다",
        "이 요금제들 완전 추천", "위 조합을 추천드립니다", "이 조합 완전 추천"
    ]
    has_final_keywords = any(keyword in ai_response for keyword in final_keywords)

    print(f"[DEBUG] Has final keywords: {has_final_keywords}")
    return has_final_keywords

def get_recommended_plans(req: ChatRequest, message: str, ai_response: str = ""):
    """메시지와 AI 응답 분석해서 추천 요금제 가져오기 - 개선된 버전"""
    db = SessionLocal()
    try:
        full_text = message + " " + ai_response

        print(f"[DEBUG] get_recommended_plans - analyzing: {ai_response[:200]}...")

        # AI가 추천한 특정 요금제들 추출
        plan_matches = re.findall(r'너겟\s*(\d+)', ai_response)

        if plan_matches:
            plan_names = [f"너겟 {num}" for num in plan_matches]
            plans = db.query(Plan).filter(Plan.name.in_(plan_names)).all()
            if plans:
                print(f"[DEBUG] Found specific plans from AI response: {[p.name for p in plans]}")
                return plans

        # 사용자 정보 기반 스마트 추천 (세션에서 수집된 정보 활용)
        session = get_session(req.session_id)
        user_info = session.get("user_info", {})

        # 예산 기반 추천
        budget_text = user_info.get("budget", "") + " " + full_text
        budget_match = re.search(r'(\d{1,2})만원|(\d{4,5})원', budget_text)
        if budget_match:
            budget = int(budget_match.group(1)) * 10000 if budget_match.group(1) else int(budget_match.group(2))
            plans = db.query(Plan).filter(Plan.price <= budget).order_by(Plan.price.desc()).limit(2).all()
            if plans:
                print(f"[DEBUG] Found budget-based plans: {[p.name for p in plans]}")
                return plans

        # 데이터 사용량 기반 추천
        data_usage = user_info.get("data_usage", "").lower()
        if "많이" in data_usage or "무제한" in data_usage:
            plans = db.query(Plan).filter(Plan.data.contains("GB")).order_by(Plan.data.desc()).limit(2).all()
        elif "적게" in data_usage or "조금" in data_usage:
            plans = db.query(Plan).filter(Plan.price <= 30000).order_by(Plan.price).limit(2).all()
        else:
            # 중간 사용자용
            plans = db.query(Plan).filter(Plan.price.between(25000, 40000)).order_by(Plan.price).limit(2).all()

        if plans:
            print(f"[DEBUG] Found usage-based plans: {[p.name for p in plans]}")
            return plans

        # 기본 추천 (인기 요금제)
        default_plans = db.query(Plan).filter(Plan.name.in_(["너겟 30", "너겟 32", "너겟 34"])).all()
        print(f"[DEBUG] Using default popular plans: {[p.name for p in default_plans]}")
        return default_plans

    finally:
        db.close()

def should_recommend_plans(ai_response: str) -> bool:
    """AI 응답에 요금제 추천이 포함되어 있는지 판단 - 개선된 버전"""

    # 질문 중인지 확인
    question_keywords = [
        "데이터는 얼마나", "통화는 얼마나", "서비스가 있나요", "예산은 어느",
        "사용하시나요", "생각하고 계신가요", "있나요", "어떤"
    ]

    # 질문 중이면 추천하지 않음
    if any(keyword in ai_response for keyword in question_keywords):
        print(f"[DEBUG] Response contains question, not recommending plans")
        return False

    # 최종 추천 키워드가 있는 경우만 추천
    final_keywords = ['요금제', '추천', '너겟', '플랜']
    recommendation_keywords = [
        '추천드립니다', '추천해드릴게', '찰떡 요금제', '완전 추천',
        '위 요금제들을 추천드립니다', '이 요금제들 완전 추천'
    ]

    has_plan_keywords = any(keyword in ai_response for keyword in final_keywords)
    has_recommendation_keywords = any(keyword in ai_response for keyword in recommendation_keywords)

    result = has_plan_keywords and has_recommendation_keywords
    print(f"[DEBUG] should_recommend_plans: {result} (plan_keywords: {has_plan_keywords}, rec_keywords: {has_recommendation_keywords})")
    return result

# 수정된 chat.py의 구독 추천 함수들

def get_recommended_subscriptions(req: ChatRequest, ai_response: str):
    """AI 응답에서 구독 서비스 추천 정보 추출 - 완전 수정된 버전"""

    # 질문 중인지 확인
    question_keywords = [
        "콘텐츠를 주로", "어떤 기기로", "언제 주로", "선호하는 장르",
        "즐기시나요", "보시나요", "시청하시나요"
    ]

    # 질문 중이면 추천하지 않음
    if any(keyword in ai_response for keyword in question_keywords):
        print(f"[DEBUG] Response contains subscription question, not recommending")
        return None

    db = SessionLocal()
    try:
        # AI 응답에서 구독 서비스와 브랜드 추출
        subscription_matches = re.findall(r'(리디|지니|왓챠|넷플릭스|유튜브|스포티파이|U\+모바일tv)', ai_response)
        brand_matches = re.findall(r'(교보문고|스타벅스|올리브영|CGV|롯데시네마)', ai_response)

        recommended_subscriptions = []

        # 🔥 1. 메인 구독 찾기 (Subscription 테이블에서)
        main_subscription = None
        if subscription_matches:
            subscription_name = subscription_matches[0]
            main_subscription = db.query(Subscription).filter(
                Subscription.title.contains(subscription_name)
            ).first()

        # AI가 특정 구독을 언급하지 않았다면 사용자 정보 기반 추천
        if not main_subscription:
            session = get_session(req.session_id)
            user_info = session.get("user_info", {})
            content_type = user_info.get("content_type", "").lower()

            if "영화" in content_type or "드라마" in content_type:
                main_subscription = db.query(Subscription).filter(
                    Subscription.title.contains("넷플릭스")
                ).first()
            elif "음악" in content_type:
                main_subscription = db.query(Subscription).filter(
                    Subscription.title.contains("지니")
                ).first()
            elif "스포츠" in content_type:
                main_subscription = db.query(Subscription).filter(
                    Subscription.title.contains("U+모바일tv")
                ).first()
            else:
                # 기본 추천 → 넷플릭스
                main_subscription = db.query(Subscription).first()

        # 메인 구독을 배열에 추가 (type: "main_subscription")
        if main_subscription:
            recommended_subscriptions.append({
                "id": main_subscription.id,
                "title": main_subscription.title,  # Subscription은 title 필드
                "image_url": main_subscription.image_url,
                "category": main_subscription.category,
                "price": main_subscription.price,
                "type": "main_subscription"  # 🔥 정확한 타입
            })

        # 🔥 2. 라이프 브랜드 찾기 (Brand 테이블에서)
        life_brand = None
        if brand_matches:
            brand_name = brand_matches[0]
            life_brand = db.query(Brand).filter(
                Brand.name.contains(brand_name)
            ).first()

        # AI가 특정 브랜드를 언급하지 않았다면 기본 추천
        if not main_subscription:
            main_subscription = db.query(Subscription).filter(
                Subscription.title.contains("넷플릭스")
            ).first() or db.query(Subscription).first()

        if not life_brand:
            life_brand = db.query(Brand).filter(
                Brand.name.contains("스타벅스")
            ).first() or db.query(Brand).first()

        # 라이프 브랜드를 배열에 추가 (type: "life_brand")
        if life_brand:
            recommended_subscriptions.append({
                "id": life_brand.id,
                "name": life_brand.name,  # Brand는 name 필드
                "image_url": life_brand.image_url,
                "description": life_brand.description,
                "type": "life_brand"  # 🔥 정확한 타입
            })

        print(f"[DEBUG] Subscription combination: main={main_subscription.title if main_subscription else None}, brand={life_brand.name if life_brand else None}")

        return recommended_subscriptions if recommended_subscriptions else None

    finally:
        db.close()

def should_recommend_subscriptions(ai_response: str) -> bool:
    """AI 응답에 구독 서비스 추천이 포함되어 있는지 판단 - 강화된 버전"""

    # 🔥 요금제 키워드가 있으면 구독 추천하지 않음 (명확한 분리)
    plan_keywords = ["요금제", "너겟", "데이터", "통화", "GB", "플랜"]
    if any(keyword in ai_response for keyword in plan_keywords):
        print(f"[DEBUG] Response contains plan keywords, not recommending subscriptions")
        return False

    # 질문 중인지 확인
    question_keywords = [
        "콘텐츠를 주로", "어떤 기기로", "언제 주로", "선호하는 장르"
    ]

    # 질문 중이면 추천하지 않음
    if any(keyword in ai_response for keyword in question_keywords):
        print(f"[DEBUG] Response contains subscription questions, not recommending")
        return False

    # 최종 추천 키워드가 있는 경우만 추천
    keywords = ['구독', '추천', '메인 구독', '라이프 브랜드', '조합']
    recommendation_keywords = [
        '추천드립니다', '추천해드릴게', '찰떡', '완전 추천',
        '위 조합을 추천드립니다', '이 조합 완전 추천'
    ]

    has_sub_keywords = any(keyword in ai_response for keyword in keywords)
    has_recommendation_keywords = any(keyword in ai_response for keyword in recommendation_keywords)

    result = has_sub_keywords and has_recommendation_keywords
    print(f"[DEBUG] should_recommend_subscriptions: {result}")
    return result

def should_recommend_plans(ai_response: str) -> bool:
    """AI 응답에 요금제 추천이 포함되어 있는지 판단 - 강화된 버전"""

    # 🔥 구독 키워드가 있으면 요금제 추천하지 않음 (명확한 분리)
    subscription_keywords = ["구독", "메인 구독", "라이프 브랜드", "조합", "넷플릭스", "스타벅스"]
    if any(keyword in ai_response for keyword in subscription_keywords):
        print(f"[DEBUG] Response contains subscription keywords, not recommending plans")
        return False

    # 질문 중인지 확인
    question_keywords = [
        "데이터는 얼마나", "통화는 얼마나", "서비스가 있나요", "예산은 어느",
        "사용하시나요", "생각하고 계신가요", "있나요", "어떤"
    ]

    # 질문 중이면 추천하지 않음
    if any(keyword in ai_response for keyword in question_keywords):
        print(f"[DEBUG] Response contains plan questions, not recommending plans")
        return False

    # 최종 추천 키워드가 있는 경우만 추천
    final_keywords = ['요금제', '추천', '너겟', '플랜']
    recommendation_keywords = [
        '추천드립니다', '추천해드릴게', '찰떡 요금제', '완전 추천',
        '위 요금제들을 추천드립니다', '이 요금제들 완전 추천'
    ]

    has_plan_keywords = any(keyword in ai_response for keyword in final_keywords)
    has_recommendation_keywords = any(keyword in ai_response for keyword in recommendation_keywords)

    result = has_plan_keywords and has_recommendation_keywords
    print(f"[DEBUG] should_recommend_plans: {result}")
    return result


@router.post("/chat")
async def chat(req: ChatRequest):
    async def generate_stream():
        # 1. handle_chat에서 함수를 받아서 실행
        ai_stream_fn = await handle_chat(req)

        # 2. AI 응답을 모두 수집해서 분석
        full_ai_response = ""
        ai_chunks = []

        async for chunk in ai_stream_fn():
            full_ai_response += chunk
            ai_chunks.append(chunk)

        print(f"[DEBUG] Full AI response collected: '{full_ai_response}'")

        # 3. 최종 추천 결과인지 확인
        is_final = is_final_recommendation(req, full_ai_response)
        print(f"[DEBUG] Is final recommendation: {is_final}")

        if is_final:
            # 🔥 4. 요금제와 구독 서비스 추천을 명확히 분리

            # 요금제 추천 확인 및 전송
            if should_recommend_plans(full_ai_response):
                print(f"[DEBUG] Planning to send PLAN recommendations")
                recommended_plans = get_recommended_plans(req, req.message, full_ai_response)

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

            # 구독 서비스 추천 확인 및 전송 (요금제와 완전 분리)
            elif should_recommend_subscriptions(full_ai_response):
                print(f"[DEBUG] Planning to send SUBSCRIPTION recommendations")
                recommended_subscriptions = get_recommended_subscriptions(req, full_ai_response)

                if recommended_subscriptions:
                    subscription_data = {
                        "type": "subscription_recommendations",
                        "subscriptions": recommended_subscriptions
                    }
                    print(f"[DEBUG] Sending subscription recommendations: {len(recommended_subscriptions)} items")
                    yield f"data: {json.dumps(subscription_data, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.1)

        # 5. 스트리밍 시작 신호
        yield f"data: {json.dumps({'type': 'message_start'}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.05)

        # 6. 전체 응답을 단어 단위로 자연스럽게 스트리밍
        words = full_ai_response.split()
        for i, word in enumerate(words):
            chunk_data = {
                "type": "message_chunk",
                "content": word + (" " if i < len(words) - 1 else "")
            }
            yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.05)

        # 7. 스트리밍 완료 신호
        yield f"data: {json.dumps({'type': 'message_end'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate_stream(), media_type="text/event-stream")


def should_recommend_subscriptions(ai_response: str) -> bool:
    """AI 응답에 구독 서비스 추천이 포함되어 있는지 판단 - 개선된 버전"""

    # 질문 중인지 확인
    question_keywords = [
        "콘텐츠를 주로", "어떤 기기로", "언제 주로", "선호하는 장르"
    ]

    # 질문 중이면 추천하지 않음
    if any(keyword in ai_response for keyword in question_keywords):
        return False

    # 최종 추천 키워드가 있는 경우만 추천
    keywords = ['구독', '추천', '메인 구독', '라이프 브랜드']
    recommendation_keywords = [
        '추천드립니다', '추천해드릴게', '찰떡', '완전 추천',
        '위 조합을 추천드립니다', '이 조합 완전 추천'
    ]

    has_sub_keywords = any(keyword in ai_response for keyword in keywords)
    has_recommendation_keywords = any(keyword in ai_response for keyword in recommendation_keywords)

    return has_sub_keywords and has_recommendation_keywords

@router.post("/chat")
async def chat(req: ChatRequest):
    async def generate_stream():
        # 1. handle_chat에서 함수를 받아서 실행
        ai_stream_fn = await handle_chat(req)

        # 2. AI 응답을 모두 수집해서 분석
        full_ai_response = ""
        ai_chunks = []

        # 함수를 실행해서 generator 얻기
        async for chunk in ai_stream_fn():
            full_ai_response += chunk
            ai_chunks.append(chunk)

        print(f"[DEBUG] Full AI response collected: '{full_ai_response}'")

        # 3. 최종 추천 결과인지 확인 - 🔥 개선된 감지!
        is_final = is_final_recommendation(req, full_ai_response)
        print(f"[DEBUG] Is final recommendation: {is_final}")

        if is_final:
            # 4. 요금제 추천이 필요한 경우에만 DB에서 조회해서 전송
            if should_recommend_plans(full_ai_response):
                recommended_plans = get_recommended_plans(req, req.message, full_ai_response)

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

            # 5. 구독 서비스 추천이 필요한 경우에만 DB에서 조회해서 전송 - 🔥 수정된 부분!
            if should_recommend_subscriptions(full_ai_response):
                recommended_subscriptions = get_recommended_subscriptions(req, full_ai_response)

                if recommended_subscriptions:
                    subscription_data = {
                        "type": "subscription_recommendations",
                        "subscriptions": recommended_subscriptions  # 배열 형태로 변경
                    }
                    print(f"[DEBUG] Sending subscription recommendations: {len(recommended_subscriptions)} items")
                    yield f"data: {json.dumps(subscription_data, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.1)

        # 6. 스트리밍 시작 신호
        yield f"data: {json.dumps({'type': 'message_start'}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.05)

        # 7. 전체 응답을 단어 단위로 자연스럽게 스트리밍
        print(f"[DEBUG] Starting message streaming")

        words = full_ai_response.split()  # 단어로 나누기
        for i, word in enumerate(words):
            chunk_data = {
                "type": "message_chunk",
                "content": word + (" " if i < len(words) - 1 else "")  # 마지막이 아니면 공백 추가
            }
            yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.05)

        # 8. 스트리밍 완료 신호
        yield f"data: {json.dumps({'type': 'message_end'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate_stream(), media_type="text/event-stream")