# 📡 LG U+ 요금제 & 구독 추천 챗봇 (4EVER0-AI)

U+ 요금제/구독 서비스를 사용자 성향에 맞춰 자동 추천해주는 AI 기반 대화 시스템입니다.
GPT API + LangChain + FastAPI + Redis 조합으로 멀티턴 대화 처리 및 유저 맞춤형 응답을 제공합니다.


## 🧱 Tech Stack

| 항목        | 내용                         |
| --------- | -------------------------- |
| Language  | Python 3.9                 |
| Framework | FastAPI                    |
| AI Engine | OpenAI GPT (gpt-4o)        |
| Pipeline  | LangChain, Redis 기반 세션 관리  |
| ORM / DB  | SQLAlchemy (ORM), MySQL    |
| 환경 관리     | .env, python-dotenv        |
| 백엔드 연동    | Spring Boot (RestTemplate) |
| 구조화       | LangChain 체인 구성 및 프롬프트 설계  |
| 세션 저장     | Redis (TTL 1800초)          |


## 🔍 주요 기능

### 1. 📱 요금제 멀티턴 추천 (`/chat`, intent: `phone_plan_multi`)

* **4단계 질문 흐름**을 통해 사용자의 데이터, 통화, 서비스 선호, 예산 정보를 수집
* 수집된 정보를 기반으로 LangChain Prompt → GPT 모델로 최적 요금제 추천
* 모든 대화 이력과 사용자 응답은 Redis 세션으로 저장되어 유지

### 2. ☕ 구독 싱글턴 추천 (`/chat`, intent: `subscription_recommend`)

* \*\*3가지 키워드(관심 분야 / 사용 스타일 / 예산)\*\*를 기반으로 단일 응답 생성
* 매번 플로우 저장 없이 현재 발화로부터 의도 감지 및 단일 답변 생성
* LG U+의 **메인 + 라이프 구독 조합**으로 추천 (유독픽 구조)

### 3. 🍡 UBTI 타코야키 성향 테스트 (`/ubti`)

* 사용자 말투와 습관을 분석하여 **8가지 타코야키 유형** 중 하나 추천
* 감성적인 설명과 함께 요금제 또는 구독 서비스 제안


## 🚀 실행 방법

```bash
# 1. 프로젝트 클론
git clone https://github.com/Ureca-Middle-Project-Team4/4EVER0-AI
cd chatbot-server

# 2. 가상환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 패키지 설치
pip install -r requirements.txt

# 4. .env 설정
echo "OPENAI_API_KEY=sk-xxxxxxxxxxxx" > .env

# 5. 서버 실행
uvicorn app.main:app --reload
```

* 📄 [Swagger Docs](http://localhost:8000/docs)
* 📄 [ReDoc Docs](http://localhost:8000/redoc)

---

## 📁 폴더 구조

```
chatbot-server/
├── app/
│   ├── api/              # FastAPI 라우터
│   ├── chains/           # 요금제/구독/UBTI 체인
│   ├── db/               # 요금제/구독 상품 mock DB
│   ├── prompts/          # LangChain prompt 템플릿
│   ├── schemas/          # Request / Response 모델
│   ├── services/         # intent → chain 라우팅
│   ├── utils/            # Redis 세션, 유틸 함수
│   └── main.py           # FastAPI entrypoint
```

---

## 💬 사용 예시

```plaintext
🧍 유저: 데이터는 적게 쓰고 통화는 많이 해요
→ 요금제 멀티턴 흐름 시작 → 최적 요금제 추천

🧍 유저: 커피 좋아하는데 이와 관련된 구독 있어?
→ 구독 싱글턴 → 메인+라이프 구독 조합 추천

🧍 유저: 저 혼자 집에서 영상 보는 걸 좋아해요
→ UBTI 분석 → TK-Eggy (집콕 마요타코) + 요금제 추천
```


## 🧪 TODO

* [ ] Spring API 연동
* [ ] 음성 대화 지원 (STT → GPT → TTS)
* [ ] 사용자 프로파일 기반 자동 추천
* [ ] UBTI 카드 이미지 생성 + 프론트 연동
