async def detect_intent(message: str, user_context: dict = None) -> str:
    lowered = message.lower()

    # 기술적 문제
    error_keywords = ["에러", "오류", "깨짐", "한글자", "안보여", "처음으로"]
    if any(k in lowered for k in error_keywords):
        return "tech_issue"

    # 인사
    greeting_keywords = ["안녕", "hi", "hello", "반가", "처음"]
    if any(k in lowered for k in greeting_keywords):
        return "greeting"

    # UBTI 검사 (단일 응답 유지)
    ubti_keywords = ["ubti", "mbti", "통신 성향", "통신 mbti", "ubti 검사", "ubti 테스트", "타코시그널"]
    if any(k in lowered for k in ubti_keywords):
        return "ubti_recommend"

    # 구독 서비스 - 구체적 조건 확인
    subscription_keywords = ["구독", "유독", "넷플릭스", "지니뮤직", "유튜브프리미엄", "ott", "디즈니"]
    if any(k in lowered for k in subscription_keywords):
        # 구체적 선호도가 언급되면 바로 추천
        specific_prefs = ["좋아해", "선호", "즐겨", "자주 봐", "많이 봐", "드라마", "영화", "음악", "스포츠"]
        if any(c in lowered for c in specific_prefs):
            return "subscription_recommend"
        return "subscription_multi"

    # 요금제 - 멀티턴 우선 (매우 구체적인 조건이 아닌 이상)
    plan_keywords = ["요금제", "5g", "lte", "통화", "데이터", "무제한", "플랜", "추천"]
    if any(k in lowered for k in plan_keywords):
        # 매우 구체적인 조건들 (가격대 + 데이터량 동시 언급 등)
        has_price = any(p in lowered for p in ["만원", "천원", "원"])
        has_data = any(d in lowered for d in ["gb", "기가", "무제한"])
        has_usage = any(u in lowered for u in ["많이", "적게", "조금", "자주"])

        # 3개 이상의 구체적 조건이 있을 때만 바로 추천
        specific_count = sum([has_price, has_data, has_usage])
        if specific_count >= 2:
            return "phone_plan_recommend"

        # 그 외에는 멀티턴으로 유도
        return "phone_plan_multi"

    # 일반 문의
    inquiry_keywords = ["문의", "질문", "도움", "상담", "알고싶", "잘 모르", "궁금"]
    if any(k in lowered for k in inquiry_keywords):
        return "inquiry"

    return "default"