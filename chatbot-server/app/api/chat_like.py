# chatbot-server/app/api/chat_like.py - 수정된 버전

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

    # 좋아요 안내 메시지인 경우 카드 표시 안함
    guidance_keywords = [
        '핫플레이스', '스토어맵', '좋아요를', '좋아요 기반', '좋아요한 브랜드가 없',
        '좋아요한 브랜드가 없어서', '맞춤 추천을 드릴 수 없', '일반 채팅으로',
        '구독 서비스 추천해주세요', '기본 추천을', '먼저 가입해보고',
        '브랜드를 못 찾겠', '데이터가 없어', '다시 시도해', '문의해주세요'
    ]

    if any(keyword in ai_response for keyword in guidance_keywords):
        print(f"[DEBUG] Likes response is guidance message, no cards needed")
        return None

    # 최종 추천이 아닌 경우 확인
    if not any(keyword in ai_response for keyword in ['추천', '조합', '메인 구독', '라이프 브랜드']):
        print(f"[DEBUG] Likes response doesn't contain recommendation keywords")
        return None

    db = SessionLocal()
    try:
        subscription_matches = re.findall(r'(리디|지니|왓챠|넷플릭스|유튜브|스포티파이|U\+모바일tv)', ai_response)
        brand_matches = re.findall(r'(교보문고|스타벅스|올리브영|CGV|롯데시네마)', ai_response)

        recommended_subscriptions = []

        # 1. 메인 구독 찾기 (AI가 명시적으로 언급한 경우만)
        main_subscription = None
        if subscription_matches:
            subscription_name = subscription_matches[0]
            main_subscription = db.query(Subscription).filter(
                Subscription.title.contains(subscription_name)
            ).first()

        # 메인 구독 추가 (AI가 명시적으로 언급한 경우만)
        if main_subscription:
            recommended_subscriptions.append({
                "id": main_subscription.id,
                "title": main_subscription.title,
                "image_url": main_subscription.image_url,
                "category": main_subscription.category,
                "price": main_subscription.price,
                "type": "main_subscription"
            })

        # 2. 라이프 브랜드 찾기 (AI가 명시적으로 언급한 경우만)
        life_brand = None
        if brand_matches:
            brand_name = brand_matches[0]
            life_brand = db.query(Brand).filter(
                Brand.name.contains(brand_name)
            ).first()

        # 라이프 브랜드 추가 (AI가 명시적으로 언급한 경우만)
        if life_brand:
            recommended_subscriptions.append({
                "id": life_brand.id,
                "name": life_brand.name,
                "image_url": life_brand.image_url,
                "description": life_brand.description,
                "type": "life_brand"
            })

        print(f"[DEBUG] Likes combination: main={main_subscription.title if main_subscription else None}, brand={life_brand.name if life_brand else None}")

        # 실제 추천이 있을 때만 카드 반환
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

        # 실제 추천이 있을 때만 구독 서비스 카드 전송 (안내 메시지는 카드 없음)
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
        else:
            print(f"[DEBUG] No subscription cards needed (guidance message or no explicit recommendations)")

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