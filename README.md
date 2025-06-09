📡 LG U+ 요금제 & 구독 추천 시스템 – AI 기반 라이프스타일 큐레이션

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

### 1. 📱 요금제 멀티턴 추천 (`POST /api/chat`, intent: `phone_plan_multi`)

* **4단계 질문 흐름**을 통해 사용자의 데이터, 통화, 서비스 선호, 예산 정보를 수집
* 수집된 정보를 기반으로 LangChain Prompt → GPT 모델로 최적 요금제 추천
* Redis를 통한 세션 기반 대화 유지

### 2. ☕ 구독 싱글턴 추천 (`POST /api/chat`, intent: `subscription_recommend`)

* **관심 분야 / 사용 스타일 / 예산**을 기반으로 단일 응답 생성
* 유저 입력 기반 의도 감지 → 메인 + 라이프 구독 조합 추천
* 예: 유튜브 프리미엄 + 스타벅스 커피쿠폰 (유독픽)

### 3. 💜 좋아요 기반 구독 추천 (`POST /api/chat/likes`)

* 사용자가 좋아요한 브랜드(예: 메가커피, CU 등)를 기반으로 구독 조합 추천
* **메인 구독 + 라이프 브랜드**의 조합을 자연어로 안내
* LG U+ 캐릭터 ‘무너’의 친근한 어투로 맞춤 추천 응답

### 4. 🍡 타코야키 성향 테스트 (UBTI) (POST /api/ubti/question, POST /api/ubti/result)
- 사용자는 4가지 자연어 질문에 자유롭게 답변 
- 답변 내용을 기반으로 UBTI 8가지 타입 중 하나를 AI가 분석하여 추천 
- 추천 결과는 JSON 형식으로 반환되어, 프론트엔드에서는 카드형 UI로 활용 가능


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

🧍 유저: 리디랑 올리브영 쿠폰 좋아요 눌렀어요
→ 좋아요 기반 → 관련 브랜드 연계 구독 조합 추천

🧍 유저: 혼자 집에서 영상 보는 걸 좋아해요
→ UBTI 분석 → TK-Eggy (집콕 마요타코) + 요금제 추천
```
