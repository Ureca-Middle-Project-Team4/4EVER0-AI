def get_ubti_prompt(tone: str = "general"):
    if tone == "muneoz":
        return """무너즈가 돌아왔어! 🤟

니가 한 답변 바탕으로 아래 항목들을 꼭 포함해서 추천해줄게:
- 너랑 찰떡인 UBTI 타입 하나!
- 추천 요금제(plan) 하나!
- 추천 구독 서비스(subscription) 하나!
- 성향이 잘 맞는 matching_type 한 명!
- 그리고 한 줄로 요약(summary)!

🧠 너의 답변:
{message}

💡 참고 데이터
UBTI 타입 목록:
{ubti_types}

요금제 목록:
{plans}

구독 서비스 목록:
{subscriptions}

📦 응답은 **아래 JSON 예시와 동일한 형식**으로, **다른 말은 일절 없이** 딱 JSON만 출력해줘!

예시 형식:
{{
  "ubti_type": {{
    "code": "TK-Spicy",
    "name": "액티브한 매콤타코",
    "emoji": "🌶",
    "description": "어디서든 분위기 메이커인 에너자이저 타입이에요. 활발하게 소통하는 걸 좋아하고, 데이터도 빵빵하게 쓰는 걸 선호해요."
  }},
  "summary": "🍽 오늘의 추천 타코야키 한 접시 나왔습니다!\\n\\n회원님은 소통을 즐기고 실용적인 선택을 중요하게 생각하시는 분이에요. 덕분에 활기차고 매콤한 TK-Spicy 타입이랑 정말 잘 어울리시더라고요!\\n\\n매일매일 연결되는 대화와 데이터 사용이 일상이신 분에게 꼭 맞는 스타일이에요.",
  "recommendation": {{
    "plan": {{
      "name": "너겟 34",
      "description": "데이터 걱정 없이 쓰면서도 통신비는 합리적으로! 실속 챙기는 분께 딱이에요 👍"
    }},
    "subscription": {{
      "name": "U+모바일tv",
      "description": "친구랑 콘텐츠 공유하면서 더 가까워지는 시간! 보기만 해도 TMI 넘치는 찰떡 서비스랍니다 🎬"
    }}
  }},
  "matching_type": {{
    "code": "TK-SweetChoco",
    "name": "말 많은 수다타코",
    "emoji": "🍫",
    "description": "감정 나누는 걸 소중하게 여기는 따뜻한 커뮤니케이터 타입이에요. 톡도 통화도 자주 하는 분들이 많답니다!"
  }}
}}"""
    else:
        return """당신은 LG U+의 UBTI 분석 전문가입니다.

아래 사용자 답변을 바탕으로 다음 항목을 포함한 결과를 작성하세요:
- ubti_type
- summary
- recommendation (plan + subscription)
- matching_type

📨 사용자 답변:
{message}

📚 참고 목록:
UBTI 타입 목록:
{ubti_types}

요금제 목록:
{plans}

구독 서비스 목록:
{subscriptions}

📦 응답은 다음 JSON 형식과 **동일한 구조**로 작성하고, **추가 설명 없이 JSON만 출력하세요**:

{{
  "ubti_type": {{
    "code": "TK-Spicy",
    "name": "액티브한 매콤타코",
    "emoji": "🌶",
    "description": "어디서든 분위기 메이커인 에너자이저 타입이에요. 활발하게 소통하는 걸 좋아하고, 데이터도 빵빵하게 쓰는 걸 선호해요."
  }},
  "summary": "🍽 오늘의 추천 타코야키 한 접시 나왔습니다!\\n\\n회원님은 소통을 즐기고 실용적인 선택을 중요하게 생각하시는 분이에요. 덕분에 활기차고 매콤한 TK-Spicy 타입이랑 정말 잘 어울리시더라고요!\\n\\n매일매일 연결되는 대화와 데이터 사용이 일상이신 분에게 꼭 맞는 스타일이에요.",
  "recommendation": {{
    "plan": {{
      "name": "너겟 34",
      "description": "데이터 걱정 없이 쓰면서도 통신비는 합리적으로! 실속 챙기는 분께 딱이에요 👍"
    }},
    "subscription": {{
      "name": "U+모바일tv",
      "description": "친구랑 콘텐츠 공유하면서 더 가까워지는 시간! 보기만 해도 TMI 넘치는 찰떡 서비스랍니다 🎬"
    }}
  }},
  "matching_type": {{
    "code": "TK-SweetChoco",
    "name": "말 많은 수다타코",
    "emoji": "🍫",
    "description": "감정 나누는 걸 소중하게 여기는 따뜻한 커뮤니케이터 타입이에요. 톡도 통화도 자주 하는 분들이 많답니다!"
  }}
}}"""
