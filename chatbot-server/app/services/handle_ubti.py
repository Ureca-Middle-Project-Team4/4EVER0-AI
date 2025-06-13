from app.db.database import SessionLocal
from app.db.models import UBType
from app.db.plan_db import get_all_plans
from app.prompts.ubti_prompt import get_ubti_prompt
from app.schemas.ubti import UBTIRequest
from app.utils.langchain_client import get_chat_model
from app.db.subscription_db import get_products_from_db
import json
import traceback
from typing import Optional

async def handle_ubti_chat(req: UBTIRequest) -> str:
    """
    UBTI 채팅 처리 - 강화된 에러 처리
    """
    try:
        print(f"[DEBUG] UBTI Request: session_id={req.session_id}, message={req.message}")

        # 1. 입력 검증
        if not req.session_id or not req.message:
            error_response = {
                "error": "UBTI_INVALID_REQUEST",
                "message": "session_id와 message는 필수입니다.",
                "details": f"session_id: {req.session_id}, message: {req.message}"
            }
            print(f"[ERROR] Invalid request: {error_response}")
            return json.dumps(error_response, ensure_ascii=False)

        # 2. UBTI 타입 데이터 조회
        ubti_types_text = await get_ubti_types()
        if not ubti_types_text:
            error_response = {
                "error": "UBTI_DATA_NOT_FOUND",
                "message": "UBTI 타입 데이터를 찾을 수 없습니다."
            }
            print(f"[ERROR] UBTI types not found")
            return json.dumps(error_response, ensure_ascii=False)

        # 3. 요금제 데이터 조회
        plans_text = await get_plans_data()
        if not plans_text:
            print(f"[WARNING] No plans data found, using fallback")
            plans_text = "요금제 데이터 없음"

        # 4. 구독 서비스 데이터 조회
        subscriptions_text = await get_subscriptions_data()
        if not subscriptions_text:
            print(f"[WARNING] No subscriptions data found, using fallback")
            subscriptions_text = "구독 서비스 데이터 없음"

        # tone 파라미터 추출
        tone = getattr(req, 'tone', 'general')

        # 5. 프롬프트 생성
        try:
            prompt = get_ubti_prompt(tone).format(
                message=req.message,
                ubti_types=ubti_types_text,
                plans=plans_text,
                subscriptions=subscriptions_text
            )
            print(f"[DEBUG] Prompt generated successfully, length: {len(prompt)}")
        except Exception as e:
            error_response = {
                "error": "UBTI_PROMPT_ERROR",
                "message": "프롬프트 생성 중 오류가 발생했습니다.",
                "details": str(e)
            }
            print(f"[ERROR] Prompt generation failed: {e}")
            return json.dumps(error_response, ensure_ascii=False)

        # 6. AI 모델 호출
        try:
            print(f"[DEBUG] Calling AI model...")
            llm = get_chat_model()
            response = await llm.ainvoke(prompt)
            print(f"[DEBUG] AI response received, length: {len(response.content)}")
            print(f"[DEBUG] AI response preview: {response.content[:200]}...")
        except Exception as e:
            error_response = {
                "error": "UBTI_AI_API_ERROR",
                "message": "AI 서비스 연결 오류가 발생했습니다.",
                "details": str(e)
            }
            print(f"[ERROR] AI API error: {e}")
            return json.dumps(error_response, ensure_ascii=False)

        # 7. JSON 응답 검증 및 파싱
        try:
            print(f"[DEBUG] Parsing JSON response...")
            parsed_response = json.loads(response.content)

            # 필수 필드 검증
            required_fields = ["ubti_type", "summary", "recommendation", "matching_type"]
            missing_fields = [field for field in required_fields if field not in parsed_response]
            if missing_fields:
                raise ValueError(f"필수 필드 누락: {missing_fields}")

            # plans 배열 검증
            if "recommendation" in parsed_response and "plans" in parsed_response["recommendation"]:
                plans_data = parsed_response["recommendation"]["plans"]
                if not isinstance(plans_data, list):
                    raise ValueError("plans는 배열이어야 합니다")
                if len(plans_data) != 2:
                    print(f"[WARNING] Expected 2 plans, got {len(plans_data)}")

                # 각 plan 객체 검증
                for i, plan in enumerate(plans_data):
                    if not isinstance(plan, dict) or "name" not in plan or "description" not in plan:
                        raise ValueError(f"plans[{i}]에 name과 description이 필요합니다")

            print(f"[DEBUG] JSON validation passed")
            return response.content

        except json.JSONDecodeError as je:
            error_response = {
                "error": "UBTI_JSON_PARSE_ERROR",
                "message": "AI 응답을 JSON으로 파싱할 수 없습니다.",
                "details": str(je),
                "raw_content": response.content[:500] if response else "No response"
            }
            print(f"[ERROR] JSON parsing failed: {je}")
            return json.dumps(error_response, ensure_ascii=False)

        except ValueError as ve:
            error_response = {
                "error": "UBTI_JSON_PARSE_ERROR",
                "message": "AI 응답 형식이 올바르지 않습니다.",
                "details": str(ve),
                "raw_content": response.content[:500] if response else "No response"
            }
            print(f"[ERROR] JSON validation failed: {ve}")
            return json.dumps(error_response, ensure_ascii=False)

    except Exception as e:
        # 최종 에러 처리
        error_response = {
            "error": "UBTI_GENERATION_FAILED",
            "message": "UBTI 결과 생성 중 예상치 못한 오류가 발생했습니다.",
            "details": str(e),
            "traceback": traceback.format_exc()
        }
        print(f"[ERROR] Unexpected error in handle_ubti_chat: {e}")
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        return json.dumps(error_response, ensure_ascii=False)


async def get_ubti_types() -> Optional[str]:
    """UBTI 타입 데이터 조회"""
    try:
        db = SessionLocal()
        ubti_types = db.query(UBType).all()
        db.close()

        if not ubti_types:
            print("[ERROR] No UBTI types found in database")
            return None

        types_text = "\\n\\n".join([
            f"{ubti.emoji} {ubti.code} ({ubti.name})\\n\\n{ubti.description}"
            for ubti in ubti_types
        ])

        print(f"[DEBUG] Found {len(ubti_types)} UBTI types")
        return types_text

    except Exception as e:
        print(f"[ERROR] Database error in get_ubti_types: {e}")
        return None


async def get_plans_data() -> Optional[str]:
    """요금제 데이터 조회"""
    try:
        plans = get_all_plans()
        if not plans:
            print("[WARNING] No plans found")
            return None

        plans_text = "\\n\\n".join([
            f"- {p.name} / {p.price}원 / {p.data or '-'} / {p.speed or '-'} / 공유:{p.share_data or '-'} / 통화:{p.voice or '-'} / 문자:{p.sms or '-'}"
            for p in plans
        ])

        print(f"[DEBUG] Found {len(plans)} plans")
        return plans_text

    except Exception as e:
        print(f"[ERROR] Error in get_plans_data: {e}")
        return None


async def get_subscriptions_data() -> Optional[str]:
    """구독 서비스 데이터 조회"""
    try:
        subscriptions = get_products_from_db()
        if not subscriptions:
            print("[WARNING] No subscriptions found")
            return None

        subscriptions_text = "\\n\\n".join([
            f"- {s.title} ({s.category}) - {s.price}원"
            for s in subscriptions
        ])

        print(f"[DEBUG] Found {len(subscriptions)} subscriptions")
        return subscriptions_text

    except Exception as e:
        print(f"[ERROR] Error in get_subscriptions_data: {e}")
        return None