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
    """좋아요 기반 AI 응답에서 구독 서비스 추천 정보 추출 - 타입 정확히 구분"""

    # 최종 추천이 아닌 경우 확인
    if not any(keyword in ai_response for keyword in ['추천', '조합', '메인 구독', '라이프 브랜드']):
        print(f"[DEBUG] Likes response doesn't contain recommendation keywords")
        return None

    db = SessionLocal()
    try:
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

        # AI가 특정 구독을 언급하지 않았다면 기본 추천
        if not main_subscription:
            # 기본 메인 구독 추천 (넷플릭스)
            main_subscription = db.query(Subscription).filter(
                Subscription.title.contains("넷플릭스")
            ).first()

            # 넷플릭스가 없으면 첫 번째 구독 서비스
            if not main_subscription:
                main_subscription = db.query(Subscription).first()

        # 메인 구독 추가 (type: "main_subscription")
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
        if not life_brand:
            # 기본 라이프 브랜드 추천 (스타벅스)
            life_brand = db.query(Brand).filter(
                Brand.name.contains("스타벅스")
            ).first()

            # 스타벅스가 없으면 첫 번째 브랜드
            if not life_brand:
                life_brand = db.query(Brand).first()

        # 라이프 브랜드 추가 (type: "life_brand")
        if life_brand:
            recommended_subscriptions.append({
                "id": life_brand.id,
                "name": life_brand.name,  # Brand는 name 필드
                "image_url": life_brand.image_url,
                "description": life_brand.description,
                "type": "life_brand"  # 🔥 정확한 타입
            })

        print(f"[DEBUG] Likes combination: main={main_subscription.title if main_subscription else None}, brand={life_brand.name if life_brand else None}")

        return recommended_subscriptions if recommended_subscriptions else None

    finally:
        db.close()

@router.post("/chat/likes", summary="좋아요 기반 추천", description="사용자가 좋아요 표시한 브랜드를 기반으로 구독 서비스 조합을 추천합니다.")
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

        print(f"[DEBUG] Likes full AI response: '{full_ai_response[:200]}...'")

        # 3. 구독 서비스 추천이 있으면 DB에서 조회해서 먼저 전송
        recommended_subscriptions = get_recommended_subscriptions_likes(full_ai_response)

        if recommended_subscriptions:
            subscription_data = {
                "type": "subscription_recommendations",
                "subscriptions": recommended_subscriptions
            }
            print(f"[DEBUG] Sending likes-based subscription recommendations: {len(recommended_subscriptions)} items")
            # 각 항목의 타입 확인
            for item in recommended_subscriptions:
                print(f"[DEBUG] Item: {item.get('title') or item.get('name')} - Type: {item['type']}")

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