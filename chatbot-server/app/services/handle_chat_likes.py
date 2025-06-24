# chatbot-server/app/services/handle_chat_likes.py - 수정된 버전

from app.schemas.chat import LikesChatRequest
from app.db.coupon_like_db import get_liked_brand_ids
from app.db.subscription_db import get_products_from_db
from app.db.brand_db import get_life_brands_from_db
from app.prompts.like_prompt import get_like_prompt
from app.utils.langchain_client import get_chat_model

async def handle_chat_likes(req: LikesChatRequest):
    # tone 파라미터 추출 및 디버깅
    tone = getattr(req, 'tone', 'general')
    print(f"[DEBUG] handle_chat_likes - tone: {tone}")

    # 1. 좋아요 기반 브랜드 ID 가져오기
    liked_brand_ids = get_liked_brand_ids(req.session_id)
    print(f"[DEBUG] Liked brand IDs: {liked_brand_ids}")

    # 2. 좋아요한 브랜드가 없을 때 안내 메시지 (기본 추천 제거)
    if not liked_brand_ids:
        print(f"[DEBUG] No liked brands found, showing guidance message")

        async def guidance_streamer():
            if tone == "muneoz":
                guidance_msg = """앗! 좋아요한 브랜드가 없네! 😅

우선 이런 걸 해봐:
📍 **핫플레이스 탭**에서 스토어맵 구경하고
💜 좋아하는 브랜드에 좋아요를 눌러봐!

그러면 완전 찰떡인 구독 추천을 해줄 수 있어~ 🐙✨

아니면 일반 상담으로 "구독 추천해줘"라고 말해도 돼! 💜"""
            else:
                guidance_msg = """좋아요한 브랜드가 없어서 맞춤 추천을 드릴 수 없어요. 😔

다음과 같이 해보시면 좋을 것 같아요:

📍 **핫플레이스 탭 > 스토어맵**에서
   관심있는 브랜드에 좋아요를 눌러주세요!

💬 또는 일반 채팅으로 **"구독 서비스 추천해주세요"**라고
   말씀해주시면 기본 추천을 받으실 수 있어요!

좋아요를 하신 후 다시 이용해주시면
취향에 맞는 개인화된 추천을 받으실 수 있습니다. 😊"""

            # 단어별로 스트리밍
            words = guidance_msg.split(' ')
            for i, word in enumerate(words):
                yield word + (" " if i < len(words) - 1 else "")

        return guidance_streamer

    # 3. 메인 구독, 라이프 브랜드 전체 조회
    subscriptions = get_products_from_db()
    brands = get_life_brands_from_db()

    # 4. 좋아요한 브랜드로 필터링 (기본 브랜드 사용 안함)
    filtered_brands = [b for b in brands if b.id in liked_brand_ids]

    # 🔥 5. 좋아요한 브랜드가 DB에서 찾을 수 없는 경우 안내
    if not filtered_brands:
        print(f"[DEBUG] Liked brands not found in database")

        async def brand_not_found_streamer():
            if tone == "muneoz":
                error_msg = """어? 좋아요한 브랜드를 못 찾겠어! 😵‍💫

혹시 좋아요가 제대로 안 됐나?
**핫플레이스 탭 > 스토어맵**에서
다시 한 번 💜 좋아요를 눌러봐!

아니면 일반 채팅으로 "구독 추천해줘"라고 하면
기본 추천을 받을 수 있어~ 🐙💜"""
            else:
                error_msg = """좋아요하신 브랜드 정보를 찾을 수 없어요. 😔

다음과 같이 해보세요:

📍 **핫플레이스 탭 > 스토어맵**에서
   브랜드 좋아요를 다시 확인해주세요

💬 또는 일반 채팅으로 **"구독 서비스 추천해주세요"**라고
   말씀해주시면 기본 추천을 받으실 수 있어요!

문제가 지속되면 고객센터로 문의해주세요."""

            words = error_msg.split(' ')
            for i, word in enumerate(words):
                yield word + (" " if i < len(words) - 1 else "")

        return brand_not_found_streamer

    # 6. 구독 서비스가 없는 경우 안내
    if not subscriptions:
        print(f"[DEBUG] No subscription data available")

        async def no_subscription_streamer():
            if tone == "muneoz":
                error_msg = """앗! 구독 서비스 데이터가 없어! 😅

일반 채팅으로 "구독 추천해줘"라고 해봐~
아니면 관리자에게 문의해줘! 🐙💜"""
            else:
                error_msg = """구독 서비스 데이터를 불러올 수 없어요. 😔

일반 채팅으로 **"구독 서비스 추천해주세요"**라고
말씀해주시거나, 잠시 후 다시 시도해주세요!"""

            words = error_msg.split(' ')
            for i, word in enumerate(words):
                yield word + (" " if i < len(words) - 1 else "")

        return no_subscription_streamer

    # 7. 포맷팅 - 명시적 줄바꿈 적용
    main = "\n\n".join([
        f"- {s.title} / {s.price}원 / {s.category}" for s in subscriptions
    ])

    life = "\n\n".join([
        f"- {b.name} / {b.description}" for b in filtered_brands
    ])

    # 8. 프롬프트 구성 (tone 파라미터 전달)
    try:
        prompt = get_like_prompt(tone).format(
            main=main,
            life=life
        )
        print(f"[DEBUG] Prompt generated successfully, length: {len(prompt)}")
    except Exception as e:
        print(f"[ERROR] Prompt generation failed: {e}")

        async def prompt_error_streamer():
            if tone == "muneoz":
                error_msg = """앗! 프롬프트 만드는 중에 문제가 생겼어! 😵‍💫

일반 채팅으로 "구독 추천해줘"라고 다시 시도해봐~ 🤟"""
            else:
                error_msg = """추천 준비 중 오류가 발생했어요. 😔

일반 채팅으로 **"구독 서비스 추천해주세요"**라고
다시 시도해주세요!"""

            words = error_msg.split(' ')
            for i, word in enumerate(words):
                yield word + (" " if i < len(words) - 1 else "")

        return prompt_error_streamer

    # 9. GPT 스트리밍
    model = get_chat_model()

    async def streamer():
        try:
            async for chunk in model.astream(prompt):
                if chunk and hasattr(chunk, 'content') and chunk.content:
                    yield chunk.content
        except Exception as e:
            print(f"[ERROR] AI streaming failed: {e}")
            # 에러 발생 시 기본 메시지
            if tone == "muneoz":
                yield """앗! AI가 삐끗했나봐! 😅

일반 채팅으로 "구독 추천해줘"라고 다시 시도해봐~ 🐙💜"""
            else:
                yield """AI 응답 생성 중 오류가 발생했어요. 😔

일반 채팅으로 **"구독 서비스 추천해주세요"**라고
다시 시도해주세요!"""

    return streamer