from fastapi import APIRouter
from app.schemas.ubti import UBTIRequest
from app.utils.analyze_ubti import analyze_ubti
from app.utils.redis_client import get_session, save_session, delete_session
router = APIRouter()

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
        # 처음 요청이면 초기화
        session_data = {"step": 0, "answers": []}
        save_session(session_id, session_data)
        return {"question": UBTI_QUESTIONS[0], "step": 0}

    # 응답 저장
    session["answers"].append(req.message)
    session["step"] += 1

    if session["step"] < len(UBTI_QUESTIONS):
        save_session(session_id, session)
        return {
            "question": UBTI_QUESTIONS[session["step"]],
            "step": session["step"]
        }
    else:
        result = await analyze_ubti(session["answers"])
        delete_session(session_id)
        return {"result": result}
