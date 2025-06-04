from app.schemas.ubti import UBTIRequest
from app.utils.redis_client import get_session, save_session, delete_session
from app.prompts.ubti_prompt import get_ubti_prompt
from app.db.ubti_types_db import get_all_ubti_types
from app.db.plan_db import get_all_plans
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.utils.langchain_client import get_chat_model

router = APIRouter()

# 검사용 질문 목록 (하나의 질문에 하나씩 답변해야함)
UBTI_QUESTIONS = [
    "하루 동안 스마트폰을 가장 많이 쓰는 시간대는 언제인가요?",
    "데이터는 주로 어떤 활동에 사용하시나요? (예: 영상, SNS, 웹서핑 등)",
    "통화를 자주 하시나요?",
    "통신비 예산은 어느 정도가 적절하다고 생각하시나요?"
]

@router.post("/ubti")
async def ubti_chat(req: UBTIRequest):
    session_id = f"ubti_session:{req.session_id}"
    session = get_session(session_id)

    if not session:
        session_data = {"step": 0, "answers": []}
        save_session(session_id, session_data)
        return {"question": UBTI_QUESTIONS[0], "step": 0}

    session["answers"].append(req.message)
    session["step"] += 1

    if session["step"] < len(UBTI_QUESTIONS):
        save_session(session_id, session)
        return {"question": UBTI_QUESTIONS[session["step"]], "step": session["step"]}
    else:
        answers = session["answers"]
        delete_session(session_id)

        # UBTI 유형 정보 불러오기
        ubti_types = get_all_ubti_types()
        ubti_text = "\n".join([
            f"{u.emoji} **{u.code} ({u.name})**  - {u.description}" for u in ubti_types
        ])

        # 요금제 정보도 활용 가능 (추후 추천 고도화)
        plans = get_all_plans()
        plans_text = "\n".join([
            f"- {p.name} (월 {p.price}) – {p.description or '설명 없음'}"
            for p in plans
        ])

        # 프롬프트 생성
        prompt = get_ubti_prompt().format(
            message="\n".join(answers),
            ubti_types=ubti_text,
            plans=plans_text
        )

        # 스트리밍 응답
        async def generate():
            model = get_chat_model()
            async for chunk in model.astream(prompt):
                yield chunk.content

        return StreamingResponse(generate(), media_type="text/plain")
