import os
import random
from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from app.utils.redis_client import get_session

class ConversationGuard:
    """대화 가드레일 시스템"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            api_key=os.getenv("OPENAI_API_KEY")
        )

    def _get_user_name(self, session_id: str = None) -> str:
        """세션에서 사용자 이름 가져오기 - name 필드 있을 때만"""
        if not session_id:
            return ""

        try:
            session = get_session(session_id)
            user_name = session.get("name") or session.get("user_name")
            return f"{user_name}님, " if user_name else ""
        except Exception as e:
            print(f"[DEBUG] Name retrieval failed: {e}")
            return ""

    async def handle_off_topic(self, message: str, tone: str = "general", session_id: str = None) -> str:
        """오프토픽 응답 생성 - 개인화"""

        # 유저 정보 가져오기
        name_part = self._get_user_name(session_id)

        # 세분화된 인텐트에 따른 처리
        from app.utils.intent_classifier import EnhancedIntentClassifier
        intent_classifier = EnhancedIntentClassifier()
        detailed_intent = await intent_classifier.classify_intent(message)

        print(f"[DEBUG] Off-topic detailed intent: {detailed_intent}")

        if detailed_intent == "nonsense":
            return await self._handle_nonsense_input(message, tone, name_part)
        elif detailed_intent == "off_topic_interesting":
            return await self._handle_interesting_off_topic(message, tone, name_part)
        elif detailed_intent == "off_topic_unclear":
            return await self._handle_unclear_question(message, tone, name_part)
        elif detailed_intent == "off_topic_boring":
            return await self._handle_boring_off_topic(message, tone, name_part)
        else:
            # 기본 오프토픽 처리
            return await self._handle_general_off_topic(message, tone, name_part)

    async def _handle_nonsense_input(self, message: str, tone: str, name_part: str = "") -> str:
        """의미없는/테스트 입력 처리"""

        if tone == "muneoz":
            responses = [
                f"어? {name_part}뭔가 이상한 말이야! 😵‍💫\n혹시 키보드가 삐끗했어?\n\n제대로 된 질문으로 다시 말해봐~ 🤟💜",
                f"앗! {name_part}무슨 말인지 전혀 모르겠어! 🤯\n\n나는 이런 거 도와줄 수 있어:\n• 요금제 추천\n• 구독 서비스 추천\n\n칠가이하게 제대로 된 질문 해봐! 🐙",
                f"헉! {name_part}뭔가 암호같은 말이네! 🔤❓\n\n혹시 이런 걸 물어보려던 거야?\n• \"요금제 찾아줘\"\n• \"구독 추천해줘\"\n\n알잘딱깔센하게 다시 말해줘~ ✨"
            ]
        else:
            responses = [
                f"{name_part}죄송해요, 입력하신 내용을 이해하지 못했어요. 😔\n\n명확한 질문으로 다시 문의해주시겠어요?\n\n예시:\n• \"요금제 추천해주세요\"\n• \"구독 서비스 추천 부탁드려요\"",
                f"{name_part}입력하신 내용이 명확하지 않네요. 🤔\n\n구체적인 질문을 해주시면 더 정확한 도움을 드릴 수 있어요!\n\n저는 다음과 같은 서비스를 제공합니다:\n• 요금제 상담 및 추천\n• 구독 서비스 추천",
                f"{name_part}무엇을 문의하시는지 정확히 파악하지 못했어요. 😅\n\n좀 더 구체적으로 말씀해주시면 정확한 답변을 드리겠습니다!\n\n💡 팁: \"OO 추천해주세요\" 형태로 질문해보세요!"
            ]

        return random.choice(responses)

    async def _handle_interesting_off_topic(self, message: str, tone: str, name_part: str = "") -> str:
        """재미있는 오프토픽 - 주제별 맞춤 응답"""

        message_lower = message.lower()

        # 영화/드라마 관련
        if any(word in message_lower for word in ["영화", "드라마", "넷플릭스", "시청"]):
            if tone == "muneoz":
                return f"오~ {name_part}영화 얘기구나! 완전 느좋한 주제네~ 🎬\n근데 나는 그거보다 구독 서비스가 더 재밌어! ㅋㅋㅋ\n\n넷플릭스나 디즈니+ 같은 구독 서비스는 어때? 럭키비키하게 추천해줄 수 있어! 🐙✨"
            else:
                return f"{name_part}영화에 관심이 많으시군요! 🎬\n그렇다면 OTT 구독 서비스는 어떠세요?\n\n그렇다면 유독 픽을 추천해드릴 수 있어요! 😊"

        # 음식 관련
        elif any(word in message_lower for word in ["음식", "맛집", "요리", "먹방", "맛집", "먹는", "간식"]):
            if tone == "muneoz":
                return f"와! {name_part}먹방러구나! 싹싹김치~ 🍽️\n근데 나는 그거보다 배달 앱 쿠폰이 더 재밌어!\n\n스타벅스나 CGV 같은 라이프 브랜드 구독은 어때? 🤟💜"
            else:
                return f"{name_part}맛있는 음식 이야기네요! 🍽️\n음식과 관련해서라면 배달 앱이나 카페 구독은 어떠세요?\n\n스타벅스 등 다양한 라이프 브랜드 구독을 추천해드릴 수 있어요! ☕"

        # 게임 관련
        elif any(word in message_lower for word in ["게임", "롤", "배그", "게이밍"]):
            if tone == "muneoz":
                return f"헉! {name_part}게이머구나! 완전 멋져~ 🎮\n게임할 때 데이터 많이 쓰지? 그럼 무제한 요금제가 찰떡일 것 같은데!\n\n요금제 추천받아볼래? 🔥"
            else:
                return f"{name_part}게임을 즐기시는군요! 🎮\n게임을 위해서는 충분한 데이터가 필요하죠.\n\n지금 바로 요금제 추천을 해드릴 수 있어요! 📱"

        # 일반적인 재미있는 주제
        else:
            if tone == "muneoz":
                responses = [
                    f"오~ {name_part}완전 느좋한 주제네! 🤩\n근데 나는 그거보다 요금제가 더 재밌어! ㅋㅋㅋ\n\n럭키비키하게 통신 잼얘나 해볼까? 🐙✨",
                    f"헉 {name_part}그것도 멋진 주제인데! 😎\n하지만 내 추구미는 요금제 전문가거든~\n\n우리 이거 관련한 잼얘로 넘어가자! 🤟💜"
                ]
            else:
                responses = [
                    f"{name_part}정말 흥미로운 주제네요! 😊\n하지만 저는 그것보다 통신 요금제가 더 재미있다고 생각해요!\n\n요금제 상담으로 화제를 바꿔볼까요?",
                    f"{name_part}와! 멋진 이야기거네요! ✨\n다만 저의 전문 분야는 LG유플러스 서비스라서요~\n\n통신 관련 궁금한 점이 있으시면 언제든 말씀해주세요!"
                ]

            return random.choice(responses)

    async def _handle_boring_off_topic(self, message: str, tone: str, name_part: str = "") -> str:
        """일반적인 오프토픽 응답"""

        if tone == "muneoz":
            responses = [
                f"음... {name_part}그건 내가 잘 모르겠어! 😅\n나는 요금제랑 구독만 완전 잘 알고 있거든!\n\n뭔가 통신 관련 궁금한 거 없어? 🐙",
                f"아 {name_part}그런 건 내 전문분야가 아니야~ 🤔\n대신 요금제나 구독은 추천해줄 수 있어!\n\n우리 요금제 얘기 해보자! 🤟"
            ]
        else:
            responses = [
                f"{name_part}죄송해요, 그 분야는 제가 잘 알지 못해요. 😔\n저는 LG유플러스 요금제와 구독 서비스만 전문적으로 상담드리고 있어요.\n\n통신 관련 문의사항이 있으시면 도움드리겠습니다!",
                f"{name_part}그 주제는 저의 전문 영역이 아니에요. 🤷‍♀️\n대신 요금제나 구독 서비스에 대해서는 자신있게 도움드릴 수 있답니다!\n\n어떤 서비스가 궁금하신가요?"
            ]

        return random.choice(responses)

    async def _handle_unclear_question(self, message: str, tone: str, name_part: str = "") -> str:
        """질문을 이해하지 못했을 때 응답"""

        if tone == "muneoz":
            responses = [
                f"어? {name_part}뭔 말인지 잘 모르겠어! 😵‍💫\n\n혹시 이런 거 물어본 거야?\n• 요금제 추천\n• 구독 서비스 추천\n\n알잘딱깔센하게 다시 말해줘! 🤟",
                f"음... {name_part}내가 이해를 못한 것 같아! 🤯\n\n나는 이런 거 도와줄 수 있어:\n• 네 추구미에 맞는 요금제 찾기\n• 구독 서비스 큐레이팅\n\n칠가이하게 다시 물어봐~ 💜"
            ]
        else:
            responses = [
                f"{name_part}죄송해요, 질문을 정확히 이해하지 못했어요. 😔\n\n혹시 이런 내용을 문의하신 건가요?\n• 요금제 추천 상담\n• 구독 서비스 추천\n\n좀 더 구체적으로 말씀해주시겠어요?",
                f"{name_part}어떤 도움이 필요하신지 정확히 파악하지 못했네요. 🤔\n\n저는 다음과 같은 서비스를 제공합니다:\n• 맞춤형 요금제 추천\n• 구독 서비스 상담\n\n어떤 서비스를 원하시는지 다시 말씀해주세요!"
            ]

        return random.choice(responses)

    async def _handle_general_off_topic(self, message: str, tone: str, name_part: str = "") -> str:
        """일반적인 오프토픽 응답 (폴백)"""

        if tone == "muneoz":
            return f"""그건 {name_part}나도 잘 모르겠어! 😅

나는 요금제랑 구독 서비스만 완전 자신 있거든~

이런 거 도와줄 수 있어:
• 럭키비키한 요금제 찾기
• 감다살 구독 추천

나한테 뭔가 물어봐~ 🤟💜"""
        else:
            return f"""{name_part}죄송해요, 그 분야는 제가 도움드리기 어려워요. 😔

저는 다음과 같은 서비스를 전문적으로 제공합니다:
• 요금제 추천 및 상담
• 구독 서비스 추천

통신 관련해서 궁금한 점이 있으시면 언제든 말씀해주세요! 😊"""

    async def handle_tech_issue(self, message: str, tone: str = "general") -> str:
        """기술적 문제 응답"""
        if tone == "muneoz":
            return """헉! 뭔가 서버 쪽에서 문제가 생긴 것 같아! 😵‍💫

럭키비키하지 못한 상황이네... 잠깐 뒤에 다시 말걸어줘! ✨

나는 요금제랑 구독 추천은 완전 자신 있으니까
그런 거 필요하면 언제든 말해줘~ 🐙"""
        else:
            return """기술적인 문제가 발생하신 것 같네요. 😔

저는 요금제와 구독 서비스 상담을 도와드릴 수 있으니
그런 문의사항이 있으시면 언제든 말씀해주세요! 😊"""

    async def handle_greeting(self, message: str, tone: str = "general", session_id: str = None) -> str:
        """개인화된 인사 응답"""
        name_part = self._get_user_name(session_id)

        if tone == "muneoz":
            greetings = [
                f"안뇽! {name_part}🤟 나는 무너야~ 🐙\n\n완전 럭키비키하게 만났네! ✨\n요금제랑 구독 전문가라서 완전 자신 있어!\n\n네 추구미에 딱 맞는 거 찾아줄게~ 💜",
                f"야호! {name_part}🎉 무너 등장!\n\n나랑 요금제 얘기 하러 왔구나?\n알잘딱깔센하게 완전 찰떡인 거 추천해줄게! 🔥",
                f"안뇽안뇽! {name_part}🤟\n\n나는 LG유플러스 큐레이터 무너야!\n느좋한 요금제든 구독이든 뭐든지 말해봐~ 🐙💜\n\n싹싹김치! 🎊"
            ]
        else:
            greetings = [
                f"안녕하세요, {name_part}! 😊\n\n저는 LG유플러스 AI 상담사입니다.\n\n요금제 추천부터 구독 서비스까지 도와드릴 수 있어요!\n\n어떤 도움이 필요하신가요?",
                f"반갑습니다, {name_part}! ✨\n\nLG유플러스 요금제와 구독 서비스 전문 상담사입니다.\n\n고객님께 최적의 서비스를 추천해드리겠습니다.\n\n무엇을 도와드릴까요?",
                f"안녕하세요, {name_part}! 🌟\n\n저는 LG유플러스 상담 AI입니다.\n\n요금제 상담, 구독 서비스 추천 등\n다양한 서비스를 제공하고 있어요!\n\n어떤 것부터 시작해볼까요?"
            ]

        return random.choice(greetings)

    async def handle_unknown(self, message: str, tone: str = "general") -> str:
        """알 수 없는 요청 처리"""
        return await self._handle_unclear_question(message, tone)

    # ============= 기존 오류 상황 처리 함수들 =============
    async def handle_loading_failure(self, tone: str = "general") -> str:
        """로딩 실패 시 응답"""
        if tone == "muneoz":
            responses = [
                "앗! 뭔가 삐끗했나봐! 😵\n잠깐만 기다려줘~ 금방 다시 시도해볼게!🐙💜",
                "어? 로딩이 좀 이상해! 🤔\n럭키비키하게 다시 해보자!\n\n조금만 참아줘~ ✨"
            ]
        else:
            responses = [
                "죄송해요, 잠시 로딩에 문제가 발생했어요. 😔\n조금만 기다려주시면 다시 시도해보겠습니다!\n\n잠시만요~ ⏳",
                "아! 시스템에 일시적인 문제가 있는 것 같아요. 😅\n곧바로 다시 처리해드리겠습니다!\n\n조금만 기다려주세요! ⏰"
            ]

        return random.choice(responses)

    async def handle_api_error(self, tone: str = "general") -> str:
        """API 오류 시 응답"""
        if tone == "muneoz":
            responses = [
                "어머 뭔가 서버가 삐끗했나봐! 😱\n내가 아니라 시스템 문제야!\n\n잠깐만 기다렸다가 다시 물어봐줘~ 🐙",
                "아이고! 뭔가 기술적 문제가 생겼어! 🤖💥\n나는 멀쩡한데 시스템이 좀 그래!\n\n조금 뒤에 다시 시도해봐! 💜"
            ]
        else:
            responses = [
                "죄송합니다. 일시적인 시스템 오류가 발생했어요. 😔\n잠시 후 다시 시도해주시면 정상적으로 도움드릴 수 있습니다.\n\n불편을 드려 죄송해요! 🙏",
                "시스템에 기술적 문제가 발생한 것 같아요. 😅\n조금 기다렸다가 다시 문의해주시겠어요?\n\n빠르게 해결하도록 하겠습니다! ⚡"
            ]

        return random.choice(responses)

    async def handle_timeout_error(self, tone: str = "general") -> str:
        """타임아웃 오류 시 응답"""
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