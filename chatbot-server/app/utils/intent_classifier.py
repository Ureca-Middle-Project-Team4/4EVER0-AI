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
5. **ubti**: UBTI, 타코시그널, MBTI, 성향 분석 관련,
6. **greeting**: 인사, 처음 방문
7. **off_topic**: 요금제/구독과 무관한 질문
8. **tech_issue**: 기술적 문제, 오류

📋 **판단 기준:**
- telecom_plan_direct: "3만원대 무제한 요금제", "게임용 5G 요금제" 등 구체적 조건 2개 이상
- off_topic: 날씨, 맛집, 프로그래밍, 일반 상식 등 통신과 무관
- current_usage: "남은 데이터", "현재 요금제", "사용량 확인" 등

사용자 메시지: "{message}"

응답 형식: 인텐트명만 출력 (예: telecom_plan)
""")

    async def classify_intent(self, message: str, context: Dict[str, Any] = None) -> str:
        """AI 기반 정확한 인텐트 분류"""
        try:
            chain = self.intent_prompt | self.llm
            response = await chain.ainvoke({"message": message})
            intent = response.content.strip().lower()

            # 유효한 인텐트인지 검증
            valid_intents = [
                "telecom_plan", "telecom_plan_direct", "subscription",
                "current_usage", "ubti", "greeting", "off_topic", "tech_issue"
            ]

            if intent in valid_intents:
                return intent
            else:
                # 폴백 로직
                return self._fallback_classification(message)

        except Exception as e:
            print(f"[ERROR] Intent classification failed: {e}")
            return self._fallback_classification(message)

    def _fallback_classification(self, message: str) -> str:
        """AI 실패시 키워드 기반 폴백"""
        lowered = message.lower()

        # 확실한 오프토픽 감지
        off_topic_keywords = [
            "날씨", "맛집", "영화", "음식", "여행", "취미",
            "프로그래밍", "코딩", "파이썬", "자바", "리액트",
            "공부", "학교", "대학교", "취업", "연애", "건강"
        ]
        if any(k in lowered for k in off_topic_keywords):
            return "off_topic"

        # 인사
        if any(k in lowered for k in ["안녕", "hi", "hello", "반가", "처음"]):
            return "greeting"

        # 현재 사용량
        if any(k in lowered for k in ["남은", "현재", "사용량", "얼마나 썼", "잔여"]):
            return "current_usage"

        # 기본적으로 요금제 관련으로 분류
        return "telecom_plan"


# app/utils/conversation_guard.py
class ConversationGuard:
    """대화 가드레일 시스템"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            api_key=os.getenv("OPENAI_API_KEY")
        )

    async def handle_off_topic(self, message: str, tone: str = "general") -> str:
        """오프토픽 응답 생성"""
        if tone == "muneoz":
            responses = [
                "앗! 그것도 궁금하긴 한데 🤔\n나는 요금제랑 구독 전문가라서 그쪽은 잘 몰라!\n\n대신 요금제나 구독 서비스 추천은 맡겨줘~ 🐙💜",
                "오오 재밌는 질문이네! 😊\n근데 나는 LG유플러스 요금제 큐레이터라서 그런 건 잘 몰라 ㅠㅠ\n\n요금제나 구독 얘기면 내가 완전 전문가야! 뭐 필요해? 🤟",
                "ㅋㅋ 그건 나도 궁금해! 🤭\n근데 내 전문 분야는 요금제랑 구독이라서...\n\n통신 관련해서 궁금한 거 있으면 편하게 물어봐! ✨"
            ]
        else:
            responses = [
                "흥미로운 질문이시네요! 😊\n다만 저는 LG유플러스 요금제와 구독 서비스 전문 상담사라서 해당 분야는 잘 모르겠어요.\n\n요금제나 구독 서비스 관련해서는 언제든 도움드릴 수 있습니다!",
                "좋은 질문이에요! 🤔\n아쉽게도 저는 통신 요금제와 구독 서비스만 전문적으로 상담드리고 있어요.\n\n요금제 추천이나 구독 서비스에 대해 궁금한 점이 있으시면 말씀해주세요!",
                "관심 있는 주제시군요! ✨\n저는 LG유플러스의 요금제와 구독 서비스 상담을 담당하고 있어서 다른 분야는 잘 알지 못해요.\n\n통신 관련 문의사항이 있으시면 언제든 도움드리겠습니다!"
            ]

        import random
        return random.choice(responses)

    async def handle_tech_issue(self, message: str, tone: str = "general") -> str:
        """기술적 문제 응답"""
        if tone == "muneoz":
            return """아이고 뭔가 문제가 있나봐? 😅

기술적인 문제는 내가 직접 해결하기 어려워서
LG유플러스 고객센터 1544-0010 으로 문의해보는 게 좋을 것 같아!

요금제랑 구독 추천은 완전 자신 있으니까
그런 거 필요하면 언제든 말해줘~ 🐙"""
        else:
            return """기술적인 문제가 발생하신 것 같네요. 😔

이런 경우에는 LG유플러스 고객센터(1544-0010)에서
전문적인 기술 지원을 받으시는 것이 가장 좋습니다.

저는 요금제와 구독 서비스 상담을 도와드릴 수 있으니
관련 문의사항이 있으시면 언제든 말씀해주세요! 😊
"""
