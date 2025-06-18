# app/api/chat.py - 완전히 새로운 싱글턴 버전
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
    """AI 응답이 요금제 추천인지 판단 - 🔥 강화된 버전"""

    # 구독 서비스 키워드가 있으면 요금제가 아님
    subscription_keywords = ["구독", "메인 구독", "라이프 브랜드", "조합", "넷플릭스", "유튜브", "스타벅스", "OTT"]
    if any(keyword in ai_response for keyword in subscription_keywords):
        print(f"[DEBUG] Contains subscription keywords, not a plan recommendation")
        return False

    # 요금제 관련 키워드 확인
    plan_keywords = ["요금제", "너겟", "라이트", "프리미엄", "플랜", "통신비", "데이터", "통화"]
    recommendation_keywords = ["추천드립니다", "추천해드릴게", "찰떡 요금제", "완전 추천", "지리고", "럭키비키"]

    has_plan_keywords = any(keyword in ai_response for keyword in plan_keywords)
    has_recommendation_keywords = any(keyword in ai_response for keyword in recommendation_keywords)

    result = has_plan_keywords and has_recommendation_keywords
    print(f"[DEBUG] is_plan_recommendation: {result} (plan: {has_plan_keywords}, rec: {has_recommendation_keywords})")
    return result

def is_subscription_recommendation(ai_response: str) -> bool:
    """AI 응답이 구독 서비스 추천인지 판단 - 🔥 강화된 버전"""

    # 요금제 키워드가 있으면 구독 서비스가 아님
    plan_keywords = ["요금제", "너겟", "라이트", "프리미엄", "플랜", "통신비", "GB", "데이터", "통화"]
    if any(keyword in ai_response for keyword in plan_keywords):
        print(f"[DEBUG] Contains plan keywords, not a subscription recommendation")
        return False

    # 구독 서비스 관련 키워드 확인
    subscription_keywords = ["구독", "메인 구독", "라이프 브랜드", "조합", "넷플릭스", "유튜브", "스타벅스", "OTT"]
    recommendation_keywords = ["추천드립니다", "추천해드릴게", "찰떡", "완전 추천", "조합", "위 조합을 추천", "이 조합 완전"]

    has_sub_keywords = any(keyword in ai_response for keyword in subscription_keywords)
    has_recommendation_keywords = any(keyword in ai_response for keyword in recommendation_keywords)

    result = has_sub_keywords and has_recommendation_keywords
    print(f"[DEBUG] is_subscription_recommendation: {result} (sub: {has_sub_keywords}, rec: {has_recommendation_keywords})")
    return result

def get_recommended_plans(req: ChatRequest, ai_response: str = ""):
    """AI 응답 분석해서 추천 요금제 가져오기 - 🔥 개선된 버전"""
    db = SessionLocal()
    try:
        print(f"[DEBUG] get_recommended_plans - analyzing: {ai_response[:200]}...")

        # 1. AI가 추천한 특정 요금제들 추출
        plan_matches = re.findall(r'너겟\s*(\d+)', ai_response)
        if plan_matches:
            plan_names = [f"너겟 {num}" for num in plan_matches]
            plans = db.query(Plan).filter(Plan.name.in_(plan_names)).all()
            if plans:
                print(f"[DEBUG] Found specific plans from AI response: {[p.name for p in plans]}")
                return plans

        # 2. 라이트 요금제 추출
        lite_matches = re.findall(r'라이트\s*(\d+)', ai_response)
        if lite_matches:
            plan_names = [f"라이트 {num}" for num in lite_matches]
            plans = db.query(Plan).filter(Plan.name.in_(plan_names)).all()
            if plans:
                print(f"[DEBUG] Found lite plans from AI response: {[p.name for p in plans]}")
                return plans

        # 3. 세션 기반 스마트 추천 (사용자 정보 활용)
        session = get_session(req.session_id)

        # 메시지에서 힌트 추출
        message_lower = req.message.lower()

        # 게임용, 업무용 등 용도 기반
        if any(word in message_lower for word in ["게임", "업무", "화상회의", "스트리밍"]):
            plans = db.query(Plan).filter(Plan.name.in_(["너겟 34", "너겟 36"])).all()
        # 예산 기반
        elif any(word in message_lower for word in ["저렴", "싸", "가성비", "3만원"]):
            plans = db.query(Plan).filter(Plan.name.in_(["라이트 23", "너겟 30"])).all()
        # 무제한, 많이 사용
        elif any(word in message_lower for word in ["무제한", "많이", "넉넉", "여유"]):
            plans = db.query(Plan).filter(Plan.name.in_(["너겟 34", "너겟 36"])).all()
        else:
            # 기본 추천 (인기 요금제)
            plans = db.query(Plan).filter(Plan.name.in_(["너겟 30", "너겟 32", "너겟 34"])).all()

        if plans:
            print(f"[DEBUG] Found context-based plans: {[p.name for p in plans]}")
            return plans[:2]  # 최대 2개만

        # 4. 폴백 - 인기 요금제
        default_plans = db.query(Plan).filter(Plan.name.in_(["너겟 30", "너겟 32"])).all()
        print(f"[DEBUG] Using default popular plans: {[p.name for p in default_plans]}")
        return default_plans

    finally:
        db.close()

def get_recommended_subscriptions(req: ChatRequest, ai_response: str):
    """AI 응답에서 구독 서비스 추천 정보 추출 - 🔥 완전 수정된 버전"""

    db = SessionLocal()
    try:
        print(f"[DEBUG] get_recommended_subscriptions - analyzing: {ai_response[:200]}...")

        # AI 응답에서 구독 서비스와 브랜드 추출
        subscription_matches = re.findall(r'(리디|지니|왓챠|넷플릭스|유튜브|스포티파이|U\+모바일tv)', ai_response)
        brand_matches = re.findall(r'(교보문고|스타벅스|올리브영|CGV|롯데시네마)', ai_response)

        recommended_subscriptions = []

        # 1. 메인 구독 찾기 (Subscription 테이블에서)
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

        # 메인 구독을 배열에 추가
        if main_subscription:
            recommended_subscriptions.append({
                "id": main_subscription.id,
                "title": main_subscription.title,
                "image_url": main_subscription.image_url,
                "category": main_subscription.category,
                "price": main_subscription.price,
                "type": "main_subscription"
            })

        # 2. 라이프 브랜드 찾기 (Brand 테이블에서)
        life_brand = None
        if brand_matches:
            brand_name = brand_matches[0]
            life_brand = db.query(Brand).filter(
                Brand.name.contains(brand_name)
            ).first()

        # AI가 특정 브랜드를 언급하지 않았다면 기본 추천
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

        # 라이프 브랜드를 배열에 추가
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

        # 7. 전체 응답을 단어 단위로 자연스럽게 스트리밍
        words = full_ai_response.split()
        for i, word in enumerate(words):
            chunk_data = {
                "type": "message_chunk",
                "content": word + (" " if i < len(words) - 1 else "")
            }
            yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.05)

        # 8. 스트리밍 완료 신호
        yield f"data: {json.dumps({'type': 'message_end'}, ensure_ascii=False)}\n\n"

        # 9. 세션 정리 (추천 타입 리셋)
        session.pop("last_recommendation_type", None)
        from app.utils.redis_client import save_session
        save_session(req.session_id, session)

    return StreamingResponse(generate_stream(), media_type="text/event-stream")