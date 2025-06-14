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

    # 2. 메인 구독, 라이프 브랜드 전체 조회
    subscriptions = get_products_from_db()
    brands = get_life_brands_from_db()

    # 3. 포맷팅 - 명시적 줄바꿈 적용
    main = "\\n\\n".join([
        f"- {s.title} / {s.price}원 / {s.category}" for s in subscriptions
    ])
    life = "\\n\\n".join([
        f"- {b.name} / {b.description}" for b in brands if b.id in liked_brand_ids
    ])

    # 4. 프롬프트 구성 (tone 파라미터 전달)
    prompt = get_like_prompt(tone).format(  # tone 파라미터 추가!
        main=main,
        life=life
    )

    # 5. GPT 스트리밍
    model = get_chat_model()

    async def streamer():
        async for chunk in model.astream(prompt):
            yield chunk.content

    return streamer