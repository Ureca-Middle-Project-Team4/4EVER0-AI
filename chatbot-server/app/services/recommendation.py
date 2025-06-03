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
    "reason": "다양한 콘텐츠를 한 번에 즐기고 싶은 모든 세대를 위한 LG U+ BEST 1위 상품이에요! 🎬"
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

    return scored[:3]  # 상위 3개로 늘려서 GPT가 선택할 여지를 줌

# GPT 리랭킹 함수 (LG U+ 브랜드 톤앤매너 적용)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def rerank_with_gpt(user: UserProfile, scored_items):
    prompt_data = [
        {"title": p.title, "description": p.description} for p, _ in scored_items
    ]

    # LG U+에 맞는 친근하고 개인화된 프롬프트
    prompt = f"""
당신은 LG U+의 친근한 상품 추천 전문가입니다. 
고객에게 딱 맞는 상품을 찾아서 따뜻하고 개인적인 추천을 해주세요.

🙋‍♀️ 고객 정보:
• 연령대: {user.age_group}
• 관심분야: {', '.join(user.interests)}
• 여가시간 활용법: {', '.join(user.time_usage)}

📱 추천 상품 후보:
{json.dumps(prompt_data, ensure_ascii=False, indent=2)}

💡 추천 가이드라인:
- 고객의 라이프스타일과 취향을 고려해서 가장 적합한 상품 1개를 골라주세요
- 추천 이유는 마치 친구가 추천해주는 것처럼 친근하고 구체적으로 작성해주세요
- "~하시는 분께", "~할 때 딱이에요", "~라서 추천드려요" 같은 자연스러운 표현 사용
- 이모지를 적절히 활용해서 친근함을 더해주세요
- LG U+만의 특별한 혜택이나 장점이 있다면 자연스럽게 언급해주세요

아래 JSON 형식으로 결과를 출력해주세요:
[
  {{"title": "상품명", "reason": "개인맞춤 추천 이유"}}
]
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,  # 좀 더 창의적이고 자연스러운 응답을 위해 온도 증가
            max_tokens=1000
        )
        content = response.choices[0].message.content
        # JSON 파싱을 위해 코드 블록 제거
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        return json.loads(content.strip())
    except Exception as e:
        print("GPT 호출 또는 파싱 실패:", e)
        return []

# 추천 로직 통합
def get_recommendations(user: UserProfile):
    db = SessionLocal()
    products = db.query(Subscription).all()
    db.close()

    # 상품이 없는 경우 기본 추천
    if not products:
        return [DEFAULT_RECOMMENDATION]

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
    """
    사용자 프로필 기반 LG U+ 상품 추천 API
    - TF-IDF 유사도와 GPT-4 기반 개인화 추천
    - 친근하고 자연스러운 추천 이유 제공
    """
    return get_recommendations(user)

# 라우터 등록
app.include_router(router, prefix="/api")