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
import re

router = APIRouter()

UBTI_QUESTIONS = [
    "하루 동안 스마트폰을 가장 많이 쓰는 시간대는 언제인가요?",
    "데이터는 주로 어떤 활동에 사용하시나요? (예: 영상, SNS, 웹서핑 등)",
    "통화를 자주 하시나요?",
    "통신비 예산은 어느 정도가 적절하다고 생각하시나요?"
]

def extract_json_from_response(response_text: str) -> str:
    """AI 응답에서 JSON 부분만 추출"""
    # ```json으로 감싸진 경우 처리
    if "```json" in response_text:
        start = response_text.find("```json") + 7
        end = response_text.rfind("```")
        if end > start:
            return response_text[start:end].strip()

    # { }로 시작하는 JSON 찾기
    start = response_text.find('{')
    if start != -1:
        # 마지막 }까지 찾기
        bracket_count = 0
        for i, char in enumerate(response_text[start:], start):
            if char == '{':
                bracket_count += 1
            elif char == '}':
                bracket_count -= 1
                if bracket_count == 0:
                    return response_text[start:i+1]

    return response_text.strip()

@router.post("/ubti/question")
async def next_question(req: UBTIRequest):
    """UBTI 질문을 스트리밍으로 전송"""
    async def generate_question_stream():
        session_id = f"ubti_session:{req.session_id}"
        session = get_session(session_id)

        # 세션이 없으면 초기화
        if not session:
            session = {"step": 0, "answers": []}
            save_session(session_id, session)

            # 첫 번째 질문 스트리밍
            yield f"data: {json.dumps({'type': 'question_start'}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.05)

            question_data = {
                "type": "question_content",
                "question": UBTI_QUESTIONS[0],
                "step": 0,
                "total_steps": len(UBTI_QUESTIONS)
            }
            yield f"data: {json.dumps(question_data, ensure_ascii=False)}\n\n"

            yield f"data: {json.dumps({'type': 'question_end'}, ensure_ascii=False)}\n\n"
            return

        # 답변이 왔으면 저장하고 step 증가
        if req.message is not None:
            session["answers"].append(req.message)
            session["step"] += 1
            save_session(session_id, session)

        step = session["step"]

        # 모든 질문이 끝났으면 완료 신호
        if step >= len(UBTI_QUESTIONS):
            yield f"data: {json.dumps({'type': 'questions_complete'}, ensure_ascii=False)}\n\n"
            return

        # 다음 질문 스트리밍
        yield f"data: {json.dumps({'type': 'question_start'}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.05)

        question_data = {
            "type": "question_content",
            "question": UBTI_QUESTIONS[step],
            "step": step,
            "total_steps": len(UBTI_QUESTIONS)
        }
        yield f"data: {json.dumps(question_data, ensure_ascii=False)}\n\n"

        yield f"data: {json.dumps({'type': 'question_end'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate_question_stream(), media_type="text/event-stream")

@router.post("/ubti/result")
async def final_result(req: UBTIRequest):
    """UBTI 최종 결과를 JSON으로 반환 (스트리밍 X)"""
    session_id = f"ubti_session:{req.session_id}"
    session = get_session(session_id)

    if not session or session["step"] < len(UBTI_QUESTIONS):
        raise HTTPException(status_code=400, detail="아직 모든 질문이 마무리되지 않았습니다.")

    # 마지막 답변 추가
    session["answers"].append(req.message)
    delete_session(session_id)

    # 1. 데이터 로드
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

    # 2. AI 응답 수집
    model = get_chat_model()
    full_response = ""
    async for chunk in model.astream(prompt):
        full_response += chunk.content

    print(f"[DEBUG] UBTI Full response: '{full_response}'")

    # 3. JSON 추출 및 파싱
    try:
        json_text = extract_json_from_response(full_response)
        print(f"[DEBUG] Extracted JSON: '{json_text}'")

        parsed_result = json.loads(json_text)
        print(f"[DEBUG] Parsed result: {parsed_result}")

        # 4. UBTIResult 스키마에 맞게 데이터 구성
        result_data = UBTIResult(**parsed_result)

        return JSONResponse(
            status_code=200,
            content={
                "status": 200,
                "message": "요청 성공",
                "data": result_data.dict()
            }
        )

    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON 파싱 실패: {e}")
        print(f"[ERROR] 추출된 텍스트: '{json_text if 'json_text' in locals() else 'N/A'}'")
        raise HTTPException(status_code=500, detail="GPT 응답 파싱에 실패했습니다.")

    except Exception as e:
        print(f"[ERROR] 결과 처리 실패: {e}")
        raise HTTPException(status_code=500, detail="결과 처리 중 오류가 발생했습니다.")