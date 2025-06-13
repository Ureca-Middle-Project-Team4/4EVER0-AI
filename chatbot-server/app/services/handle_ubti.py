from app.db.database import SessionLocal
from app.db.models import UBType
from app.db.plan_db import get_all_plans
from app.prompts.ubti_prompt import get_ubti_prompt
from app.schemas.ubti import UBTIRequest
from app.utils.langchain_client import get_chat_model
from app.db.subscription_db import get_products_from_db
import json

async def handle_ubti_chat(req: UBTIRequest) -> str:
    try:
        # UBTI 타입 조회
        db = SessionLocal()
        ubti_types = db.query(UBType).all()
        types_text = "\\n\\n".join([
            f"{ubti.emoji} {ubti.code} ({ubti.name})\\n\\n{ubti.description}"
            for ubti in ubti_types
        ])
        db.close()
    except Exception as e:
        print(f"UBTI 데이터 조회 오류: {e}")
        types_text = "데이터 조회 중 오류 발생"

    try:
        # 요금제 조회
        plans = get_all_plans()
        plans_text = "\\n\\n".join([
            f"- {p.name} / {p.price}원 / {p.data or '-'} / {p.speed or '-'} / 공유:{p.share_data or '-'} / 통화:{p.voice or '-'} / 문자:{p.sms or '-'}"
            for p in plans
        ])
    except Exception as e:
        print(f"요금제 조회 오류: {e}")
        plans_text = "데이터 조회 중 오류 발생"

    try:
        # 구독 서비스 조회
        subscriptions = get_products_from_db()
        subscriptions_text = "\\n\\n".join([
            f"- {s.title} ({s.category}) - {s.price}원"
            for s in subscriptions
        ])
    except Exception as e:
        print(f"구독 서비스 조회 오류: {e}")
        subscriptions_text = "데이터 조회 중 오류 발생"

    try:
        prompt = get_ubti_prompt().format(
            message=req.message,
            ubti_types=types_text,
            plans=plans_text,
            subscriptions=subscriptions_text
        )

        llm = get_chat_model()
        response = await llm.ainvoke(prompt)

        # JSON 응답 검증
        try:
            parsed_response = json.loads(response.content)
            # plans가 리스트인지 확인
            if "recommendation" in parsed_response and "plans" in parsed_response["recommendation"]:
                if not isinstance(parsed_response["recommendation"]["plans"], list):
                    raise ValueError("plans는 배열이어야 합니다")
                if len(parsed_response["recommendation"]["plans"]) != 2:
                    raise ValueError("정확히 2개의 요금제가 필요합니다")
        except json.JSONDecodeError:
            print(f"JSON 파싱 오류: {response.content}")
            return "JSON 응답 생성 중 오류가 발생했습니다."
        except ValueError as ve:
            print(f"응답 형식 오류: {ve}")
            return f"응답 형식 오류: {ve}"

        return response.content

    except Exception as e:
        print(f"UBTI 채팅 처리 오류: {e}")
        return f"처리 중 오류가 발생했습니다: {str(e)}"