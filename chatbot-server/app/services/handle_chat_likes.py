from app.schemas.chat import LikesChatRequest
from app.db.coupon_like_db import get_liked_brand_ids
from app.db.brand_db import get_life_brands_from_db
from app.db.subscription_db import get_products_from_db
from app.prompts.like_prompt import get_like_prompt
from app.utils.langchain_client import get_chat_model


def get_brand_names_by_ids(brand_ids: list[int]) -> list[str]:
    all_brands = get_life_brands_from_db()
    return [b.name for b in all_brands if b.id in brand_ids]


def filter_subscriptions_by_brand_names(brand_names: list[str]):
    all_subscriptions = get_products_from_db()
    return [
        s for s in all_subscriptions
        if any(brand in s.title or brand in s.category for brand in brand_names)
    ]


async def handle_chat_likes(req: LikesChatRequest):
    liked_brand_ids = get_liked_brand_ids(req.session_id)
    brand_names = get_brand_names_by_ids(liked_brand_ids)
    subscriptions = filter_subscriptions_by_brand_names(brand_names)

    brands_text = ", ".join(brand_names)
    subscriptions_text = "\n".join([
        f"- {s.title} / {s.price}원 / {s.category}" for s in subscriptions
    ])

    prompt = get_like_prompt().format(
        brands=brands_text,
        subscriptions=subscriptions_text
    )

    model = get_chat_model()

    async def streamer():
        async for chunk in model.astream(prompt):
            yield chunk.content

    return streamer
