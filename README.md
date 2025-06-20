# 📡 Enhanced Template-based LangChain System AI

**LG U+ 요금제/구독 서비스 추천 AI 대화 시스템**

OpenAI GPT-4o-mini + LangChain + FastAPI + Redis 기반으로 구축된 **강화된 AI 인텐트 감지**와 **Nonsense 입력 처리**를 탑재한 Template-based 대화 AI입니다.

4단계 멀티턴 플로우를 통해 사용자 성향을 파악하고, 개인 맞춤형 서비스를 자연스럽게 추천하며, 이상한 입력이나 오프토픽 질문에도 적절하게 대응합니다.

[MoonuZ](https://github.com/Ureca-Middle-Project-Team4) 프로젝트의 AI 대화 엔진으로 개발되었습니다.


## 초간단 실행 방법

### **Windows 사용자**
```cmd
git clone https://github.com/Ureca-Middle-Project-Team4/4EVER0-AI
cd 4EVER0-AI
setup.bat
run.bat
```

###  macOS/Linux 사용자
```cmd
git clone https://github.com/Ureca-Middle-Project-Team4/4EVER0-AI
cd 4EVER0-AI
chmod +x setup.sh run.sh
./setup.sh
./run.sh
```

### **⚙개발자 수동 설치**
```bash
# 1. 프로젝트 클론
git clone https://github.com/Ureca-Middle-Project-Team4/4EVER0-AI
cd chatbot-server

# 2. 가상환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 패키지 설치
pip install -r chatbot-server/requirements.txt
# Windows: pip install -r chatbot-server/requirements-windows.txt

# 4. .env 설정 
# chatbot-server/.env 생성 및 환경변수 설정

# 5. Redis 시작 (Linux/macOS만)
redis-server --daemonize yes

# 6. 서버 실행
cd chatbot-server
python run.py
# 또는
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 주요 기능

> **Template-based Conversational AI**로 RAG 대비 빠른 응답속도와 일관된 품질을 제공하면서도 **자연스러운 대화**를 구현합니다.

### **템플릿 기반 아키텍처 + AI 인텐트**
- **Smart Intent Detection**: GPT-4o-mini + 폴백 로직으로 99% 정확도
- **Nonsense Input Handling**: "ㅁㄴㅇㄹ", "asdf", "1234" 등 의미없는 입력 감지
- **Multiturn Answer Recognition**: 멀티턴 대화 중 답변을 정확히 인식
- **Greeting Priority**: 인사말을 최우선으로 처리하여 자연스러운 시작
- **Context-Aware Processing**: 대화 상황에 맞는 적응형 응답

### **멀티턴 대화 관리**
- **Unified Session Keys**: 일관된 세션 키로 안정성 향상
- **Flow State Preservation**: 대화 중단 시에도 정확한 상태 복원
- **Smart Flow Transition**: 플로우 완료 후 새로운 대화 자동 전환
- **Redis Session Migration**: 기존 세션과 새 세션 간 자동 마이그레이션
- **Error Recovery**: 오류 발생 시 graceful 복구 메커니즘

### **⚡ 스트리밍 응답 최적화**
- **Differentiated Latency**: 질문 0.05초, AI 응답 0.01초
- **Natural User Experience**: 실제 타이핑 패턴 모방
- **Async Processing**: FastAPI 기반 동시 다중 사용자 지원
- **Memory Efficient**: Redis TTL 30분으로 효율적 메모리 관리

### **페르소나 기반 응답**
- **Dual Character System**: 전문 상담원과 친근한 무너 중 선택
- **2025 Trendy Language**: 최신 유행어 반영한 자연스러운 대화
- **Tone Adaptation**: 사용자 선호에 따른 실시간 톤 변경
- **Emotional Intelligence**: 상황에 맞는 감정적 응답

### **강화된 대화 가드레일**
- **Off-topic Classification**: 재미있는/지루한/불분명한 오프토픽 세분화
- **Technical Issue Detection**: 기술적 문제 자동 감지 및 대응
- **Input Validation**: 사용자 입력의 유효성 실시간 검증
- **Graceful Degradation**: 시스템 오류 시에도 자연스러운 응답 유지

## 🛠️ Tech Stack

| 항목 | 내용 |
|------|------|
| **Language** | Python 3.9+ |
| **Framework** | FastAPI |
| **AI Engine** | OpenAI GPT-4o-mini |
| **AI Pipeline** | **LangChain Template-based Chain** |
| **Session Management** | Redis (TTL 1800초) |
| **ORM / DB** | SQLAlchemy (ORM), MySQL |
| **환경 관리** | .env, python-dotenv |
| **백엔드 연동** | Spring Boot (RestTemplate) |
| **Intent Classification** | GPT-4o-mini + Fallback Logic |
| **Conversation Guard** | Multi-layered Response System |

**📄 API 문서:**
- [Swagger Docs](http://localhost:8000/docs)
- [ReDoc Docs](http://localhost:8000/redoc)

## Conversational System Architecture
```mermaid
graph TD
    A[사용자 메시지] --> B{입력 검증}
    B -->|Valid| C[🧠 Enhanced Intent Classifier]
    B -->|Nonsense| H[🛡️ Nonsense Handler]
    
    C --> D[폴백 로직 1차 검증]
    D -->|확실한 케이스| E[즉시 분류]
    D -->|애매한 케이스| F[GPT-4o-mini AI 분류]
    
    E --> G{인텐트 라우팅}
    F --> G
    H --> G
    
    G -->|greeting| I[인사 응답]
    G -->|telecom_plan| J[요금제 멀티턴]
    G -->|subscription| K[구독 멀티턴]
    G -->|multiturn_answer| L[멀티턴 답변 처리]
    G -->|off_topic_*| M[오프토픽 가드레일]
    G -->|current_usage| N[🎯 사용량 기반 추천]
    G -->|likes_based_recommendation| O[💖 좋아요 기반 추천]
    G -->|ubti| P[UBTI API 안내]
    G -->|tech_issue| Q[기술 문제 처리]
    
    subgraph "🔄 Unified Multiturn Flow"
        J --> R[4단계 질문 플로우]
        K --> R
        L --> R
        R --> S[Redis 세션 통합 관리]
        S --> T[최종 추천 생성]
        T --> U[플로우 완료 & 초기화]
    end
    
    subgraph "🎯 Smart Usage Recommendation"
        N --> V[📊 사용량 패턴 분석]
        V --> W[👤 사용자 타입 분류]
        W --> X[💰 비용 효과 계산]
        X --> Y[📱 맞춤 요금제 필터링]
        Y --> Z[✨ 개인화된 설명 생성]
        Z --> AA[🔄 스트리밍 응답]
    end
    
    subgraph "💖 Likes-based Recommendation Engine"
        O --> AB[📈 좋아요 데이터 수집]
        AB --> AC[🎭 선호도 패턴 분석]
        AC --> AD[🏷️ 카테고리별 클러스터링]
        AD --> AE[🔍 유사도 기반 필터링]
        AE --> AF[📦 맞춤 구독 패키지]
        AF --> AG[💬 취향 맞춤 설명]
        AG --> AH[🔄 실시간 스트리밍]
    end
    
    subgraph "🛡️ Enhanced Guard System"
        M --> AI[재미있는 오프토픽]
        M --> AJ[지루한 오프토픽]
        M --> AK[불분명한 오프토픽]
        H --> AL[의미없는 입력 처리]
    end
    
    I --> AM[스트리밍 응답]
    AI --> AM
    AJ --> AM
    AK --> AM
    AL --> AM
    P --> AM
    Q --> AM
    U --> AM
    AA --> AM
    AH --> AM
```

### Enhanced Usage-based Recommendation Engine

> 사용량 기반 스마트 추천 시스템

사용자의 실제 데이터/음성/SMS 사용 패턴을 분석하여 **6가지 사용자 타입**으로 분류하고, 
**구체적인 절약/이득 금액**과 함께 맞춤형 요금제를 추천하는 시스템입니다.

### **AI 기반 사용자 타입 분석**

```mermaid
graph LR
    A[사용량 데이터] --> B[가중평균 계산]
    B --> C[패턴 분석]
    C --> D{사용자 타입}
    
    D --> E[🔥 헤비 사용자<br/>85%+]
    D --> F[💪 안정 추구형<br/>70-84%]
    D --> G[⚖️ 균형잡힌<br/>40-69% >2GB]
    D --> H[🎯 스마트 선택형<br/>40-69% ≤2GB]
    D --> I[💸 절약형<br/>20-39%]
    D --> J[🌱 라이트<br/><20%]
```

### **구체적 비용 효과 분석하여 제공**

| 추천 타입 | 비용 변화 | 실생활 비교 예시 |
|-----------|-----------|------------------|
| **urgent_upgrade** | 월 +15,000원 | "치킨 2번 값으로 데이터 걱정 제로!" |
| **upgrade** | 월 +8,000원 | "카페 아메리카노 8잔 값으로 여유 확보!" |
| **maintain** | 동일 가격 | "같은 가격에 더 많은 혜택!" |
| **downgrade** | 월 -12,000원 | "연간 144,000원 절약 = 넷플릭스 1년!" |
| **cost_optimize** | 월 -8,000원 | "절약한 돈으로 유튜브 프리미엄까지!" |

### **스마트 필터링 로직**

```mermaid
flowchart TD
    A[사용률 분석] --> B{95%+}
    A --> C{85-94%}
    A --> D{70-84%}
    A --> E{40-69%}
    A --> F{20-39%}
    A --> G{<20%}
    
    B --> H[urgent_upgrade<br/>상위 요금제 3개]
    C --> I[upgrade<br/>+2만원 이내 2개]
    D --> J[maintain<br/>±1만원 이내 2개]
    E --> K[alternative<br/>±1.5만원 이내 3개]
    F --> L[cost_optimize<br/>현재가 이하 3개]
    G --> M[downgrade<br/>하위 요금제 3개]
```

> 응답 예시 (무너톤 버전)

```
"오~ 너는 완전 **헤비 사용자** 타입이구나! 🔥

월 15,000원 더 내면 데이터 걱정 제로로 만들어줄게~
그 돈으로 치킨 2번 정도인데, 스트레스 없이 넷플릭스 
무제한으로 볼 수 있어! 완전 럭키비키잖아? ✨"
```


## Redis 세션 관리

### **통합된 세션 라이프사이클**

```mermaid
stateDiagram-v2
    [*] --> 입력_검증
    입력_검증 --> AI_인텐트_분류: Valid Input
    입력_검증 --> Nonsense_처리: Invalid Input
    
    AI_인텐트_분류 --> 폴백_로직_검증
    폴백_로직_검증 --> 즉시_분류: 확실한 케이스
    폴백_로직_검증 --> GPT_AI_분류: 애매한 케이스
    
    즉시_분류 --> 인텐트_라우팅
    GPT_AI_분류 --> 인텐트_라우팅
    Nonsense_처리 --> 인텐트_라우팅
    
    인텐트_라우팅 --> 멀티턴_시작: telecom_plan/subscription
    인텐트_라우팅 --> 직접_응답: 기타 인텐트
    
    멀티턴_시작 --> 세션_키_통일
    세션_키_통일 --> 1단계_질문
    1단계_질문 --> 2단계_질문: multiturn_answer
    2단계_질문 --> 3단계_질문: multiturn_answer
    3단계_질문 --> 4단계_질문: multiturn_answer
    4단계_질문 --> 최종_추천: multiturn_answer
    
    최종_추천 --> 세션_완전_초기화
    직접_응답 --> 세션_완전_초기화
    세션_완전_초기화 --> [*]
    
    note right of AI_인텐트_분류
        GPT-4o-mini + 폴백 로직
        99% 정확도 달성
    end note
    
    note right of 세션_키_통일
        phone_plan_flow_step
        subscription_flow_step
        user_info 통합 관리
    end note
    
    note right of 멀티턴_시작
        Redis TTL: 30분
        에러 복구 메커니즘
        자동 마이그레이션
    end note
```

### 성능 최적화 플로우
```mermaid
graph TD
A[사용자 메시지] --> B{입력 검증}
B -->|Valid| C[🧠 Enhanced Intent Classifier]
B -->|Nonsense| H[🛡️ Nonsense Handler]

    C --> D[폴백 로직 1차 검증]
    D -->|확실한 케이스| E[즉시 분류]
    D -->|애매한 케이스| F[GPT-4o-mini AI 분류]
    
    E --> G{인텐트 라우팅}
    F --> G
    H --> G
    
    G -->|greeting| I[인사 응답]
    G -->|telecom_plan| J[요금제 멀티턴]
    G -->|subscription| K[구독 멀티턴]
    G -->|multiturn_answer| L[멀티턴 답변 처리]
    G -->|off_topic_*| M[오프토픽 가드레일]
    G -->|current_usage| N[🎯 사용량 기반 추천]
    G -->|likes_based_recommendation| O[💖 좋아요 기반 추천]
    G -->|ubti| P[UBTI API 안내]
    G -->|tech_issue| Q[기술 문제 처리]
    
    subgraph "🔄 Unified Multiturn Flow"
        J --> R[4단계 질문 플로우]
        K --> R
        L --> R
        R --> S[Redis 세션 통합 관리]
        S --> T[최종 추천 생성]
        T --> U[플로우 완료 & 초기화]
    end
    
    subgraph "🎯 Smart Usage Recommendation"
        N --> V[📊 사용량 패턴 분석]
        V --> W[👤 사용자 타입 분류]
        W --> X[💰 비용 효과 계산]
        X --> Y[📱 맞춤 요금제 필터링]
        Y --> Z[✨ 개인화된 설명 생성]
        Z --> AA[🔄 스트리밍 응답]
    end
    
    subgraph "💖 Likes-based Recommendation Engine"
        O --> AB[📈 좋아요 데이터 수집]
        AB --> AC[🎭 선호도 패턴 분석]
        AC --> AD[🏷️ 카테고리별 클러스터링]
        AD --> AE[🔍 유사도 기반 필터링]
        AE --> AF[📦 맞춤 구독 패키지]
        AF --> AG[💬 취향 맞춤 설명]
        AG --> AH[🔄 실시간 스트리밍]
    end
    
    subgraph "🛡️ Enhanced Guard System"
        M --> AI[재미있는 오프토픽]
        M --> AJ[지루한 오프토픽]
        M --> AK[불분명한 오프토픽]
        H --> AL[의미없는 입력 처리]
    end
    
    I --> AM[스트리밍 응답]
    AI --> AM
    AJ --> AM
    AK --> AM
    AL --> AM
    P --> AM
    Q --> AM
    U --> AM
    AA --> AM
    AH --> AM
```


### **헬스체크 엔드포인트**
```bash
# 서버 상태 확인
curl http://localhost:8000/health

# AI 시스템 상태
curl http://localhost:8000/api/status

# 인텐트 분류 테스트
curl -X POST http://localhost:8000/debug/intent \
  -H "Content-Type: application/json" \
  -d '{"message": "요금제 추천해줘"}'
```

### **모니터링 대시보드**
- **Intent Classification Accuracy**: 실시간 인텐트 분류 정확도
- **Session Management**: 활성 세션 및 메모리 사용량
- **Response Time**: API 응답 시간 모니터링
- **Error Rate**: 오류 발생률 및 복구율
