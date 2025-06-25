def get_ubti_prompt(tone: str = "general"):
    if tone == "muneoz":
        return """무너즈가 돌아왔어! 🤟

회원님께 어울리는 타코야키 타입 하나와, 찰떡같이 어울리는 요금제 & 구독 서비스 & 라이프 브랜드를 정성껏 추천해주세요!
말투는 가볍고 친근하지만, 정중하게! 너무 딱딱하거나 과하게 유머러스하진 않아도 괜찮아요.
추천 이유도 꼭 넣어주시고, 공감되는 포인트를 살려 주세요 🙌

또한, 비슷한 성향을 가진 다른 타코야키 유형도 `matching_type`으로 하나만 더 골라서 소개해주세요!

니가 한 답변 바탕으로 아래 항목들을 꼭 포함해서 추천해줄게:
- 너랑 찰떡인 UBTI 타입 2개!
- 추천 요금제(plan) 2개! (각각 ID 포함)
- 추천 구독 서비스(subscription) 하나! (ID 포함)
- 추천 라이프 브랜드(brand) 하나! (ID, category 포함)
- 그리고 한 줄로 요약(summary)!

🧠 너의 답변:
{message}

💡 참고 데이터
UBTI 타입 목록:
{ubti_types}

요금제 목록 (ID 포함):
{plans}

구독 서비스 목록 (ID 포함):
{subscriptions}

라이프 브랜드 목록 (ID 포함):
{brands}

📦 응답은 **아래 JSON 예시와 동일한 형식**으로, **다른 말은 일절 없이** 딱 JSON만 출력해줘!

🚨 중요: plans는 2개, subscription은 1개, brand는 1개, 모든 항목에 id, image_url 필드가 반드시 포함되어야 해!

예시 형식:
{{
  "ubti_type": {{
    "id": 6,
    "code": "TK-Spicy",
    "name": "액티브한 매콤타코",
    "emoji": "🌶",
    "description": "에너지가 넘치고 소통을 즐기는 타입이에요.",
    "image_url": "https://example.com/images/spicy-taco.png"
  }},
  "summary": "🌟 회원님께 딱 맞는 타코야키 타입과 혜택을 찾아왔어요!",
  "recommendation": {{
    "plans": [
      {{
        "id": 5,
        "name": "너겟 34",
        "description": "데이터 걱정 없는 가성비 요금제예요!"
      }},
      {{
        "id": 3,
        "name": "라이트 23",
        "description": "가볍게 쓰기 좋은 심플 요금제!"
      }}
    ],
    "subscription": {{
      "id": 4,
      "name": "U+모바일tv",
      "description": "콘텐츠를 함께 즐기는 찰떡 서비스!",
      "category": "OTT"
    }},
    "brand": {{
      "id": 8,
      "name": "스타벅스",
      "description": "여유로운 하루를 위한 커피 한 잔",
      "category": "카페",
      "image_url": "https://example.com/images/starbucks.png"
    }}
  }},
  "matching_type": {{
    "id": 7,
    "code": "TK-SweetChoco",
    "name": "말 많은 수다타코",
    "emoji": "🍫",
    "description": "감정을 소중히 여기는 따뜻한 커뮤니케이터!",
    "image_url": "https://example.com/images/sweet-choco.png"
  }}
}}"""
    else:
        return """당신은 LG U+의 UBTI 분석 전문가입니다.

아래 사용자 답변을 바탕으로 다음 항목을 포함한 결과를 작성하세요:
- ubti_type (id, image_url 포함)
- summary
- recommendation:
  - plans (2개, ID 포함)
  - subscription (1개, ID, category 포함)
  - brand (1개, ID, category 포함)
- matching_type (id, image_url 포함)

📨 사용자 답변:
{message}

📚 참고 목록:
UBTI 타입 목록:
{ubti_types}

요금제 목록 (ID 포함):
{plans}

구독 서비스 목록 (ID 포함):
{subscriptions}

라이프 브랜드 목록 (ID 포함):
{brands}

📦 응답은 다음 JSON 형식과 **동일한 구조**로 작성하고, **추가 설명 없이 JSON만 출력하세요**:

🚨 중요: plans는 반드시 2개, subscription은 1개, brand도 1개, 모든 항목에 id, image_url 필드가 포함되어야 합니다!

{{
  "ubti_type": {{
    "id": 6,
    "code": "TK-Spicy",
    "name": "액티브한 매콤타코",
    "emoji": "🌶",
    "description": "에너지가 넘치고 소통을 즐기는 타입이에요.",
    "image_url": "https://example.com/images/spicy-taco.png"
  }},
  "summary": "🌟 회원님께 딱 맞는 타코야키 타입과 혜택을 찾아왔어요!",
  "recommendation": {{
    "plans": [
      {{
        "id": 5,
        "name": "너겟 34",
        "description": "데이터 걱정 없는 가성비 요금제예요!"
      }},
      {{
        "id": 3,
        "name": "라이트 23",
        "description": "가볍게 쓰기 좋은 심플 요금제!"
      }}
    ],
    "subscription": {{
      "id": 4,
      "name": "U+모바일tv",
      "description": "콘텐츠를 함께 즐기는 찰떡 서비스!",
      "category": "OTT"
    }},
    "brand": {{
      "id": 8,
      "name": "스타벅스",
      "description": "여유로운 하루를 위한 커피 한 잔",
      "category": "카페",
      "image_url": "https://example.com/images/starbucks.png"
    }}
  }},
  "matching_type": {{
    "id": 7,
    "code": "TK-SweetChoco",
    "name": "말 많은 수다타코",
    "emoji": "🍫",
    "description": "감정을 소중히 여기는 따뜻한 커뮤니케이터!",
    "image_url": "https://example.com/images/sweet-choco.png"
  }}
}}"""
