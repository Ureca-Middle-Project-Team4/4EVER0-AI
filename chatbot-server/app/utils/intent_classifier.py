# chatbot-server/app/utils/intent_classifier.py - 멀티턴 지원 강화

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

사용자 메시지와 대화 컨텍스트를 분석하여 정확한 인텐트를 분류해주세요.

🎯 **분류 가능한 인텐트:**
1. **greeting**: 인사, 처음 방문 (안녕, hi, hello, 하이, 헬로, 반가워 등)
2. **telecom_plan**: 요금제 관련 질문 및 추천 요청
3. **subscription**: 구독 서비스, OTT, 음악 관련 질문 및 추천 요청
4. **current_usage**: 현재 요금제 상태, 남은 데이터/통화량 확인
5. **ubti**: UBTI, 성향 분석 관련
6. **multiturn_answer**: 멀티턴 대화 중 질문에 대한 답변 (중요!)
7. **off_topic_interesting**: 재미있지만 통신과 무관한 주제
8. **off_topic_boring**: 일반적이고 통신과 무관한 주제
9. **off_topic_unclear**: 의도를 파악하기 어려운 애매한 질문
10. **nonsense**: 의미 없는 문자열, 랜덤 텍스트, 테스트 입력
11. **tech_issue**: 기술적 문제, 오류 상황

📋 **멀티턴 대화 감지 규칙 (매우 중요!):**
- 컨텍스트에 "flow_step"이 있으면 → **multiturn_answer**
- 질문형 메시지 뒤의 답변 → **multiturn_answer**
- 짧은 단답형 (10자 이하) → **multiturn_answer**
- 예: "5GB", "많이", "3만원", "드라마", "스포츠", "저렴하게" 등

📋 **가격 관련 특별 처리**:
- "5만원", "7만원", "십만원", "오만원" 등 → **telecom_plan**
- "3만원대", "5만원 이하", "7만원 정도" 등 → **telecom_plan**

📋 **예시:**
- "안녕", "하이" → **greeting**
- "요금제 추천해줘" → **telecom_plan**
- "5GB" (멀티턴 중) → **multiturn_answer**
- "많이 써요" (멀티턴 중) → **multiturn_answer**
- "영화 좋아해" (첫 메시지) → **off_topic_interesting**
- "영화 좋아해" (멀티턴 중) → **multiturn_answer**

사용자 메시지: "{message}"
대화 컨텍스트: {context}

🚨 **중요**: 응답은 반드시 위 인텐트 중 하나로만 답변하세요.
응답: 인텐트명만 출력 (예: greeting, multiturn_answer)
""")

    async def classify_intent(self, message: str, context: Dict[str, Any] = None) -> str:
        """AI 기반 정확한 인텐트 분류 - 멀티턴 우선 처리"""
        try:
            # 입력 검증
            if not message or len(message.strip()) == 0:
                return "off_topic_unclear"

            # 🔥 멀티턴 컨텍스트 우선 확인
            if context and self._is_multiturn_context(context):
                print(f"[DEBUG] Multiturn context detected: {list(context.keys())}")
                return "multiturn_answer"

            # 폴백 로직으로 확실한 케이스 체크
            fallback_intent = self._enhanced_fallback_classification(message, context)

            # 확실한 케이스는 AI 호출 없이 바로 반환
            if fallback_intent in ["greeting", "nonsense", "tech_issue", "multiturn_answer"]:
                print(f"[DEBUG] Fallback classified intent: {fallback_intent}")
                return fallback_intent

            # 가격 관련은 확실히 요금제로 분류
            if self._has_price_mention(message):
                # 🔥 단, 멀티턴 중이면 multiturn_answer
                if context and self._is_multiturn_context(context):
                    return "multiturn_answer"
                print(f"[DEBUG] Price mention detected, classifying as telecom_plan")
                return "telecom_plan"

            # AI 분류 시도 (애매한 케이스만)
            try:
                context_str = self._format_context(context) if context else "대화 시작"

                chain = self.intent_prompt | self.llm
                response = await asyncio.wait_for(
                    chain.ainvoke({"message": message, "context": context_str}),
                    timeout=8.0
                )
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
            return self._enhanced_fallback_classification(message, context)

    def _is_multiturn_context(self, context: Dict[str, Any]) -> bool:
        """멀티턴 대화 컨텍스트 감지"""
        if not context:
            return False

        # 멀티턴 플로우 키들 확인
        multiturn_keys = [
            "phone_plan_flow_step", "subscription_flow_step",
            "plan_step", "subscription_step", "ubti_step"
        ]

        for key in multiturn_keys:
            if key in context:
                value = context[key]
                # 안전한 타입 체크
                if isinstance(value, (int, float)) and value > 0:
                    return True
                elif isinstance(value, str) and value != '0' and value.strip():
                    try:
                        if int(value) > 0:
                            return True
                    except (ValueError, TypeError):
                        pass

        # user_info가 있으면 질문 받는 중
        if "user_info" in context:
            return True

        return False

    def _format_context(self, context: Dict[str, Any]) -> str:
        """컨텍스트를 문자열로 포맷팅"""
        if not context:
            return "대화 시작"

        info_parts = []

        # 멀티턴 상태 확인
        if self._is_multiturn_context(context):
            info_parts.append("멀티턴_대화_진행중")

        # 플로우 단계 정보
        for key in ["phone_plan_flow_step", "subscription_flow_step"]:
            if key in context and context[key] > 0:
                info_parts.append(f"{key}:{context[key]}")

        # 사용자 정보
        if "user_info" in context:
            user_info = context["user_info"]
            if isinstance(user_info, dict):
                for k, v in user_info.items():
                    if v:
                        info_parts.append(f"{k}:{v}")

        return ", ".join(info_parts) if info_parts else "대화 시작"

    def _has_price_mention(self, message: str) -> bool:
        """가격 언급 감지 - 강화된 한국어 처리"""
        text_lower = message.lower().strip()

        # 한국어 숫자 변환
        korean_numbers = {
            '일': '1', '이': '2', '삼': '3', '사': '4', '오': '5',
            '육': '6', '칠': '7', '팔': '8', '구': '9', '십': '10'
        }

        for kr, num in korean_numbers.items():
            text_lower = text_lower.replace(kr, num)

        # 가격 관련 패턴들
        price_patterns = [
            r'\d+만\s*원?',           # "5만원", "5만"
            r'\d{4,6}\s*원',          # "50000원"
            r'\d+천\s*원?',           # "3천원"
            r'\d+만원대',             # "3만원대"
            r'\d+만원?\s*(이하|미만|까지|정도|쯤)',  # "5만원 이하"
            r'\d+만원?\s*(이상|넘|초과)',          # "5만원 이상"
            r'\d+[\-~]\d+만원?',      # "3-5만원"
        ]

        for pattern in price_patterns:
            if re.search(pattern, text_lower):
                print(f"[DEBUG] Price pattern detected: {pattern} in '{message}'")
                return True

        # 예산 관련 키워드
        budget_keywords = ['예산', '돈', '가격', '비용', '통신비', '요금']
        if any(keyword in text_lower for keyword in budget_keywords):
            return True

        return False

    def _enhanced_fallback_classification(self, message: str, context: Dict[str, Any] = None) -> str:
        """강화된 키워드 기반 폴백 - 멀티턴 우선 처리"""
        lowered = message.lower().strip()
        original = message.strip()

        # 🔥 멀티턴 컨텍스트 우선 확인
        if context and self._is_multiturn_context(context):
            print(f"[DEBUG] Multiturn context in fallback classification")
            return "multiturn_answer"

        # 의미없는 입력 감지 (최우선)
        if self._is_nonsense_input(original, lowered):
            return "nonsense"

        # 인사 감지 (최우선)
        if self._is_greeting_input(lowered):
            return "greeting"

        # 입력이 너무 짧은 경우 → 멀티턴 답변일 가능성
        if len(lowered) <= 10 and self._is_likely_multiturn_answer(lowered):
            return "multiturn_answer"

        # 가격 언급 확인 (높은 우선순위)
        if self._has_price_mention(message):
            return "telecom_plan"

        # 기술 문제 관련
        tech_keywords = [
            "오류", "에러", "error", "문제", "안돼", "안되", "작동", "버그", "느려", "끊어져",
            "접속", "연결", "로딩", "loading", "timeout", "시간초과", "느림"
        ]
        if any(k in lowered for k in tech_keywords):
            return "tech_issue"

        # 요금제 관련 - 핵심 키워드만
        plan_keywords = [
            "요금제", "통신비", "데이터", "통화", "5g", "lte", "플랜", "너겟", "라이트",
            "프리미엄", "요금", "통신", "모바일", "핸드폰", "폰", "휴대폰"
        ]

        if any(k in lowered for k in plan_keywords):
            return "telecom_plan"

        # 구독 서비스 관련 - 핵심 키워드만
        subscription_keywords = [
            "구독", "ott", "넷플릭스", "유튜브", "음악", "지니", "스포티파이",
            "웨이브", "스타벅스", "브랜드"
        ]

        if any(k in lowered for k in subscription_keywords):
            return "subscription"

        # 현재 사용량 관련
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

        # 기본값: 애매한 케이스로 처리
        print(f"[DEBUG] No clear classification, defaulting to off_topic_unclear")
        return "off_topic_unclear"

    def _is_likely_multiturn_answer(self, lowered: str) -> bool:
        """멀티턴 대화에서의 답변일 가능성 확인"""
        # 10자 이하 짧은 답변들
        short_answers = [
            "드라마", "영화", "음악", "스포츠", "예능", "많이", "적게", "보통",
            "무제한", "저렴", "좋아해", "좋아", "싫어", "가끔", "자주",
            "예", "아니요", "네", "아니", "맞아", "글쎄", "모르겠어",
            "3만원", "5만원", "7만원", "10만원", "3gb", "5gb", "10gb",
            "출퇴근", "저녁", "주말", "밤", "아침", "점심", "낮", "새벽"
        ]

        # 키워드 완전 포함 체크
        for answer in short_answers:
            if answer in lowered:
                return True

        # 숫자+단위 패턴 (5자 이하)
        if len(lowered) <= 5:
            patterns = [
                r'\d+gb',      # "5gb"
                r'\d+만원?',   # "3만원"
                r'\d+시간?',   # "2시간"
                r'\d+분',      # "30분"
            ]
            for pattern in patterns:
                if re.search(pattern, lowered):
                    return True

        return False

    def _is_greeting_input(self, lowered: str) -> bool:
        """인사 입력 감지 - 정확도 향상"""
        # 정확한 인사말들
        exact_greetings = ["안녕", "hi", "hello", "헬로", "하이", "안뇽", "반가워", "반갑"]

        # 완전 일치 체크
        if lowered in exact_greetings:
            return True

        # 시작 패턴 체크 (3글자 이상일 때만)
        if len(lowered) >= 3:
            start_patterns = ["안녕", "hello", "헬로"]
            for pattern in start_patterns:
                if lowered.startswith(pattern):
                    return True

        return False

    def _is_nonsense_input(self, original: str, lowered: str) -> bool:
        """의미없는 입력 감지 - 더 정확하게"""

        # 1. 너무 짧거나 비어있는 경우
        if len(original.strip()) == 0:
            return True

        # 2. 단순 반복 문자 (웃음 표현 제외)
        if len(set(original)) <= 2 and len(original) > 3:
            if not any(laugh in original for laugh in ['ㅋ', 'ㅎ', 'ㅠ', 'ㅜ', '하', '호']):
                return True

        # 3. 테스트성 입력
        test_inputs = [
            "test", "테스트", "ㅁㄷㄱㄹ", "asdf", "qwer", "1234", "0000",
            "ㅁㄴㅇㄹ", "zxcv", "ㅋㅋㅋㅋㅋ", "ㅎㅎㅎㅎㅎ"
        ]

        if lowered in test_inputs:
            return True

        # 4. 랜덤 키보드 입력 (5자 이상)
        if len(original) >= 5:
            nonsense_patterns = [
                r'^[qwertyuiop\[\]\\asdfghjkl;\'zxcvbnm,\./]+$',  # 키보드 순서
                r'^[ㅁㄴㅇㄹㅎㅗㅓㅏㅣㅡㅜㅠㅋㅌㅊㅍㅎ]+$',  # 한글 자음/모음만
                r'^\d+$',  # 숫자만 (5자 이상)
            ]

            for pattern in nonsense_patterns:
                if re.match(pattern, lowered):
                    return True

        return False

    def _is_unclear_question(self, lowered: str) -> bool:
        """애매하고 불분명한 질문 감지"""

        # 너무 애매한 표현들 (단독 사용시만)
        unclear_words = ["뭐", "그거", "저거", "이거", "어떻게", "왜"]

        # 3글자 이하이고 애매한 단어만 있는 경우
        if len(lowered) <= 3 and any(word == lowered for word in unclear_words):
            return True

        # 질문표만 있는 경우
        if lowered in ["?", "??", "???", "ㅁ?", "어?"]:
            return True

        return False