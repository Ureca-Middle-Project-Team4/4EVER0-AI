from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from app.schemas.usage import CurrentUsageRequest
from app.db.user_usage_db import get_user_current_usage
from app.db.plan_db import get_all_plans
import json
import asyncio

router = APIRouter()

def _analyze_usage_pattern(usage) -> str:
    """사용 패턴 분석"""
    usage_pct = usage.usage_percentage

    if usage_pct >= 95:
        return "urgent_upgrade"
    elif usage_pct >= 85:
        return "upgrade"
    elif usage_pct >= 70:
        return "maintain"
    elif usage_pct <= 20:
        return "downgrade"
    elif usage_pct <= 40:
        return "cost_optimize"
    else:
        return "alternative"

def _filter_plans_by_usage(all_plans: list, usage, recommendation_type: str) -> list:
    """사용 패턴에 따른 요금제 필터링"""
    current_price = usage.current_plan_price

    def safe_price(plan):
        try:
            if isinstance(plan.price, str):
                price_str = plan.price.replace(',', '').replace('원', '').strip()
                return int(price_str)
            return int(plan.price)
        except (ValueError, TypeError):
            return 0

    if recommendation_type == "urgent_upgrade":
        return [p for p in all_plans if safe_price(p) > current_price][:3]
    elif recommendation_type == "upgrade":
        return [p for p in all_plans if current_price < safe_price(p) <= current_price + 20000][:2]
    elif recommendation_type == "maintain":
        return [p for p in all_plans if abs(safe_price(p) - current_price) <= 10000][:2]
    elif recommendation_type == "downgrade":
        return [p for p in all_plans if safe_price(p) < current_price][:3]
    elif recommendation_type == "cost_optimize":
        return [p for p in all_plans if safe_price(p) <= current_price][:3]
    else:  # alternative
        return [p for p in all_plans if abs(safe_price(p) - current_price) <= 15000][:3]

def _safe_price_value(price) -> int:
    """가격을 정수로 안전하게 변환"""
    try:
        if isinstance(price, str):
            price_str = price.replace(',', '').replace('원', '').strip()
            return int(price_str)
        return int(price)
    except (ValueError, TypeError):
        return 0

def _generate_simple_explanation(usage, recommendation_type: str, recommended_plans: list, tone: str) -> str:
    """간단한 설명 생성 - 더 자세하고 유용하게"""

    usage_pct = usage.usage_percentage
    current_plan = usage.current_plan_name
    data_gb = usage.remaining_data / 1000

    if tone == "muneoz":
        if recommendation_type == "urgent_upgrade":
            return f"""헉! 사용률이 {usage_pct:.1f}%나 돼서 완전 위험해! 🚨

현재 {current_plan} 쓰고 있는데 데이터가 {data_gb:.1f}GB밖에 안 남았어!
이대로 가면 속도 제한 걸릴 거야~ 😱

지금 당장 상위 요금제로 바꿔야 할 것 같아!
위에 추천한 요금제들 중에 하나 골라봐! 🔥

데이터 더 많이 주는 걸로 바꾸면 완전 럭키비키할 거야! ✨"""

        elif recommendation_type == "upgrade":
            return f"""사용률이 {usage_pct:.1f}%라서 좀 넉넉한 요금제가 좋을 것 같아! 💪

현재 {current_plan}인데 {data_gb:.1f}GB 남았네~
아직 괜찮긴 한데 여유가 별로 없어 보여!

위에 추천한 요금제들이 네 패턴에 완전 찰떡일 거야! ✨
데이터 걱정 없이 마음껏 쓸 수 있어~

어때? 업그레이드 해볼까? 🤟"""

        elif recommendation_type == "maintain":
            return f"""현재 {current_plan} 사용률이 {usage_pct:.1f}%로 딱 적당해! 😊

{data_gb:.1f}GB 남아있고 사용 패턴도 안정적이야!
굳이 바꿀 필요는 없지만 비슷한 가격대 요금제들도 있어~

위에 추천한 거 보고 혹시 더 마음에 드는 게 있나 확인해봐! 🤟
가성비나 혜택이 더 좋을 수도 있거든! 💜"""

        elif recommendation_type == "downgrade":
            return f"""사용률이 {usage_pct:.1f}%밖에 안 돼서 돈 아까워! 💸

{data_gb:.1f}GB나 남았는데 이건 완전 오버스펙이야!
더 저렴한 요금제로 바꿔서 헬시플레저하게 써봐~

위에 추천한 요금제들로 바꾸면 월 1만원 이상 아낄 수 있어!
그 돈으로 맛있는 거 먹거나 다른 구독 서비스 쓰는 게 어때? 싹싹김치! ✨"""

        else:  # alternative or cost_optimize
            return f"""사용률 {usage_pct:.1f}%보니까 이런 요금제들이 느좋할 것 같아! 🎯

현재 {current_plan}에서 {data_gb:.1f}GB 남았는데,
네 사용 패턴 분석해보니까 딱 적당한 수준이야!

위에 추천한 요금제들 중에서 골라봐:
• 비슷한 가격대지만 혜택이 더 좋은 거
• 아니면 조금 더 저렴하면서도 충분한 거

어떤 게 마음에 들어? 💜"""

    else:  # general tone
        if recommendation_type == "urgent_upgrade":
            return f"""⚠️ 긴급 업그레이드 권장

현재 사용률이 {usage_pct:.1f}%로 매우 높습니다!
{current_plan} 요금제에서 데이터가 {data_gb:.1f}GB만 남아있어 곧 속도 제한에 걸릴 수 있습니다.

📋 권장사항:
• 즉시 상위 요금제로 변경하여 데이터 부족 방지
• 데이터 용량이 더 큰 요금제 선택 권장
• 월말까지 안전하게 사용할 수 있는 여유 확보

위 추천 요금제들을 검토해보시고 빠른 변경을 고려해주세요."""

        elif recommendation_type == "upgrade":
            return f"""📈 업그레이드 권장

사용률 {usage_pct:.1f}%로 약간의 여유가 필요해 보입니다.
현재 {current_plan}에서 {data_gb:.1f}GB 남아있지만, 안정적인 사용을 위해 상위 요금제를 권장드립니다.

💡 업그레이드 시 장점:
• 데이터 걱정 없이 자유로운 인터넷 사용
• 속도 제한 위험 제거
• 여유로운 월말 사용 가능

위 추천 요금제들이 고객님의 사용 패턴에 적합할 것 같습니다."""

        elif recommendation_type == "maintain":
            return f"""✅ 현재 요금제 적정 수준

{current_plan} 요금제의 사용률이 {usage_pct:.1f}%로 적절합니다.
{data_gb:.1f}GB가 남아있어 월말까지 무리 없이 사용 가능합니다.

📊 현재 상태:
• 사용 패턴이 요금제와 잘 맞음
• 데이터 여유분 충분
• 비용 대비 효율적 사용

굳이 변경하지 않으셔도 되지만, 비슷한 가격대의 다른 옵션들도 참고해보세요."""

        elif recommendation_type == "downgrade":
            return f"""💰 비용 절약 기회

사용률이 {usage_pct:.1f}%로 낮아 비용 절약이 가능합니다!
현재 {data_gb:.1f}GB나 남아있어 현재 요금제가 과도할 수 있습니다.

💸 절약 효과:
• 월 통신비 1만원 이상 절약 가능
• 불필요한 데이터 용량 제거
• 절약한 비용으로 다른 서비스 이용 가능

위 추천 요금제들로 변경하시면 더 경제적으로 이용하실 수 있습니다."""

        else:  # alternative or cost_optimize
            return f"""🎯 맞춤 요금제 추천

사용률 {usage_pct:.1f}%를 종합 분석한 결과입니다.
현재 {current_plan}에서 {data_gb:.1f}GB 남은 상태로 적정 수준입니다.

📋 추천 근거:
• 현재 사용 패턴 분석 완료
• 데이터/통화/문자 사용량 고려
• 가성비 최적화 옵션 선별

위 요금제들은 고객님의 사용 습관과 예산에 맞춰 선별된 옵션들입니다.
각 요금제의 상세 혜택을 비교해보시고 선택하세요."""

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

            # 3. 🔥 추천 요금제 카드 데이터 전송
            recommendation_type = _analyze_usage_pattern(user_usage)
            all_plans = get_all_plans()
            recommended_plans = _filter_plans_by_usage(all_plans, user_usage, recommendation_type)

            if recommended_plans:
                plan_data = {
                    "type": "plan_recommendations",
                    "plans": [
                        {
                            "id": plan.id,
                            "name": plan.name,
                            "price": _safe_price_value(plan.price),
                            "data": plan.data,
                            "voice": plan.voice,
                            "speed": plan.speed,
                            "share_data": plan.share_data,
                            "sms": plan.sms,
                            "description": plan.description
                        }
                        for plan in recommended_plans
                    ]
                }
                print(f"[DEBUG] Sending plan recommendations: {len(recommended_plans)} plans")
                yield f"data: {json.dumps(plan_data, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.1)

            # 4. 스트리밍 시작 신호
            yield f"data: {json.dumps({'type': 'message_start'}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.05)

            # 5. 🔥 간단한 설명 스트리밍
            simple_explanation = _generate_simple_explanation(user_usage, recommendation_type, recommended_plans, tone)

            words = simple_explanation.split(' ')
            for i, word in enumerate(words):
                chunk_data = {
                    "type": "message_chunk",
                    "content": word + (" " if i < len(words) - 1 else "")
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