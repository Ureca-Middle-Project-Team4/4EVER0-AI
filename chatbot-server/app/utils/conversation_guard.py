import os
import random
from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI

class ConversationGuard:
    """대화 가드레일 시스템 (기존 클래스명 유지)"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            api_key=os.getenv("OPENAI_API_KEY")
        )

    async def handle_off_topic(self, message: str, tone: str = "general") -> str:
        """오프토픽 응답 생성 (기존 함수명 유지, 내부 로직 향상)"""

        # 내부에서 세분화된 처리
        intent_classifier = EnhancedIntentClassifier()
        detailed_intent = await intent_classifier.classify_intent(message)

        if detailed_intent == "off_topic_interesting":
            return await self._handle_interesting_off_topic(message, tone)
        elif detailed_intent == "off_topic_unclear":
            return await self._handle_unclear_question(message, tone)
        else:
            return await self._handle_boring_off_topic(message, tone)

    async def _handle_interesting_off_topic(self, message: str, tone: str) -> str:
        """재미있지만 전문분야가 아닌 주제 응답 (내부 함수)"""
        if tone == "muneoz":
            responses = [
                "오~ 완전 느좋 주제네! 🤩\n근데 나는 그거보다 요금제가 더 재밌어! ㅋㅋㅋ\n\우리 요금제 얘기 해볼까? 🐙✨",
                "헉 그것도 느좋 주제인데! 😎\n하지만 내 추구미는 완전 요금제 전문가거든~\n\n그냥 통신 얘기로 넘어가자! 🤟💜",
                "와 싹싹김치! 재밌는 얘기네~ 🔥\n근데 나는 요금제 큐레이터라서 그쪽은 잘 몰라! 😅\n\n우리 요금제나 구독 얘기 할까? 🐙"
            ]
        else:
            responses = [
                "정말 흥미로운 주제네요! 😊\n하지만 저는 그것보다 통신 요금제가 더 재미있다고 생각해요! ㅎㅎ\n\n요금제 상담으로 화제를 바꿔볼까요?",
                "와! 멋진 이야기거네요! ✨\n다만 저의 전문 분야는 LG유플러스 서비스라서요~\n\n통신 관련 궁금한 점이 있으시면 언제든 말씀해주세요!",
                "오~ 그것도 정말 좋은 주제인데요! 🌟\n저는 요금제 전문가라서 그쪽 분야는 잘 몰라요 😅\n\n대신 통신비 절약 얘기는 어떠세요?"
            ]

        return random.choice(responses)

    async def _handle_boring_off_topic(self, message: str, tone: str) -> str:
        """일반적인 오프토픽 응답 (내부 함수)"""
        if tone == "muneoz":
            responses = [
                "음... 그건 내가 잘 모르겠어! 😅\n나는 요금제랑 구독만 완전 지리고 있거든!\n\n뭔가 통신 관련 궁금한 거 없어? 🐙",
                "아 그런 건 내 전문분야가 아니야~ 🤔\n대신 요금제는 퀸의 마인드로 추천해줄 수 있어!\n\n럭키비키하게 요금제 얘기 해보자! 🤟",
                "칠가이같은 질문이네! 😂\n나는 LG유플러스 전문가라서 그런 건 모르겠어~\n\n허거덩거덩스?! 요금제 상담 받아보는 건 어때? ✨"
            ]
        else:
            responses = [
                "죄송해요, 그 분야는 제가 잘 알지 못해요. 😔\n저는 LG유플러스 요금제와 구독 서비스만 전문적으로 상담드리고 있어요.\n\n통신 관련 문의사항이 있으시면 도움드리겠습니다!",
                "그 주제는 저의 전문 영역이 아니에요. 🤷‍♀️\n대신 요금제나 구독 서비스에 대해서는 자신있게 도움드릴 수 있답니다!\n\n어떤 서비스가 궁금하신가요?",
                "아쉽게도 그런 질문에는 답변드리기 어려워요. 😅\n저는 통신 요금제 전문 상담사라서요!\n\n요금제 관련해서 궁금한 점이 있으시면 언제든 말씀해주세요!"
            ]

        return random.choice(responses)

    async def _handle_unclear_question(self, message: str, tone: str) -> str:
        """질문을 이해하지 못했을 때 응답 (내부 함수)"""
        if tone == "muneoz":
            responses = [
                "어? 뭔 말인지 잘 모르겠어! 😵‍💫\n\n혹시 이런 거 물어본 거야?\n• 요금제 추천\n• 구독 서비스 추천\n• 현재 사용량 확인\n• UBTI 성향 분석\n\n알잘딱깔센하게 다시 말해줘! 🤟",
                "음... 내가 이해를 못한 것 같아! 🤯\n\n나는 이런 거 도와줄 수 있어:\n• 네 추구미에 맞는 요금제 찾기\n• 구독 서비스 큐레이팅\n• 데이터/통화 사용량 안내\n• 성향 분석\n\n다시 물어보는 것도 럭키비키잖앙?! 💜",
                "앗! 내가 뭔가 놓친 것 같아! 😅\n\n혹시 이런 얘기였어?\n• 럭키비키한 요금제 찾기\n• 너의 추구미 구독 서비스\n• 현재 요금제 상태 확인\n• UBTI 테스트\n\n다시 설명해줄래? 🐙✨"
            ]
        else:
            responses = [
                "죄송해요, 질문을 정확히 이해하지 못했어요. 😔\n\n혹시 이런 내용을 문의하신 건가요?\n• 요금제 추천 상담\n• 구독 서비스 추천\n• 현재 사용량 확인\n• 성향 분석 안내\n\n좀 더 구체적으로 말씀해주시겠어요?",
                "어떤 도움이 필요하신지 정확히 파악하지 못했네요. 🤔\n\n저는 다음과 같은 서비스를 제공합니다:\n• 맞춤형 요금제 추천\n• 구독 서비스 상담\n• 사용량 기반 분석\n• UBTI 성향 테스트\n\n어떤 서비스를 원하시는지 다시 말씀해주세요!",
                "무엇을 도와드려야 할지 명확하지 않네요. 😅\n\n제가 도움드릴 수 있는 영역은:\n• 요금제 비교 및 추천\n• OTT/음악 구독 서비스\n• 현재 요금제 상태 안내\n• 개인 성향 분석\n\n구체적으로 무엇이 궁금하신가요?"
            ]

        return random.choice(responses)

    async def handle_tech_issue(self, message: str, tone: str = "general") -> str:
        """기술적 문제 응답 (기존 함수명 유지)"""
        if tone == "muneoz":
            return """헉! 뭔가 서버 쪽에서 문제가 생긴 것 같아! 😵‍💫

럭키비키하지 못한 상황이네... 잠깐 뒤에 다시 말걸어줘! ✨

나는 요금제랑 구독 추천은 완전 자신 있으니까
그런 거 필요하면 언제든 말해줘~ 🐙"""
        else:
            return """기술적인 문제가 발생하신 것 같네요. 😔

저는 요금제와 구독 서비스 상담을 도와드릴 수 있으니
그런 문의사항이 있으시면 언제든 말씀해주세요! 😊"""

    async def handle_greeting(self, message: str, tone: str = "general") -> str:
        """인사 응답 (기존 함수명 유지, 2025년 유행어 반영)"""
        if tone == "muneoz":
            greetings = [
                "안뇽! 🤟 나는 무너야~ 🐙\n\n이 넓은 세상에서 우리가 만났다니.. 완전 럭키비키잖앙! ✨\n요금제랑 구독 전문가라서 완전 자신 있어!\n\n네 추구미에 딱 맞는 거 찾아줄게~ 💜",
                "야호! 🎉 무너 등장!\n\n무너즈 특) 요금제 무너한테 무러봄 ㅎㅎ\n알잘딱깔센하게 완전 찰떡인 거 추천해줄게! 🔥",
                "안뇽안뇽! 🤟\n\n무너 귀엽고 깜찍하게 등장~💜\n느좋한 요금제든 구독이든 뭐든지 말해봐~ 🐙\n\n싹싹김치!🥬🌶️"
            ]
        else:
            greetings = [
                "안녕하세요, 고객님! 😊\n\n저는 LG유플러스 AI 상담사입니다.\n\n요금제 추천부터 구독 서비스까지 도와드릴 수 있어요!\n\n어떤 도움이 필요하신가요?",
                "반갑습니다! ✨\n\nLG유플러스 요금제와 구독 서비스 전문 상담사입니다.\n\n고객님께 최적의 서비스를 추천해드리겠습니다.\n\n무엇을 도와드릴까요?",
                "안녕하세요! 🌟\n\n저는 LG유플러스 상담 AI입니다.\n\n요금제 상담, 구독 서비스 추천 등\n다양한 서비스를 제공하고 있어요!\n\n어떤 것부터 시작해볼까요?"
            ]

        return random.choice(greetings)

    async def handle_unknown(self, message: str, tone: str = "general") -> str:
        """알 수 없는 요청 처리 (기존 함수명 유지, 내부에서 unclear 처리)"""
        return await self._handle_unclear_question(message, tone)

    # ============= 추가된 오류 상황 처리 함수들 =============
    async def handle_loading_failure(self, tone: str = "general") -> str:
        """로딩 실패 시 응답 (새 함수)"""
        if tone == "muneoz":
            responses = [
                "앗! 뭔가 삐끗했나봐! 😵\n잠깐만 기다려줘~ 금방 다시 시도해볼게!\n\n칠가이하게 기다려줘! 🐙💜",
                "어? 로딩이 좀 이상해! 🤔\n럭키비키하게 다시 해보자!\n\n조금만 참아줘~ ✨",
                "앗차! 뭔가 꼬였나봐! 😅\n알잘딱깔센하게 다시 처리해볼게!\n\n싹싹김치! 금방 해결될 거야~ 🔥"
            ]
        else:
            responses = [
                "죄송해요, 잠시 로딩에 문제가 발생했어요. 😔\n조금만 기다려주시면 다시 시도해보겠습니다!\n\n잠시만요~ ⏳",
                "아! 시스템에 일시적인 문제가 있는 것 같아요. 😅\n곧바로 다시 처리해드리겠습니다!\n\n조금만 기다려주세요! ⏰",
                "로딩 중 오류가 발생했네요. 🔄\n다시 시도하고 있으니 잠시만 기다려주세요!\n\n금방 해결하겠습니다! 💫"
            ]

        return random.choice(responses)

    async def handle_api_error(self, tone: str = "general") -> str:
        """API 오류 시 응답 (새 함수)"""
        if tone == "muneoz":
            responses = [
                "어머 뭔가 서버가 삐끗했나봐! 😱\n내가 아니라 시스템 문제야!\n\n잠깐만 기다렸다가 다시 물어봐줘~ 🐙",
                "아이고! 뭔가 기술적 문제가 생겼어! 🤖💥\n나는 멀쩡한데 시스템이 좀 그래!\n\n칠가이하게 조금 뒤에 다시 시도해봐! 💜",
                "헉! 뭔가 서버 쪽에서 문제가 생긴 것 같아! 😵‍💫\n럭키비키하지 못한 상황이네...\n\n잠깐 뒤에 다시 말걸어줘! ✨"
            ]
        else:
            responses = [
                "죄송합니다. 일시적인 시스템 오류가 발생했어요. 😔\n잠시 후 다시 시도해주시면 정상적으로 도움드릴 수 있습니다.\n\n불편을 드려 죄송해요! 🙏",
                "시스템에 기술적 문제가 발생한 것 같아요. 😅\n조금 기다렸다가 다시 문의해주시겠어요?\n\n빠르게 해결하도록 하겠습니다! ⚡",
                "아! API 연결에 문제가 있는 것 같네요. 🔧\n잠시만 기다려주시면 다시 정상 작동할 거예요!\n\n조금만 참아주세요! 💪"
            ]

        return random.choice(responses)

    async def handle_timeout_error(self, tone: str = "general") -> str:
        """타임아웃 오류 시 응답 (새 함수)"""
        if tone == "muneoz":
            return """으악! 시간이 너무 오래 걸려서 타임아웃났어! ⏰💥

뭔가 복잡한 처리를 하다가 그런 것 같아!
칠가이하게 다시 한 번 시도해볼까? 🤟

아니면 좀 더 간단하게 질문해봐~
예를 들어 "3만원대 요금제 추천해줘" 이런 식으로! 💜"""
        else:
            return """요청 처리 시간이 초과되었어요. ⏰

복잡한 분석을 수행하다가 시간이 오래 걸린 것 같네요.
조금 더 구체적이고 간단한 질문으로 다시 시도해주시겠어요?

예: "월 3만원 이하 요금제 추천해주세요" 😊"""
