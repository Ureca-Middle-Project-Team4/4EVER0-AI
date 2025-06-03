async def detect_intent(message: str, user_context: dict = None) -> str:
    lowered = message.lower()

    # 기술적 문제
    error_keywords = ["에러", "오류", "깨짐", "한글자", "안보여"]
    if any(k in lowered for k in error_keywords):
        return "tech_issue"

    # 인사
    if any(k in lowered for k in ["안녕", "hi", "hello", "반가", "처음"]):
        return "greeting"

    # 구독 서비스
    if any(k in lowered for k in ["구독", "넷플릭스", "멜론", "유튜브프리미엄", "ott", "디즈니"]):
        return "subscription_recommend"

    # 요금제 멀티턴 판단
    if "추천" in lowered and any(k in lowered for k in ["요금제", "플랜"]):
        specific_conditions = ["데이터", "통화", "무제한", "만원", "저렴", "비싼", "GB", "유튜브", "SNS"]
        if any(c in lowered for c in specific_conditions):
            return "phone_plan_recommend"
        # 이전에 수집된 정보가 있다면 바로 추천
        if user_context and ("data_usage" in user_context or "call_usage" in user_context):
            return "phone_plan_recommend"
        return "phone_plan_multi"

    # 일반 요금제 문의
    if any(k in lowered for k in ["요금제", "5g", "lte", "통화", "데이터"]):
        return "phone_plan_recommend"

    # 기타 일반 문의
    if any(k in lowered for k in ["문의", "질문", "도움", "상담", "알고싶"]):
        return "inquiry"

    return "default"
