from app.db.database import SessionLocal
from app.db.models import UBType
from app.prompts.ubti_prompt import get_ubti_prompt
from app.schemas.ubti import UBTIRequest  # ✅ 변경됨
from app.utils.langchain_client import get_chat_model


async def handle_ubti_chat(req: UBTIRequest) -> str:
    try:
        db = SessionLocal()
        ubti_types = db.query(UBType).all()
        types_text = "\n".join([
            f"- {ubti.code}: {ubti.name} - {ubti.description}"
            for ubti in ubti_types
        ])
    except Exception as e:
        print(f"UBTI 타입 조회 오류: {e}")
        types_text = "..."  # fallback
    finally:
        db.close()

    try:
        prompt = get_ubti_prompt().format(
            message=req.message,       # ✅ 하나만 사용
            ubti_types=types_text
        )

        llm = get_chat_model()
        response = await llm.ainvoke(prompt)
        return response.content

    except Exception as e:
        print(f"UBTI 채팅 처리 오류: {e}")
        return f"❌ 오류 발생: {str(e)}"
