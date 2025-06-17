# app/utils/conversation_guard.py
import os
import random
from langchain_openai import ChatOpenAI

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
        
        return random.choice(responses)
    
    async def handle_tech_issue(self, message: str, tone: str = "general") -> str:
        """기술적 문제 응답"""
        if tone == "muneoz":
            return """아이고 뭔가 문제가 있나봐? 😅

기술적인 문제는 내가 직접 해결하기 어려워서
LG유플러스 고객센터 1544-0010 으로 문의해보는 게 좋을 것 같아!

나는 요금제랑 구독 추천은 완전 자신 있으니까
그런 거 필요하면 언제든 말해줘~ 🐙"""
        else:
            return """기술적인 문제가 발생하신 것 같네요. 😔

이런 경우에는 LG유플러스 고객센터(1544-0010)에서 
전문적인 기술 지원을 받으시는 것이 가장 좋습니다.

저는 요금제와 구독 서비스 상담을 도와드릴 수 있으니
그런 문의사항이 있으시면 언제든 말씀해주세요! 😊"""
    
    async def handle_greeting(self, message: str, tone: str = "general") -> str:
        """인사 응답"""
        if tone == "muneoz":
            greetings = [
                "안뇽! 🤟 나는 무너야~ 🐙\n\n요금제랑 구독 전문가라서 완전 자신 있어!\n\n뭐든지 편하게 물어봐~ 💜",
                "야호! 🎉 무너 등장!\n\n요금제 추천이나 구독 서비스 얘기 하러 왔구나?\n\n내가 완전 찰떡인 거 추천해줄게! 🔥",
                "안뇽안뇽! 🤟\n\n나는 LG유플러스 큐레이터 무너야!\n\n요금제든 구독이든 뭐든지 말해봐~ 🐙💜"
            ]
        else:
            greetings = [
                "안녕하세요, 고객님! 😊\n\n저는 LG유플러스 AI 상담사입니다.\n\n요금제 추천부터 구독 서비스까지 도와드릴 수 있어요!\n\n어떤 도움이 필요하신가요?",
                "반갑습니다! ✨\n\nLG유플러스 요금제와 구독 서비스 전문 상담사입니다.\n\n고객님께 최적의 서비스를 추천해드리겠습니다.\n\n무엇을 도와드릴까요?",
                "안녕하세요! 🌟\n\n저는 LG유플러스 상담 AI입니다.\n\n요금제 상담, 구독 서비스 추천 등\n다양한 서비스를 제공하고 있어요!\n\n어떤 것부터 시작해볼까요?"
            ]
        
        return random.choice(greetings)
    
    async def handle_unknown(self, message: str, tone: str = "general") -> str:
        """알 수 없는 요청 처리"""
        if tone == "muneoz":
            return """음... 뭔 말인지 잘 모르겠어! 😅

혹시 요금제나 구독 서비스 관련 얘기였어?
그런 거면 내가 완전 전문가니까 다시 말해봐! 🤟

아니면 이런 것들 도와줄 수 있어:
• 요금제 추천
• 구독 서비스 추천
• 사용량 확인 안내
• UBTI 성향 분석 안내

뭐 해볼까? 💜"""
        else:
            return """죄송합니다. 요청을 정확히 이해하지 못했어요. 😔

저는 다음과 같은 서비스를 도와드릴 수 있습니다:
• 요금제 추천 상담
• 구독 서비스 추천
• 현재 사용량 기반 추천 안내
• UBTI 성향 분석 안내

어떤 서비스가 필요하신지 다시 말씀해주시겠어요?"""