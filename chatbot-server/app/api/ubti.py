from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Union
from app.schemas.ubti import UBTIRequest, UBTIQuestion, UBTIComplete, UBTIResult
from app.utils.redis_client import get_session, save_session, delete_session
from app.prompts.ubti_prompt import get_ubti_prompt
from app.db.ubti_types_db import get_all_ubti_types
from app.db.plan_db import get_all_plans
from app.utils.langchain_client import get_chat_model
import json
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

    if not session:
        session = {"step": 0, "answers": []}
        save_session(session_id, session)

    # 답변이 왔다면 저장하고 step 증가
    if req.message is not None:
        session["answers"].append(req.message)
        session["step"] += 1
        save_session(session_id, session)

    step = session["step"]

    # 질문 완료 시 완료 안내 반환 (200 OK)
    if step >= len(UBTI_QUESTIONS):
        return UBTIComplete()

    # 아직 질문이 남았다면 해당 질문 반환
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
    prompt = get_ubti_prompt().format(
        message="\n".join(session["answers"]),
        ubti_types="\n".join(f"{u.emoji} {u.code} - {u.name}" for u in ubti_types),
        plans="\n".join(p.name for p in plans)
    )

    # LLM 호출해서 스트리밍으로 받고 합침
    model = get_chat_model()
    full = ""
    async for chunk in model.astream(prompt):
        full += chunk.content

    return UBTIResult(message=full)
