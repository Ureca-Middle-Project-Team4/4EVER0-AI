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

def get_intent_from_session(req: ChatRequest) -> str:
    """세션에서 현재 인텐트 파악"""
    session = get_session(req.session_id)

    # 멀티턴 플로우 확인
    phone_plan_step = session.get("phone_plan_flow_step", 0)
    subscription_step = session.get("subscription_flow_step", 0)

    if phone_plan_step > 0:
        return "phone_plan"
    elif subscription_step > 0:
        return "subscription"

    # 세션에 저장된 인텐트 확인 (handle_chat에서 설정)
    return session.get("current_intent", "unknown")

def is_final_recommendation(req: ChatRequest, ai_response: str) -> bool:
    """최종 추천 결과인지 판단"""
    session = get_session(req.session_id)

    # 멀티턴 플로우 진행 중인지 확인
    phone_plan_step = session.get("phone_plan_flow_step", 0)
    subscription_step = session.get("subscription_flow_step", 0)

    # 멀티턴이 아직 진행 중이면 최종 추천이 아님
    if phone_plan_step > 0 or subscription_step > 0:
        # 다음 질문이 있는지 확인 (4단계 질문이 끝났는지)
        if "데이터는 얼마나" in ai_response or "통화는 얼마나" in ai_response or "서비스가 있나요" in ai_response or "예산은 어느" in ai_response:
            return False  # 아직 질문 중
        if "콘텐츠를 주로" in ai_response or "어떤 기기로" in ai_response or "언제 주로" in ai_response or "선호하는 장르" in ai_response:
            return False  # 아직 질문 중

    # 최종 추천 키워드가 있는지 확인
    final_keywords = ["추천드립니다", "추천해드릴게", "추천 요금제", "추천 메인 구독", "찰떡 요금제", "완전 추천"]
    return any(keyword in ai_response for keyword in final_keywords)

def get_recommended_plans(message: str, ai_response: str = ""):
    """메시지와 AI 응답 분석해서 추천 요금제 가져오기"""
    db = SessionLocal()
    try:
        full_text = message + " " + ai_response

        # AI가 추천한 특정 요금제들 추출
        plan_matches = re.findall(r'너겟\s*(\d+)', ai_response)

        if plan_matches:
            plan_names = [f"너겟 {num}" for num in plan_matches]
            plans = db.query(Plan).filter(Plan.name.in_(plan_names)).all()
            if plans:
                return plans

        # 예산 기반 추천
        budget_match = re.search(r'(\d{1,2})만원|(\d{4,5})원', full_text)
        if budget_match:
            budget = int(budget_match.group(1)) * 10000 if budget_match.group(1) else int(budget_match.group(2))
            plans = db.query(Plan).filter(Plan.price <= budget).order_by(Plan.price).limit(3).all()
            if plans:
                return plans

        # 기본 추천
        return db.query(Plan).order_by(Plan.price).limit(3).all()

    finally:
        db.close()

def should_recommend_plans(ai_response: str) -> bool:
    """AI 응답에 요금제 추천이 포함되어 있는지 판단"""
    keywords = ['요금제', '추천', '너겟', '26000원', '30000원', '플랜', '상품']
    return any(keyword in ai_response for keyword in keywords)

def get_recommended_subscriptions(ai_response: str):
    """AI 응답에서 구독 서비스 추천 정보 추출"""
    db = SessionLocal()
    try:
        subscription_matches = re.findall(r'(리디|지니|왓챠|넷플릭스|유튜브|스포티파이|U\+모바일tv)', ai_response)
        brand_matches = re.findall(r'(교보문고|스타벅스|올리브영|CGV|롯데시네마)', ai_response)

        recommended_data = {}

        if subscription_matches:
            subscription_name = subscription_matches[0]
            subscription = db.query(Subscription).filter(
                Subscription.title.contains(subscription_name)
            ).first()
            if subscription:
                recommended_data['main_subscription'] = {
                    "id": subscription.id,
                    "title": subscription.title,
                    "price": subscription.price,
                    "category": subscription.category,
                    "image_url": subscription.image_url
                }

        if brand_matches:
            brand_name = brand_matches[0]
            brand = db.query(Brand).filter(
                Brand.name.contains(brand_name)
            ).first()
            if brand:
                recommended_data['life_brand'] = {
                    "id": brand.id,
                    "name": brand.name,
                    "image_url": brand.image_url,
                    "description": brand.description
                }

        return recommended_data if recommended_data else None

    finally:
        db.close()

def should_recommend_subscriptions(ai_response: str) -> bool:
    """AI 응답에 구독 서비스 추천이 포함되어 있는지 판단"""
    keywords = ['구독', '추천', '메인 구독', '라이프 브랜드', '리디', '지니', '교보문고', '스타벅스', 'U+모바일tv']
    return any(keyword in ai_response for keyword in keywords)

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

        # 3. 최종 추천 결과인지 확인
        if is_final_recommendation(req, full_ai_response):

            # ⭐ 핵심: 인텐트별로 분기 처리
            current_intent = get_intent_from_session(req)
            print(f"[DEBUG] Current intent: {current_intent}")

            # 🔥 요금제 추천 상담인 경우 → 요금제 데이터만 전송
            if current_intent in ["phone_plan", "phone_plan_multi", "telecom_plan", "telecom_plan_direct"]:
                if should_recommend_plans(full_ai_response):
                    recommended_plans = get_recommended_plans(req.message, full_ai_response)

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
                        yield f"data: {json.dumps(plan_data, ensure_ascii=False)}\n\n"
                        await asyncio.sleep(0.1)

            # 🎬 구독 서비스 추천인 경우 → 구독 데이터만 전송
            elif current_intent in ["subscription", "subscription_recommend", "subscription_multi"]:
                if should_recommend_subscriptions(full_ai_response):
                    recommended_subscriptions = get_recommended_subscriptions(full_ai_response)

                    if recommended_subscriptions:
                        subscription_data = {
                            "type": "subscription_recommendations",
                            "data": recommended_subscriptions
                        }
                        yield f"data: {json.dumps(subscription_data, ensure_ascii=False)}\n\n"
                        await asyncio.sleep(0.1)

            # 💡 기타 경우 (안전장치)
            else:
                print(f"[WARNING] Unknown intent: {current_intent}")
                # 키워드 기반으로 추천 결정
                if should_recommend_plans(full_ai_response):
                    recommended_plans = get_recommended_plans(req.message, full_ai_response)
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
                        yield f"data: {json.dumps(plan_data, ensure_ascii=False)}\n\n"
                        await asyncio.sleep(0.1)

        # 6. 스트리밍 시작 신호
        yield f"data: {json.dumps({'type': 'message_start'}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.05)

        # 7. 전체 응답을 단어 단위로 자연스럽게 스트리밍
        print(f"[DEBUG] Full AI response: '{full_ai_response}'")

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

    return StreamingResponse(generate_stream(), media_type="text/event-stream")