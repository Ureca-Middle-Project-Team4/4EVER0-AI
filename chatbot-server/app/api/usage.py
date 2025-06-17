# app/api/usage.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.schemas.usage import CurrentUsageRequest
from app.chains.usage_chain import get_usage_based_recommendation_chain

router = APIRouter()

@router.post("/usage/recommend")
async def recommend_based_on_usage(req: CurrentUsageRequest):
    """현재 사용량 기반 요금제 추천"""
    try:
        stream_fn = await get_usage_based_recommendation_chain(req)
        return StreamingResponse(stream_fn(), media_type="text/plain")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"추천 생성 실패: {str(e)}")

@router.get("/usage/{user_id}")
async def get_current_usage(user_id: int):
    """사용자 현재 사용량 조회"""
    from app.db.user_usage_db import get_user_current_usage
    
    usage_info = get_user_current_usage(user_id)
    if not usage_info:
        raise HTTPException(status_code=404, detail="사용자 정보를 찾을 수 없습니다.")
    
    return {
        "status": 200,
        "message": "사용량 조회 성공",
        "data": usage_info.dict()
    }