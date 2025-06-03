from app.schemas.recommend import UserProfile

def generate_reason_only_prompt(user: UserProfile) -> str:
    return f"""
당신은 LG U+ 상품 추천 전문가입니다.
고객 정보에 맞는 상품을 하나 고르고, 그 이유만 간단하고 따뜻하게 추천해주세요.

고객 정보:
- 연령대: {user.age_group}
- 관심사: {', '.join(user.interests)}
- 여가 시간 활용: {', '.join(user.time_usage)}

🎯 추천 이유를 자연스럽고 친근하게 작성해주세요.
JSON 형식 없이 텍스트로만 출력하세요.
예시: "영상 콘텐츠를 좋아하시는 20대에게 딱 어울리는 상품이에요! 😊"
"""