from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Union
from app.schemas.ubti import UBTIRequest, UBTIQuestion, UBTIComplete, UBTIResult
from app.utils.redis_client import get_session, save_session, delete_session
from app.prompts.ubti_prompt import get_ubti_prompt
from app.db.ubti_types_db import get_all_ubti_types
from app.db.plan_db import get_all_plans
from app.db.subscription_db import get_products_from_db
from app.utils.langchain_client import get_chat_model
import json
from fastapi.responses import JSONResponse
import asyncio

router = APIRouter()

UBTI_QUESTIONS = [
    "하루 동안 스마트폰을 가장 많이 쓰는 시간대는 언제인가요?",
    "데이터는 주로 어떤 활동에 사용하시나요? (예: 영상, SNS, 웹서핑 등)",
    "통화를 자주 하시나요?",
    "통신비 예산은 어느 정도가 적절하다고 생각하시나요?"
]


@router.post(
    "/ubti/question",
    summary="다음 UBTI 질문 스트리밍 또는 완료 안내",
    response_model=Union[UBTIQuestion, UBTIComplete]
)
async def next_question(req: UBTIRequest):
    session_id = f"ubti_session:{req.session_id}"
    session = get_session(session_id)

    # 세션이 없으면 초기화하고 0번 질문 반환
    if not session:
        session = {"step": 0, "answers": []}
        save_session(session_id, session)
        return UBTIQuestion(question=UBTI_QUESTIONS[0], step=0)

    # 답변이 왔으면 저장하고 step 증가
    if req.message is not None:
        session["answers"].append(req.message)
        session["step"] += 1
        save_session(session_id, session)

    step = session["step"]
    if step >= len(UBTI_QUESTIONS):
        return UBTIComplete()

    return UBTIQuestion(question=UBTI_QUESTIONS[step], step=step)



@router.post(
    "/ubti/result",
    summary="모든 UBTI 답변을 합쳐 최종 결과 JSON으로 반환",
    response_model=UBTIResult
)
async def final_result(req: UBTIRequest):
    session_id = f"ubti_session:{req.session_id}"
    session = get_session(session_id)
    if not session or session["step"] < len(UBTI_QUESTIONS):
        raise HTTPException(status_code=400, detail="아직 모든 질문이 마무리되지 않았습니다.")

    # 마지막 답변 추가
    session["answers"].append(req.message)
    delete_session(session_id)

    # UBTI 유형 & 요금제 정보 로드
    ubti_types = get_all_ubti_types()
    plans = get_all_plans()
    subscriptions = get_products_from_db()

    subs_text = "\n".join([
        f"- {s.title}: {s.category}" for s in subscriptions
    ])

    prompt = get_ubti_prompt().format(
        message="\n".join(session["answers"]),
        ubti_types="\n".join(f"{u.emoji} {u.code} - {u.name}" for u in ubti_types),
        plans="\n".join(p.name for p in plans),
        subscriptions=subs_text
    )




    model = get_chat_model()
    full = ""
    async for chunk in model.astream(prompt):
        full += chunk.content

<<<<<<< HEAD
    try:
        parsed = json.loads(full)
        return UBTIResult(**parsed)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="GPT 응답 파싱에 실패했습니다.")

=======
<<<<<<< Updated upstream
    return UBTIResult(message=full)
=======
    try:
        parsed = json.loads(full)
        result = UBTIResult(**parsed)
        return JSONResponse(
            status_code=200,
            content={
                "status": 200,
                "message": "요청 성공",
                "data": result.dict()
            }
        )
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="GPT 응답 파싱에 실패했습니다.")

>>>>>>> Stashed changes
>>>>>>> 171cffe (Fix: [EVER-105] JSON 단일 객체 버그 수정)
