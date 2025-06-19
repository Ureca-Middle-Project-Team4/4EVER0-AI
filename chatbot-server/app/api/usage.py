from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from app.schemas.usage import CurrentUsageRequest
from app.chains.usage_chain import get_usage_based_recommendation_chain
from app.db.user_usage_db import get_user_current_usage
import json
import asyncio

router = APIRouter()

@router.post("/usage/recommend")
async def usage_based_recommendation(
    user_id: int = Query(..., description="사용자 ID"),
    tone: str = Query("general", description="응답 톤 (general/muneoz)")
):
    """
    사용자 사용량 기반 요금제 추천 - 스트리밍 지원
    """
    async def generate_stream():
        try:
            print(f"[DEBUG] Usage recommendation request - user_id: {user_id}, tone: {tone}")

            # 1. 사용자 정보 존재 여부 확인
            user_usage = get_user_current_usage(user_id)
            if not user_usage:
                error_data = {
                    "type": "error",
                    "message": "사용자 정보를 찾을 수 없습니다." if tone == "general" else "앗! 사용자 정보를 찾을 수 없어! 😅"
                }
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
                return

            # 2. 사용량 분석 결과 먼저 전송
            usage_summary = {
                "type": "usage_analysis",
                "data": {
                    "user_id": user_id,
                    "current_plan": user_usage.current_plan_name,
                    "current_price": user_usage.current_plan_price,
                    "remaining_data": user_usage.remaining_data,
                    "remaining_voice": user_usage.remaining_voice,
                    "remaining_sms": user_usage.remaining_sms,
                    "usage_percentage": round(user_usage.usage_percentage, 1)
                }
            }
            yield f"data: {json.dumps(usage_summary, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.1)

            # 3. 스트리밍 시작 신호
            yield f"data: {json.dumps({'type': 'message_start'}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.05)

            # 4. 사용량 기반 추천 체인 실행
            req = CurrentUsageRequest(user_id=user_id, tone=tone)
            stream_fn = await get_usage_based_recommendation_chain(req)

            # 5. AI 추천 스트리밍
            async for chunk in stream_fn():
                if chunk.strip():
                    chunk_data = {
                        "type": "message_chunk",
                        "content": chunk
                    }
                    yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.05)

            # 6. 스트리밍 완료 신호
            yield f"data: {json.dumps({'type': 'message_end'}, ensure_ascii=False)}\n\n"

        except Exception as e:
            print(f"[ERROR] Usage recommendation failed: {e}")
            error_data = {
                "type": "error",
                "message": f"추천 생성 실패: {str(e)}"
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate_stream(), media_type="text/event-stream")

@router.get("/usage/{user_id}")
async def get_user_usage(user_id: int):
    """
    사용자 사용량 조회 - 실제 DB 연동
    """
    try:
        # 실제 DB에서 사용량 데이터 조회
        user_usage = get_user_current_usage(user_id)

        if not user_usage:
            raise HTTPException(status_code=404, detail="사용자 정보를 찾을 수 없습니다.")

        # 응답 데이터 구성
        usage_data = {
            "user_id": user_usage.user_id,
            "current_plan": {
                "name": user_usage.current_plan_name,
                "price": user_usage.current_plan_price
            },
            "remaining": {
                "data": f"{user_usage.remaining_data}MB",
                "voice": f"{user_usage.remaining_voice}분",
                "sms": f"{user_usage.remaining_sms}건"
            },
            "usage_percentage": user_usage.usage_percentage,
            "status": _get_usage_status(user_usage.usage_percentage)
        }

        return {
            "success": True,
            "message": "사용량 조회 성공",
            "data": usage_data
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Usage data retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"사용량 조회 실패: {str(e)}")

def _get_usage_status(usage_percentage: float) -> dict:
    """사용률에 따른 상태 정보"""
    if usage_percentage >= 95:
        return {
            "level": "critical",
            "message": "사용량이 거의 소진되었습니다",
            "recommendation": "요금제 업그레이드를 권장합니다"
        }
    elif usage_percentage >= 80:
        return {
            "level": "warning",
            "message": "사용량이 많습니다",
            "recommendation": "사용량을 확인하시거나 상위 요금제를 고려해보세요"
        }
    elif usage_percentage >= 50:
        return {
            "level": "normal",
            "message": "적절한 사용량입니다",
            "recommendation": "현재 요금제가 적합합니다"
        }
    elif usage_percentage <= 20:
        return {
            "level": "low",
            "message": "사용량이 적습니다",
            "recommendation": "더 저렴한 요금제를 고려해보세요"
        }
    else:
        return {
            "level": "normal",
            "message": "안정적인 사용량입니다",
            "recommendation": "현재 요금제를 유지하시면 됩니다"
        }