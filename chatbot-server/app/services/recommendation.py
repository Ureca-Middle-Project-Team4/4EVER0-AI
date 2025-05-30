from fastapi import FastAPI, APIRouter
from pydantic import BaseModel
from typing import List, Optional
from app.db.database import SessionLocal
from app.db.models import Subscription
from openai import OpenAI
import os
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# FastAPI setup
app = FastAPI()
router = APIRouter()

# Pydantic models
class UserProfile(BaseModel):
    age_group: str
    interests: List[str]
    time_usage: List[str]

class RecommendedItem(BaseModel):
    title: str
    description: str
    image_url: str
    detail_url: str
    price: str
    reason: Optional[str] = None

DEFAULT_RECOMMENDATION = {
    "title": "더블 스트리밍 연간권",
    "description": "넷플릭스+유튜브 프리미엄 국내 유일 월 15,900원!",
    "image_url": "https://www.lguplus.com/static-pogg/pc-contents/images/pogg/20241022-034447-076-xJJotJRj.png",
    "detail_url": "https://www.lguplus.com/pogg/product/double-streaming",
    "price": "15,900원",
    "reason": "다양한 콘텐츠를 한 번에 즐기고 싶은 모든 세대를 위한 유독 BEST 1위 상품이에요!"
}


# TF-IDF 기반 추천 함수
def get_similarity_recommendations(user: UserProfile, products):
    user_keywords = " ".join(user.interests + user.time_usage + [user.age_group])
    corpus = [user_keywords] + [f"{p.title} {p.description}" for p in products]

    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(corpus)
    cosine_sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()

    scored = list(zip(products, cosine_sim))
    scored.sort(key=lambda x: x[1], reverse=True)

    return scored[:1]  # 유사도 점수 기반 상위 1개만 반환

# GPT 리랭킹 함수 (OpenAI SDK v1+)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def rerank_with_gpt(user: UserProfile, scored_items):
    prompt_data = [
        {"title": p.title, "description": p.description} for p, _ in scored_items
    ]
    prompt = (
        f"다음은 사용자에게 맞는 추천 상품 후보입니다.\n"
        f"사용자 정보:\n"
        f"- 나이대: {user.age_group}\n"
        f"- 관심사: {', '.join(user.interests)}\n"
        f"- 여가 시간 활용 방식: {', '.join(user.time_usage)}\n\n"
        f"상품 리스트:\n{json.dumps(prompt_data, ensure_ascii=False, indent=2)}\n\n"
        f"위 정보를 바탕으로 가장 적합한 상위 3개 상품을 골라주세요.\n"
        f"각 상품에 대해 간결하고 친절한 추천 이유를 덧붙여주세요.\n\n"
        f"아래와 같은 형식으로 한국어로 결과를 출력해주세요:\n"
        f"[\n  {{\"title\": \"상품명\", \"reason\": \"추천 이유\" }}, ...\n]"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print("GPT 호출 또는 파싱 실패:", e)
        return []

# 추천 로직 통합
def get_recommendations(user: UserProfile):
    db = SessionLocal()
    products = db.query(Subscription).all()
    db.close()

    top_candidates = get_similarity_recommendations(user, products)

    # 유사한 상품이 하나도 없을 경우
    if not top_candidates:
        return [DEFAULT_RECOMMENDATION]

    gpt_reranked = rerank_with_gpt(user, top_candidates)
    if not gpt_reranked:
        return [DEFAULT_RECOMMENDATION]

    title_to_product = {p.title: p for p, _ in top_candidates}

    results = []
    for item in gpt_reranked:
        title = item.get("title")
        reason = item.get("reason")
        product = title_to_product.get(title)
        if product:
            results.append({
                "title": product.title,
                "description": product.description,
                "image_url": product.image_url,
                "detail_url": product.detail_url,
                "price": product.price,
                "reason": reason
            })

    # GPT가 예기치 않게 빈 결과를 준 경우도 대비
    if not results:
        return [DEFAULT_RECOMMENDATION]

    return results


# FastAPI endpoint
@router.post("/recommend", response_model=List[RecommendedItem])
def recommend(user: UserProfile):
    return get_recommendations(user)

# 라우터 등록
app.include_router(router, prefix="/api")
