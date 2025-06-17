from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.schemas.chat import LikesChatRequest
from app.services.handle_chat_likes import handle_chat_likes
from app.db.database import SessionLocal
from app.db.models import Subscription, Brand
import json
import asyncio
import re

router = APIRouter()

def get_recommended_subscriptions_likes(ai_response: str):
    """좋아요 기반 AI 응답에서 구독 서비스 추천 정보 추출"""
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

@router.post("/chat/likes")
async def chat_likes(req: LikesChatRequest):
    async def generate_stream():
        # 1. handle_chat_likes에서 함수를 받아서 실행
        ai_stream_fn = await handle_chat_likes(req)

        # 2. AI 응답을 모두 수집해서 분석
        full_ai_response = ""
        ai_chunks = []

        async for chunk in ai_stream_fn():
            full_ai_response += chunk
            ai_chunks.append(chunk)

        # 3. 구독 서비스 추천이 있으면 DB에서 조회해서 먼저 전송
        recommended_subscriptions = get_recommended_subscriptions_likes(full_ai_response)

        if recommended_subscriptions:
            subscription_data = {
                "type": "subscription_recommendations",
                "data": recommended_subscriptions
            }
            yield f"data: {json.dumps(subscription_data, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.1)

        # 4. 스트리밍 시작 신호
        yield f"data: {json.dumps({'type': 'message_start'}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.05)

        # 5. 수집된 AI 응답을 자연스럽게 다시 스트리밍
        for chunk in ai_chunks:
            if chunk.strip():
                chunk_data = {
                    "type": "message_chunk",
                    "content": chunk
                }
                yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.05)

        # 6. 스트리밍 완료 신호
        yield f"data: {json.dumps({'type': 'message_end'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate_stream(), media_type="text/event-stream")