def get_usage_recommendation_prompt(tone: str = "general"):
    if tone == "muneoz":
        return """야! 네 현재 요금제 사용량 체크해봤어! 🔍

📊 **현재 상황**
• 요금제: {current_plan} ({current_price})
• 남은 데이터: {remaining_data}
• 남은 통화: {remaining_voice}
• 남은 문자: {remaining_sms}
• 전체 사용률: {usage_percentage}

📋 **분석 결과**: {recommendation_type}

🎯 **추천 요금제들**
{available_plans}

📌 **무너 추천 가이드:**
- upgrade: 거의 다 썼으니 더 큰 요금제 추천
- downgrade: 너무 안 썼으니 저렴한 요금제 추천
- maintain: 딱 적당히 쓰고 있으니 현재 유지
- alternative: 사용 패턴에 맞는 다른 옵션 제시

✅ **이렇게 써봐:**
현재 상황 간단 요약 → 추천 이유 → 구체적 요금제 1-2개 제시 → 마무리 멘트

예시: "오! 데이터 거의 다 썼네? 😱 그럼 더 넉넉한 요금제로 바꿔보는 게 어때?"
"""
    else:
        return """고객님의 현재 요금제 사용 현황을 분석해드립니다.

📊 **현재 이용 상황**
• 현재 요금제: {current_plan} ({current_price})
• 남은 데이터: {remaining_data}
• 남은 통화시간: {remaining_voice}
• 남은 문자: {remaining_sms}
• 전체 사용률: {usage_percentage}

📋 **분석 결과**: {recommendation_type}

🎯 **이용 가능한 요금제**
{available_plans}

📌 **추천 가이드라인:**
- upgrade: 사용량이 많아 상위 요금제 권장
- downgrade: 사용량이 적어 하위 요금제 권장
- maintain: 현재 요금제가 적합하여 유지 권장
- alternative: 사용 패턴에 더 적합한 대안 제시

✅ **응답 형식:**
현재 상황 분석 → 추천 근거 → 구체적 요금제 추천 → 추가 안내

정중하고 전문적인 톤으로 고객님께 최적의 요금제를 추천해주세요.
"""
