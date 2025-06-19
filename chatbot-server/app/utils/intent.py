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
    """대화 가드 싱글톤 인스턴스 (기존 함수명 유지)"""
    global conversation_guard
    if conversation_guard is None:
        conversation_guard = ConversationGuard()
    return conversation_guard

async def detect_intent(message: str, user_context: dict = None) -> str:
    """강화된 인텐트 감지 - 이상한 입력 감지 포함"""
    classifier = get_intent_classifier()
    
    try:
        # 빈 메시지나 None 체크
        if not message or not message.strip():
            return "off_topic_unclear"
            
        intent = await classifier.classify_intent(message, user_context)
        print(f"[DEBUG] Final detected intent: {intent} for message: '{message[:50]}...'")
        return intent
        
    except Exception as e:
        print(f"[ERROR] Intent detection failed: {e}")
        # 폴백으로 간단한 키워드 체크
        return _emergency_intent_fallback(message)

def _emergency_intent_fallback(message: str) -> str:
    """긴급 폴백 - 시스템 오류 시 사용"""
    if not message or len(message.strip()) < 2:
        return "nonsense"
        
    lowered = message.lower().strip()
    
    # 확실한 케이스들만 체크
    if any(word in lowered for word in ["요금제", "플랜", "추천"]):
        return "telecom_plan"
    elif any(word in lowered for word in ["구독", "ott", "넷플릭스"]):
        return "subscription"
    elif any(word in lowered for word in ["안녕", "hello", "hi"]):
        return "greeting"
    elif len(set(message)) <= 2 and len(message) > 3:  # 반복 문자
        return "nonsense"
    else:
        return "off_topic_unclear"

async def handle_off_topic_response(message: str, tone: str = "general") -> str:
    """강화된 오프토픽 응답 처리 - nonsense 감지 포함"""
    guard = get_conversation_guard()
    
    try:
        return await guard.handle_off_topic(message, tone)
    except Exception as e:
        print(f"[ERROR] Off-topic handling failed: {e}")
        # 폴백 응답
        return _emergency_off_topic_response(tone)

def _emergency_off_topic_response(tone: str) -> str:
    """긴급 오프토픽 응답"""
    if tone == "muneoz":
        return """앗! 뭔가 문제가 생겼어! 😅
칠가이하게 다시 한 번 말해봐~
요금제나 구독 얘기 해보자! 💜"""
    else:
        return """죄송해요, 일시적인 문제가 발생했어요. 😔
요금제나 구독 서비스 관련해서 다시 문의해주세요!"""

async def handle_tech_issue_response(message: str, tone: str = "general") -> str:
    """기술 문제 응답 처리 (기존 함수명 유지)"""
    guard = get_conversation_guard()
    try:
        return await guard.handle_tech_issue(message, tone)
    except Exception as e:
        print(f"[ERROR] Tech issue handling failed: {e}")
        return _emergency_tech_response(tone)

def _emergency_tech_response(tone: str) -> str:
    """긴급 기술 문제 응답"""
    if tone == "muneoz":
        return "헉! 시스템에 문제가 있나봐! 😵‍💫\n잠깐 뒤에 다시 시도해봐~ 🐙"
    else:
        return "기술적 문제가 발생했어요. 😔\n잠시 후 다시 시도해주세요!"

async def handle_greeting_response(message: str, tone: str = "general") -> str:
    """인사 응답 처리 (기존 함수명 유지)"""
    guard = get_conversation_guard()
    try:
        return await guard.handle_greeting(message, tone)
    except Exception as e:
        print(f"[ERROR] Greeting handling failed: {e}")
        return _emergency_greeting_response(tone)

def _emergency_greeting_response(tone: str) -> str:
    """긴급 인사 응답"""
    if tone == "muneoz":
        return "안뇽! 🤟 나는 무너야!\n요금제 전문가라서 완전 자신 있어! 💜"
    else:
        return "안녕하세요! 😊 LG유플러스 상담사입니다.\n어떤 도움이 필요하신가요?"

async def handle_unknown_response(message: str, tone: str = "general") -> str:
    """알 수 없는 요청 응답 처리 (기존 함수명 유지)"""
    guard = get_conversation_guard()
    try:
        return await guard.handle_unknown(message, tone)
    except Exception as e:
        print(f"[ERROR] Unknown handling failed: {e}")
        return _emergency_unknown_response(tone)

def _emergency_unknown_response(tone: str) -> str:
    """알 수 없는 요청 응답"""
    if tone == "muneoz":
        return "어? 뭔 말인지 모르겠어! 😅\n요금제나 구독 얘기 해보자~ 💜"
    else:
        return "죄송해요, 이해하지 못했어요. 😔\n요금제 관련 질문을 해주세요!"

# ============= 새로 추가된 오류 처리 함수들 =============
async def handle_loading_error_response(tone: str = "general") -> str:
    """로딩 실패 응답 (새 함수)"""
    guard = get_conversation_guard()
    try:
        return await guard.handle_loading_failure(tone)
    except Exception as e:
        print(f"[ERROR] Loading error handling failed: {e}")
        return _emergency_loading_response(tone)

def _emergency_loading_response(tone: str) -> str:
    """긴급 로딩 오류 응답"""
    if tone == "muneoz":
        return "앗! 로딩이 좀 이상해! 😅\n잠깐만 기다려줘~ ✨"
    else:
        return "로딩 중 문제가 발생했어요. 😔\n잠시만 기다려주세요!"

async def handle_api_error_response(tone: str = "general") -> str:
    """API 오류 응답 (새 함수)"""
    guard = get_conversation_guard()
    try:
        return await guard.handle_api_error(tone)
    except Exception as e:
        print(f"[ERROR] API error handling failed: {e}")
        return _emergency_api_response(tone)

def _emergency_api_response(tone: str) -> str:
    """긴급 API 오류 응답"""
    if tone == "muneoz":
        return "어머! 서버가 삐끗했나봐! 😱\n잠깐 뒤에 다시 시도해봐~ 🐙"
    else:
        return "시스템 오류가 발생했어요. 😔\n잠시 후 다시 시도해주세요!"

async def handle_timeout_error_response(tone: str = "general") -> str:
    """타임아웃 오류 응답 (새 함수)"""
    guard = get_conversation_guard()
    try:
        return await guard.handle_timeout_error(tone)
    except Exception as e:
        print(f"[ERROR] Timeout error handling failed: {e}")
        return _emergency_timeout_response(tone)

def _emergency_timeout_response(tone: str) -> str:
    """긴급 타임아웃 오류 응답"""
    if tone == "muneoz":
        return "으악! 시간이 너무 오래 걸렸어! ⏰💥\n간단하게 다시 물어봐~ 💜"
    else:
        return "처리 시간이 초과되었어요. ⏰\n더 간단한 질문으로 다시 시도해주세요!"

# ============= 🔥 새로운 nonsense 전용 함수 =============
async def handle_nonsense_response(message: str, tone: str = "general") -> str:
    """의미없는 입력 전용 응답 처리 (새 함수)"""
    guard = get_conversation_guard()
    try:
        # ConversationGuard에 _handle_nonsense_input 메서드가 있는지 확인
        if hasattr(guard, '_handle_nonsense_input'):
            return await guard._handle_nonsense_input(message, tone)
        else:
            # 메서드가 없으면 직접 처리
            return _direct_nonsense_response(message, tone)
    except Exception as e:
        print(f"[ERROR] Nonsense handling failed: {e}")
        return _emergency_nonsense_response(tone)

def _direct_nonsense_response(message: str, tone: str) -> str:
    """직접 nonsense 응답 처리"""
    if tone == "muneoz":
        return """어? 뭔가 이상한 말이야! 😵‍💫
혹시 키보드가 삐끗했어?

제대로 된 질문으로 다시 말해봐~ 🤟
예: "3만원대 요금제 추천해줘!" 💜"""
    else:
        return """죄송해요, 입력하신 내용을 이해하지 못했어요. 😔

명확한 질문으로 다시 문의해주시겠어요?

예시:
• "월 3만원 이하 요금제 추천해주세요"
• "구독 서비스 추천 부탁드려요"
• "현재 데이터 사용량 확인해주세요" """

def _emergency_nonsense_response(tone: str) -> str:
    """긴급 nonsense 응답"""
    if tone == "muneoz":
        return "어? 뭔가 이상한 말이야! 😵‍💫\n제대로 된 질문 해봐~ 🤟💜"
    else:
        return "입력하신 내용을 이해하지 못했어요. 😔\n명확한 질문을 해주세요!"

# ============= 통합 응답 처리 함수 =============
async def handle_response_by_intent(intent: str, message: str, tone: str = "general") -> str:
    """인텐트에 따른 통합 응답 처리"""
    try:
        if intent == "nonsense":
            return await handle_nonsense_response(message, tone)
        elif intent == "greeting":
            return await handle_greeting_response(message, tone)
        elif intent == "tech_issue":
            return await handle_tech_issue_response(message, tone)
        elif intent.startswith("off_topic"):
            return await handle_off_topic_response(message, tone)
        else:
            return await handle_unknown_response(message, tone)
            
    except Exception as e:
        print(f"[ERROR] Response handling failed for intent {intent}: {e}")
        return _emergency_fallback_response(tone)

def _emergency_fallback_response(tone: str) -> str:
    """최종 긴급 폴백 응답"""
    if tone == "muneoz":
        return "앗! 뭔가 꼬였나봐! 😅\n다시 한 번 말해봐~ 💜"
    else:
        return "죄송해요, 문제가 발생했어요. 😔\n다시 시도해주세요!"

# ============= 입력 검증 함수 =============
def validate_user_input(message: str) -> dict:
    """사용자 입력 검증 및 분석"""
    result = {
        "is_valid": True,
        "is_nonsense": False,
        "is_empty": False,
        "length": len(message) if message else 0,
        "char_variety": 0,
        "has_korean": False,
        "has_english": False,
        "has_numbers": False,
        "has_special": False
    }
    
    if not message or not message.strip():
        result["is_valid"] = False
        result["is_empty"] = True
        return result
    
    cleaned = message.strip()
    result["length"] = len(cleaned)
    result["char_variety"] = len(set(cleaned))
    
    # 문자 종류 분석
    result["has_korean"] = any('\uac00' <= c <= '\ud7af' or '\u3131' <= c <= '\u318e' for c in cleaned)
    result["has_english"] = any(c.isalpha() and ord(c) < 128 for c in cleaned)
    result["has_numbers"] = any(c.isdigit() for c in cleaned)
    result["has_special"] = any(not c.isalnum() and not c.isspace() for c in cleaned)
    
    # nonsense 여부 판단
    if result["char_variety"] <= 2 and result["length"] > 3:
        result["is_nonsense"] = True
        result["is_valid"] = False
    
    return result