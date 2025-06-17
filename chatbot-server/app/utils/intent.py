# app/utils/intent.py
import os
from app.utils.intent_classifier import EnhancedIntentClassifier
from app.utils.conversation_guard import ConversationGuard

# 전역 인스턴스 (싱글톤 패턴)
intent_classifier = None
conversation_guard = None

def get_intent_classifier():
    """인텐트 분류기 싱글톤 인스턴스"""
    global intent_classifier
    if intent_classifier is None:
        intent_classifier = EnhancedIntentClassifier()
    return intent_classifier

def get_conversation_guard():
    """대화 가드 싱글톤 인스턴스"""
    global conversation_guard
    if conversation_guard is None:
        conversation_guard = ConversationGuard()
    return conversation_guard

async def detect_intent(message: str, user_context: dict = None) -> str:
    """고도화된 인텐트 감지"""
    classifier = get_intent_classifier()
    return await classifier.classify_intent(message, user_context)

async def handle_off_topic_response(message: str, tone: str = "general") -> str:
    """오프토픽 응답 처리"""
    guard = get_conversation_guard()
    return await guard.handle_off_topic(message, tone)

async def handle_tech_issue_response(message: str, tone: str = "general") -> str:
    """기술 문제 응답 처리"""
    guard = get_conversation_guard()
    return await guard.handle_tech_issue(message, tone)

async def handle_greeting_response(message: str, tone: str = "general") -> str:
    """인사 응답 처리"""
    guard = get_conversation_guard()
    return await guard.handle_greeting(message, tone)

async def handle_unknown_response(message: str, tone: str = "general") -> str:
    """알 수 없는 요청 응답 처리"""
    guard = get_conversation_guard()
    return await guard.handle_unknown(message, tone)