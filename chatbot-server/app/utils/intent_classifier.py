import os
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import asyncio

class EnhancedIntentClassifier:
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1,  # 일관성을 위해 낮은 temperature
            api_key=os.getenv("OPENAI_API_KEY")
        )

        self.intent_prompt = ChatPromptTemplate.from_template("""
당신은 LG유플러스 챗봇의 인텐트 분류 전문가입니다.

사용자 메시지를 분석하여 정확한 인텐트를 분류해주세요.

🎯 **분류 규칙:**
1. **telecom_plan**: 요금제, 통신비, 데이터, 통화 관련 (멀티턴 필요)
2. **telecom_plan_direct**: 매우 구체적인 요금제 요청 (바로 추천)
3. **subscription**: 구독 서비스, OTT, 음악 관련
4. **current_usage**: 현재 요금제 상태, 남은 데이터/통화량 확인
5. **ubti**: UBTI, 타코시그널, MBTI, 성향 분석 관련
6. **greeting**: 인사, 처음 방문
7. **off_topic**: 요금제/구독과 무관한 질문 (세분화됨)
8. **tech_issue**: 기술적 문제, 오류

📋 **off_topic 세분화:**
- 재미있는 주제 (영화, 맛집, 여행, 취미, 연예인) → off_topic_interesting
- 일반 주제 (날씨, 시간, 일반상식, 프로그래밍) → off_topic_boring
- 질문 의도 불명확 → off_topic_unclear

📋 **판단 기준:**
- telecom_plan_direct: "3만원대 무제한 요금제", "게임용 5G 요금제" 등 구체적 조건 2개 이상
- off_topic_interesting: 영화, 맛집, 여행, 취미, 연예인 등 흥미로운 주제
- off_topic_boring: 날씨, 시간, 일반 상식 등 평범한 질문
- off_topic_unclear: 문맥이 애매하거나 여러 해석이 가능한 경우

사용자 메시지: "{message}"

응답 형식: 기본 인텐트명 또는 세분화된 인텐트명 (예: off_topic_interesting)
""")

    async def classify_intent(self, message: str, context: Dict[str, Any] = None) -> str:
        """AI 기반 정확한 인텐트 분류"""
        try:
            # 입력 검증
            if not message or len(message.strip()) == 0:
                return "off_topic_unclear"

            chain = self.intent_prompt | self.llm
            response = await chain.ainvoke({"message": message})
            intent = response.content.strip().lower()

            # 유효한 인텐트인지 검증 (세분화된 것 포함)
            valid_intents = [
                "telecom_plan", "telecom_plan_direct", "subscription",
                "current_usage", "ubti", "greeting", "tech_issue",
                "off_topic", "off_topic_interesting", "off_topic_boring", "off_topic_unclear"
            ]

            if intent in valid_intents:
                print(f"[DEBUG] AI classified intent: {intent}")
                return intent
            else:
                # 폴백 로직
                print(f"[DEBUG] AI returned invalid intent: {intent}, using fallback")
                return self._fallback_classification(message)

        except Exception as e:
            print(f"[ERROR] Intent classification failed: {e}")
            return self._fallback_classification(message)

    def _fallback_classification(self, message: str) -> str:
        """AI 실패시 키워드 기반 폴백"""
        lowered = message.lower().strip()

        # 입력이 너무 짧거나 비어있는 경우
        if len(lowered) < 2:
            return "off_topic_unclear"

        # 인사 감지 (우선순위 높음)
        greeting_keywords = ["안녕", "hi", "hello", "반가", "처음", "시작", "헬로"]
        if any(k in lowered for k in greeting_keywords):
            return "greeting"

        # 현재 사용량 관련
        usage_keywords = ["남은", "현재", "사용량", "얼마나 썼", "잔여", "상태", "확인"]
        if any(k in lowered for k in usage_keywords):
            return "current_usage"

        # UBTI 관련
        ubti_keywords = ["ubti", "성향", "분석", "테스트", "mbti", "타코"]
        if any(k in lowered for k in ubti_keywords):
            return "ubti"

        # 요금제 관련 (구체적 vs 일반)
        plan_keywords = ["요금제", "통신비", "데이터", "통화", "5g", "lte", "플랜"]
        specific_keywords = ["원", "gb", "무제한", "만원", "게임용", "비즈니스"]

        if any(k in lowered for k in plan_keywords):
            # 구체적 조건이 있으면 direct
            if any(k in lowered for k in specific_keywords) and len([k for k in specific_keywords if k in lowered]) >= 2:
                return "telecom_plan_direct"
            else:
                return "telecom_plan"

        # 구독 서비스 관련
        subscription_keywords = ["구독", "ott", "넷플릭스", "유튜브", "음악", "동영상", "스트리밍"]
        if any(k in lowered for k in subscription_keywords):
            return "subscription"

        # 재미있는 오프토픽 감지
        interesting_keywords = [
            "영화", "드라마", "음식", "맛집", "여행", "연예인", "취미",
            "게임", "스포츠", "음악", "책", "카페", "쇼핑", "연애", "친구"
        ]
        if any(k in lowered for k in interesting_keywords):
            return "off_topic_interesting"

        # 일반 오프토픽 감지
        boring_keywords = [
            "날씨", "시간", "프로그래밍", "코딩", "파이썬", "자바", "리액트",
            "공부", "학교", "대학교", "취업", "건강", "운동", "뉴스"
        ]
        if any(k in lowered for k in boring_keywords):
            return "off_topic_boring"

        # 기술 문제 관련
        tech_keywords = ["오류", "에러", "문제", "안돼", "작동", "버그", "느려"]
        if any(k in lowered for k in tech_keywords):
            return "tech_issue"

        # 너무 애매하거나 판단하기 어려운 경우
        unclear_patterns = [
            len(lowered) < 3,  # 너무 짧음
            lowered in ["?", "??", "뭐", "음", "어", "그냥"],  # 의미없는 단어
            "?" in lowered and len(lowered) < 10,  # 짧은 질문
        ]

        if any(unclear_patterns):
            return "off_topic_unclear"

        # 기본적으로 일반 요금제 관련으로 분류
        return "telecom_plan"