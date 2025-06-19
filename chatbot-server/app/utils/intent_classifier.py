import os
import re
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import asyncio

class EnhancedIntentClassifier:
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1,
            api_key=os.getenv("OPENAI_API_KEY")
        )

        self.intent_prompt = ChatPromptTemplate.from_template("""
당신은 LG유플러스 챗봇의 인텐트 분류 전문가입니다.

사용자 메시지를 분석하여 정확한 인텐트를 분류해주세요.

🎯 **분류 가능한 인텐트:**
1. **greeting**: 인사, 처음 방문 (안녕, hi, hello, 하이, 헬로 등)
2. **telecom_plan**: 요금제 관련 (바로 추천 가능)
3. **subscription**: 구독 서비스, OTT, 음악 관련 (바로 추천 가능)
4. **usage_based_recommendation**: 내 사용량 기반 추천, 현재 사용량 기반 요금제 추천
5. **likes_based_recommendation**: 좋아요 기반 추천, 내 취향 기반 구독 추천
6. **current_usage**: 현재 요금제 상태, 남은 데이터/통화량 확인
7. **ubti**: UBTI, 타코시그널, MBTI, 성향 분석 관련
8. **off_topic_interesting**: 재미있지만 통신과 무관한 주제 (영화, 음식, 여행 등)
9. **off_topic_boring**: 일반적이고 통신과 무관한 주제 (날씨, 시간, 기술 등)
10. **off_topic_unclear**: 의도를 파악하기 어려운 애매한 질문
11. **nonsense**: 의미 없는 문자열, 랜덤 텍스트, 테스트 입력
12. **tech_issue**: 기술적 문제, 오류 상황
13. **multiturn_answer**: 질문에 대한 답변 (스포츠, 영화, 무제한, 3만원 등)

📋 **🔥 중요한 구분 기준:**
- **greeting**: 인사말이 최우선 (안녕, hi, hello, 하이, 헬로, 반가워 등)
- **telecom_plan**: 요금제, 통신비, 데이터, 통화, 5G, LTE, 플랜 관련
- **subscription**: 구독, OTT, 넷플릭스, 유튜브, 음악, 지니 관련
- **usage_based_recommendation**: "내 사용량", "현재 사용량 기반", "사용 패턴 분석" 등
- **likes_based_recommendation**: "내 취향", "좋아요 기반", "내가 좋아하는", "선호도" 등
- **multiturn_answer**: 질문에 대한 간단한 답변

📋 **예시:**
- "안녕", "하이", "hello" → greeting (최우선)
- "요금제 추천해줘" → telecom_plan
- "구독 서비스 추천" → subscription
- "내 사용량 기반으로 추천해줘" → usage_based_recommendation
- "내 취향에 맞는 구독 추천해줘" → likes_based_recommendation
- "스포츠를 좋아해" → multiturn_answer

사용자 메시지: "{message}"

🚨 **중요**: 응답은 반드시 위 인텐트 중 하나로만 답변하세요.
응답: 인텐트명만 출력 (예: greeting, telecom_plan)
""")

    async def classify_intent(self, message: str, context: Dict[str, Any] = None) -> str:
        """AI 기반 정확한 인텐트 분류 - 인사 우선 처리"""
        try:
            # 입력 검증
            if not message or len(message.strip()) == 0:
                return "off_topic_unclear"

            # 먼저 폴백 로직으로 확실한 케이스 체크
            fallback_intent = self._enhanced_fallback_classification(message)

            # 확실한 케이스는 AI 호출 없이 바로 반환
            if fallback_intent in ["greeting", "nonsense", "tech_issue", "multiturn_answer"]:
                print(f"[DEBUG] Fallback classified intent: {fallback_intent}")
                return fallback_intent

            # AI 분류 시도 (애매한 케이스만)
            try:
                chain = self.intent_prompt | self.llm
                response = await asyncio.wait_for(chain.ainvoke({"message": message}), timeout=10.0)
                intent = response.content.strip().lower()

                # 유효한 인텐트인지 검증
                valid_intents = [
                    "greeting", "telecom_plan", "subscription", "current_usage", "ubti",
                    "tech_issue", "off_topic_interesting", "off_topic_boring",
                    "off_topic_unclear", "nonsense", "multiturn_answer"
                ]

                if intent in valid_intents:
                    print(f"[DEBUG] AI classified intent: {intent}")
                    return intent
                else:
                    print(f"[DEBUG] AI returned invalid intent: {intent}, using fallback")
                    return fallback_intent

            except asyncio.TimeoutError:
                print(f"[WARNING] AI classification timeout, using fallback")
                return fallback_intent
            except Exception as ai_error:
                print(f"[WARNING] AI classification error: {ai_error}, using fallback")
                return fallback_intent

        except Exception as e:
            print(f"[ERROR] Intent classification failed: {e}")
            return self._enhanced_fallback_classification(message)

    def _enhanced_fallback_classification(self, message: str) -> str:
        """강화된 키워드 기반 폴백 - 인사 최우선 처리"""
        lowered = message.lower().strip()
        original = message.strip()

        # 의미없는 입력 감지 (최우선)
        if self._is_nonsense_input(original, lowered):
            return "nonsense"

        # 인사 감지 (최최우선)
        greeting_words = ["안녕", "hi", "hello", "헬로", "하이", "반가", "처음", "시작"]
        greeting_patterns = [
            r"^(안녕|hi|hello|헬로|하이)",  # 시작 부분
            r"(안녕|hi|hello|헬로|하이)$",  # 끝 부분
            r"^(안녕|hi|hello|헬로|하이).*[!.]*$"  # 전체
        ]

        # 단어 정확 매칭
        if lowered in greeting_words:
            print(f"[DEBUG] Direct greeting match: {message}")
            return "greeting"

        # 패턴 매칭
        for pattern in greeting_patterns:
            if re.search(pattern, lowered):
                print(f"[DEBUG] Greeting pattern match: {message}")
                return "greeting"

        # 입력이 너무 짧은 경우
        if len(lowered) < 2:
            return "off_topic_unclear"

        # 멀티턴 답변 감지
        if self._is_multiturn_answer(lowered):
            print(f"[DEBUG] Detected multiturn answer: {message}")
            return "multiturn_answer"

        # 기술 문제 관련
        tech_keywords = [
            "오류", "에러", "error", "문제", "안돼", "안되", "작동", "버그", "느려", "끊어져",
            "접속", "연결", "로딩", "loading", "timeout", "시간초과", "느림", "엥"
        ]
        if any(k in lowered for k in tech_keywords):
            return "tech_issue"

        # 🔥 요금제 관련 강화된 감지
        plan_keywords = [
            "요금제", "통신비", "데이터", "통화", "5g", "lte", "플랜",
            "너겟", "라이트", "프리미엄", "추천", "요금", "통신", "모바일",
            "핸드폰", "폰", "휴대폰", "가입", "상품"
        ]

        plan_phrases = [
            "요금제 추천", "통신비 추천", "플랜 추천", "요금제 찾",
            "요금제 골라", "요금제 알아", "통신 요금", "휴대폰 요금"
        ]

        if any(phrase in lowered for phrase in plan_phrases):
            return "telecom_plan"

        if any(k in lowered for k in plan_keywords):
            return "telecom_plan"

        # 구독 서비스 관련
        subscription_keywords = [
            "구독", "ott", "넷플릭스", "유튜브", "음악", "지니", "스포티파이",
            "웨이브", "스타벅스", "브랜드"
        ]

        subscription_phrases = [
            "구독 추천", "구독 서비스", "ott 추천", "음악 서비스",
            "동영상 서비스", "스트리밍"
        ]

        if any(phrase in lowered for phrase in subscription_phrases):
            return "subscription"

        if any(k in lowered for k in subscription_keywords):
            return "subscription"

        # 🔥 사용량 기반 추천 관련
        usage_keywords = ["사용량", "사용 패턴", "내 사용량", "현재 사용량", "데이터 사용량", "통화 사용량"]
        usage_phrases = ["사용량 기반", "내 사용량으로", "현재 사용량 기반으로", "사용 패턴 분석"]

        if any(phrase in lowered for phrase in usage_phrases):
            return "usage_based_recommendation"
        if any(k in lowered for k in usage_keywords) and any(rec in lowered for rec in ["추천", "분석"]):
            return "usage_based_recommendation"

        # 🔥 좋아요/취향 기반 추천 관련
        likes_keywords = ["좋아요", "취향", "선호", "내가 좋아하는", "마음에 드는", "선호도"]
        likes_phrases = ["좋아요 기반", "내 취향", "취향에 맞는", "선호도 기반"]

        if any(phrase in lowered for phrase in likes_phrases):
            return "likes_based_recommendation"
        if any(k in lowered for k in likes_keywords) and any(rec in lowered for rec in ["추천", "서비스", "구독"]):
            return "likes_based_recommendation"

        # 현재 사용량 관련 (단순 조회)
        current_usage_keywords = ["남은", "현재", "잔여", "상태", "확인", "체크"]
        if any(k in lowered for k in current_usage_keywords):
            return "current_usage"

        # UBTI 관련
        ubti_keywords = ["ubti", "성향", "분석", "테스트", "mbti", "타코", "진단"]
        if any(k in lowered for k in ubti_keywords):
            return "ubti"

        # 재미있는 오프토픽
        interesting_keywords = [
            "영화", "드라마", "음식", "맛집", "여행", "연예인", "취미",
            "게임", "스포츠", "책", "카페", "쇼핑", "연애", "친구", "만화"
        ]
        if any(k in lowered for k in interesting_keywords):
            return "off_topic_interesting"

        # 일반 오프토픽
        boring_keywords = [
            "날씨", "시간", "프로그래밍", "코딩", "파이썬", "자바", "리액트",
            "공부", "학교", "대학교", "취업", "건강", "운동", "뉴스", "정치"
        ]
        if any(k in lowered for k in boring_keywords):
            return "off_topic_boring"

        # 애매한 질문 감지
        if self._is_unclear_question(lowered):
            return "off_topic_unclear"

        # 기본값: 인사로 처리 (통신 회사 챗봇이므로 친근하게)
        print(f"[DEBUG] No clear classification, defaulting to greeting")
        return "greeting"

    def _is_multiturn_answer(self, lowered: str) -> bool:
        """멀티턴 대화에서의 답변 감지"""

        # 멀티턴 질문에 대한 일반적인 답변들
        content_answers = ["드라마", "영화", "음악", "스포츠", "예능", "다큐", "애니메이션"]
        device_answers = ["스마트폰", "핸드폰", "tv", "태블릿", "컴퓨터", "노트북"]
        time_answers = ["출퇴근", "저녁", "주말", "점심", "새벽", "밤"]
        usage_answers = ["무제한", "많이", "적게", "보통", "거의안해", "자주"]
        budget_answers = ["3만원", "5만원", "저렴", "싸게", "가성비"]

        # 간단한 답변 패턴들
        simple_patterns = [
            r"^(좋아해|좋아|싫어|안좋아|그냥).*[!.]*$",
            r"^(많이|적게|보통|거의|전혀).*[!.]*$",
            r"^(무제한|제한없이).*[!.]*$",
            r"^\d+만원?.*[!.]*$",
            r"^(예|아니요|네|아니|맞아|틀려).*[!.]*$"
        ]

        # 패턴 매칭
        for pattern in simple_patterns:
            if re.match(pattern, lowered):
                return True

        # 키워드 매칭 (단어가 포함된 경우)
        all_answers = content_answers + device_answers + time_answers + usage_answers + budget_answers

        # 메시지가 짧고 (10자 이하) 답변 키워드를 포함하는 경우
        if len(lowered) <= 10:
            for answer in all_answers:
                if answer in lowered:
                    return True

        # "를 좋아해", "봐요", "해요" 등의 패턴
        if any(ending in lowered for ending in ["좋아해", "좋아요", "봐요", "해요", "써요", "들어요"]):
            return True

        return False

    def _is_nonsense_input(self, original: str, lowered: str) -> bool:
        """의미없는 입력 감지"""

        # 1. 너무 짧거나 비어있는 경우
        if len(original.strip()) == 0:
            return True

        # 2. 단순 반복 문자 (ㅋㅋㅋ, ㅎㅎㅎ 등은 제외)
        if len(set(original)) <= 2 and len(original) > 3:
            # 단, 일반적인 웃음 표현은 제외
            if not any(laugh in original for laugh in ['ㅋ', 'ㅎ', 'ㅠ', 'ㅜ']):
                return True

        # 3. 랜덤 키보드 입력
        nonsense_patterns = [
            r'^[qwertyuiop\[\]\\asdfghjkl;\'zxcvbnm,\./]+$',  # 키보드 순서
            r'^[ㅁㄴㅇㄹㅎㅗㅓㅏㅣㅡㅜㅠㅋㅌㅊㅍㅎ]+$',  # 한글 자음/모음만
            r'^\d+$',  # 숫자만
            r'^[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]+$',  # 특수문자만
        ]

        for pattern in nonsense_patterns:
            if re.match(pattern, lowered) and len(original) > 2:
                return True

        # 4. 테스트성 입력
        test_inputs = [
            "test", "테스트", "ㅁㄷㄱㄹ", "asdf", "qwer", "1234", "0000",
            "ㅁㄴㅇㄹ", "zxcv", "hello world", "안녕하세요테스트"
        ]

        if lowered in test_inputs:
            return True

        return False

    def _is_unclear_question(self, lowered: str) -> bool:
        """애매하고 불분명한 질문 감지"""

        # 너무 애매한 표현들
        unclear_patterns = [
            "뭐", "그거", "저거", "이거", "어떻게", "왜", "언제", "어디",
            "누가", "뭔가", "그런", "이런", "저런"
        ]

        # 단독으로 사용되거나 매우 짧은 경우만
        if len(lowered) <= 3 and any(pattern in lowered for pattern in unclear_patterns):
            return True

        # 질문표만 있는 경우
        if lowered in ["?", "??", "???", "ㅁ?", "어?"]:
            return True

        return False