from fastapi import APIRouter
from typing import List
from app.prompts.generate_reason_only_prompt import generate_reason_only_prompt
from app.schemas.recommend import UserProfile, MultiTurnRequest, RecommendedItem
from app.services.recommendation import get_recommendations
from app.utils.redis_client import get_session, save_session
from openai import OpenAI
from fastapi.responses import StreamingResponse
import os
import json

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
router = APIRouter()

@router.post("/recommend", response_model=List[RecommendedItem])
def recommend(user: UserProfile):
    return get_recommendations(user)

@router.post("/multi-recommend", response_model=List[RecommendedItem])
def multi_recommend(req: MultiTurnRequest):
    session_id = req.session_id
    session_state = get_session(session_id)

    # 누적 상태 업데이트
    if req.age_group:
        session_state["age_group"] = req.age_group
    if req.interests:
        session_state["interests"] = list(set(session_state.get("interests", []) + req.interests))
    if req.time_usage:
        session_state["time_usage"] = list(set(session_state.get("time_usage", []) + req.time_usage))

    save_session(session_id, session_state)

    user_profile = UserProfile(**session_state)
    return get_recommendations(user_profile)

@router.post("/multi-recommend/reason-stream")
async def stream_reason(req: MultiTurnRequest):
    session_id = req.session_id
    session_state = get_session(session_id)

    # 누적 정보 업데이트
    if req.age_group:
        session_state["age_group"] = req.age_group
    if req.interests:
        session_state["interests"] = list(set(session_state.get("interests", []) + req.interests))
    if req.time_usage:
        session_state["time_usage"] = list(set(session_state.get("time_usage", []) + req.time_usage))

    save_session(session_id, session_state)
    user_profile = UserProfile(**session_state)
    prompt = generate_reason_only_prompt(user_profile)

    async def gpt_stream():
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                stream=True
            )
            for chunk in response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    # SSE 형식으로 데이터 전송
                    yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"

            # 스트림 종료 신호
            yield "data: [DONE]\n\n"

        except Exception as e:
            error_msg = f"추천 이유를 생성하는 중 오류가 발생했습니다: {str(e)}"
            yield f"data: {json.dumps({'error': error_msg}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        gpt_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/plain; charset=utf-8"
        }
    )

# 대안: 더 간단한 스트리밍 방식
@router.post("/multi-recommend/reason-stream-simple")
async def stream_reason_simple(req: MultiTurnRequest):
    session_id = req.session_id
    session_state = get_session(session_id)

    # 누적 정보 업데이트
    if req.age_group:
        session_state["age_group"] = req.age_group
    if req.interests:
        session_state["interests"] = list(set(session_state.get("interests", []) + req.interests))
    if req.time_usage:
        session_state["time_usage"] = list(set(session_state.get("time_usage", []) + req.time_usage))

    save_session(session_id, session_state)
    user_profile = UserProfile(**session_state)
    prompt = generate_reason_only_prompt(user_profile)

    async def simple_stream():
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                stream=True
            )

            for chunk in response:
                if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            yield f"\n\n[오류] 추천 이유 생성 실패: {str(e)}"

    return StreamingResponse(
        simple_stream(),
        media_type="text/plain; charset=utf-8"
    )