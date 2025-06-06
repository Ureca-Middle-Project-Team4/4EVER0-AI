from app.db.database import SessionLocal
from app.db.models import UBType
from app.db.plan_db import get_all_plans
from app.prompts.ubti_prompt import get_ubti_prompt
from app.schemas.ubti import UBTIRequest
from app.utils.langchain_client import get_chat_model

async def handle_ubti_chat(req: UBTIRequest) -> str:
    try:
        db = SessionLocal()
        ubti_types = db.query(UBType).all()
        types_text = "\n".join([
            f"{ubti.emoji} {ubti.code} ({ubti.name}) - {ubti.description}"
            for ubti in ubti_types
        ])
        db.close()
    except Exception as e:
        print(f"UBTI 데이터 조회 오류: {e}")
        types_text = "..."

    try:
        plans = get_all_plans()
        plans_text = "\n".join([
            f"- {p.name} / {p.price}원 / {p.data or '-'} / {p.speed or '-'} / 공유:{p.share_data or '-'} / 통화:{p.voice or '-'} / 문자:{p.sms or '-'}"
            for p in plans
        ])
    except Exception as e:
        print(f"요금제 조회 오류: {e}")
        plans_text = "..."

    try:
        prompt = get_ubti_prompt().format(
            message=req.message,
            ubti_types=types_text,
            plans=plans_text
        )

        llm = get_chat_model()
        response = await llm.ainvoke(prompt)
        return response.content

    except Exception as e:
        print(f"UBTI 채팅 처리 오류: {e}")
        return f"오류: {str(e)}"
