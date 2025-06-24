# chatbot-server/app/api/usage.py - 완전 개선 버전

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
    if not usage:
        return "unknown"

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
    if not all_plans:
        return []

    current_price = usage.current_plan_price if usage else 35000

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
    else:  # alternative or unknown
        # 기본 인기 요금제 반환
        return all_plans[:2] if len(all_plans) >= 2 else all_plans

def _safe_price_value(price) -> int:
    """가격을 정수로 안전하게 변환"""
    try:
        if isinstance(price, str):
            price_str = price.replace(',', '').replace('원', '').strip()
            return int(price_str)
        return int(price)
    except (ValueError, TypeError):
        return 0

def _analyze_user_type(usage_pct: float, data_gb: float, voice_min: int) -> str:
    """사용자 타입 분석"""
    if usage_pct >= 85:
        return "헤비 사용자"
    elif usage_pct >= 70:
        return "안정 추구형"
    elif usage_pct >= 40:
        return "균형잡힌 사용자" if data_gb > 2 else "스마트 선택형"
    elif usage_pct >= 20:
        return "절약형 사용자"
    else:
        return "라이트 사용자"

def _create_fallback_usage_data(user_id: int, tone: str) -> dict:
    """사용자 정보가 없을 때 기본 데이터 생성"""
    return {
        "user_id": user_id,
        "current_plan": "기본 요금제",
        "current_price": 35000,
        "remaining_data": 5000,  # 5GB
        "remaining_voice": 200,  # 200분
        "remaining_sms": 100,    # 100건
        "usage_percentage": 50.0  # 평균 사용률
    }

def _generate_fallback_explanation(user_id: int, recommended_plans: list, tone: str) -> str:
    """폴백 상황에 대한 설명 생성"""
    if tone == "muneoz":
        return f"""앗! {user_id}번 사용자 정보를 못 찾았어! 😅

하지만 걱정 마! 인기 요금제로 추천해줄게~

✅ **추천 이유:**
• 많은 사람들이 선택한 검증된 요금제들이야!
• 평균적인 사용 패턴에 딱 맞아!
• 가성비 완전 럭키비키! ✨

**🔥 1순위: {recommended_plans[0].name if recommended_plans else '너겟 30'} ({_safe_price_value(recommended_plans[0].price) if recommended_plans else 35000:,}원)**
• 데이터도 넉넉하고 가격도 적당해!

**🔥 2순위: {recommended_plans[1].name if len(recommended_plans) > 1 else '라이트 23'} ({_safe_price_value(recommended_plans[1].price) if len(recommended_plans) > 1 else 25000:,}원)**
• 가성비 완전 찰떡이야!

이 중에서 네 스타일에 맞는 거 골라봐~ 🐙💜"""
    else:
        return f"""죄송해요, {user_id}번 사용자의 정보를 찾을 수 없어요. 😔

대신 인기 요금제를 추천해드릴게요!

✅ **추천 근거:**
• 다수 고객이 선택한 검증된 요금제
• 일반적인 사용 패턴에 최적화
• 안정적인 가성비 제공

**💡 1순위: {recommended_plans[0].name if recommended_plans else '너겟 30'} ({_safe_price_value(recommended_plans[0].price) if recommended_plans else 35000:,}원)**
• 적절한 데이터 용량과 합리적 가격

**💡 2순위: {recommended_plans[1].name if len(recommended_plans) > 1 else '라이트 23'} ({_safe_price_value(recommended_plans[1].price) if len(recommended_plans) > 1 else 25000:,}원)**
• 경제적이면서 기본 기능 충실

위 요금제 중에서 선택하시면 만족하실 거예요! 😊"""

def _generate_simple_explanation(usage, recommendation_type: str, recommended_plans: list, tone: str) -> str:
    """사용자 친화적 설명 생성 - 사용자 타입 분석 + 구체적 이익/절약 금액"""

    if not usage or not recommended_plans:
        return _generate_fallback_explanation(usage.user_id if usage else 0, recommended_plans, tone)

    usage_pct = usage.usage_percentage
    current_plan = usage.current_plan_name
    data_gb = usage.remaining_data / 1000
    current_price = usage.current_plan_price

    # 사용자 타입 분석
    user_type = _analyze_user_type(usage_pct, data_gb, usage.remaining_voice)

    # 추천 요금제 최고 가격과 최저 가격
    plan_prices = [_safe_price_value(plan.price) for plan in recommended_plans]
    min_price = min(plan_prices) if plan_prices else current_price
    max_price = max(plan_prices) if plan_prices else current_price
    monthly_saving = current_price - min_price if current_price > min_price else 0
    additional_cost = max_price - current_price if max_price > current_price else 0

    if tone == "muneoz":
        if recommendation_type == "urgent_upgrade":
            return f"""헉! 너는 완전 **{user_type}** 타입이구나! 🔥

사용률이 {usage_pct:.1f}%나 돼서 완전 위험해! 🚨
{current_plan}에서 데이터가 {data_gb:.1f}GB밖에 안 남았어!

**🎯 너한테 딱 맞는 추천:**
• **{recommended_plans[0].name}** ({_safe_price_value(recommended_plans[0].price):,}원)
→ 월 {additional_cost:,}원 정도 더 내면 데이터 2배는 더 쓸 수 있어
→ 속도 제한 걸리면 스트레스 받잖아~ 미리미리 대비하자!

지금 바꾸면 완전 럭키비키할 거야! ✨"""

        elif recommendation_type == "upgrade":
            return f"""너는 **{user_type}** 사용자구나! 💪

사용률 {usage_pct:.1f}%로 아직 괜찮긴 한데, 여유가 별로 없어 보여!
{current_plan}에서 {data_gb:.1f}GB 남은 상태야~

**🎯 업그레이드 하면 이런 게 좋아:**
• **{recommended_plans[0].name}** ({_safe_price_value(recommended_plans[0].price):,}원)
→ 월 {additional_cost:,}원 정도 더 내면 데이터 걱정 제로!
→ 영상 스트리밍이나 게임할 때 끊김 없이 쭉쭉!

어때? 업그레이드 해볼까? 🤟"""

        elif recommendation_type == "maintain":
            return f"""오~ 너는 **{user_type}** 사용자네! 😊

{current_plan} 사용률 {usage_pct:.1f}%로 딱 적당해!
{data_gb:.1f}GB 남아있고 사용 패턴도 안정적이야!

**🎯 현재 상태 분석:**
• **{recommended_plans[0].name}** ({_safe_price_value(recommended_plans[0].price):,}원)
→ 요금제와 사용량이 완전 찰떡궁합!
→ 비슷한 가격대에서 혜택 더 좋은 것들도 있어

위에 추천한 거 중에 마음에 드는 게 있나 확인해봐! 💜"""

        elif recommendation_type == "downgrade":
            return f"""완전 **{user_type}**구나! 💸

사용률 {usage_pct:.1f}%밖에 안 돼서 돈 완전 아까워!
{data_gb:.1f}GB나 남았는데 이건 오버스펙이야!

**🎯 절약 효과 미쳤다:**
• **{recommended_plans[0].name}** ({_safe_price_value(recommended_plans[0].price):,}원)
→ 월 {monthly_saving:,}원 절약 가능! (연간 {monthly_saving*12:,}원!)
→ 그 돈으로 배달음식 2-3번은 더 시켜먹을 수 있어

이 기회에 확 바꿔서 싹싹김치하자! ✨"""

        else:  # alternative or cost_optimize
            return f"""너는 **{user_type}** 사용자야! 🎯

사용률 {usage_pct:.1f}%보니까 딱 적당한 수준!
{current_plan}에서 {data_gb:.1f}GB 남은 상태로 안정적이야~

**🎯 스마트한 선택지들:**
• **{recommended_plans[0].name}** ({_safe_price_value(recommended_plans[0].price):,}원)
→ 비슷한 가격대지만 혜택 더 좋은 거
→ 네 패턴이랑 알잘딱깔센하게 맞는 조합!

어떤 게 마음에 들어? 💜"""

    else:  # general tone
        if recommendation_type == "urgent_upgrade":
            return f"""**{user_type}**로 분석됩니다! 📊

현재 사용률이 {usage_pct:.1f}%로 매우 높아, 곧 데이터 부족을 겪으실 가능성이 높습니다.
{current_plan} 요금제에서 {data_gb:.1f}GB만 남은 상황입니다.

**💡 업그레이드 시 이점:**
• **{recommended_plans[0].name}** ({_safe_price_value(recommended_plans[0].price):,}원)
→ 월 {additional_cost:,}원 추가 시 데이터 용량 2배 이상 확보
→ 속도 제한 없이 안정적인 인터넷 사용 가능

상위 요금제로 변경하시면 더욱 쾌적한 모바일 환경을 경험하실 수 있습니다."""

        elif recommendation_type == "upgrade":
            return f"""**{user_type}** 사용자로 분석됩니다! 📈

사용률 {usage_pct:.1f}%로 적절하지만, 여유분이 부족해 보입니다.
현재 {current_plan}에서 {data_gb:.1f}GB 남아있습니다.

**💡 업그레이드 혜택:**
• **{recommended_plans[0].name}** ({_safe_price_value(recommended_plans[0].price):,}원)
→ 월 {additional_cost:,}원 추가로 데이터 걱정 해결
→ 영상통화, 스트리밍 등 자유로운 사용 가능

조금만 더 투자하시면 훨씬 여유로운 모바일 생활이 가능합니다."""

        elif recommendation_type == "maintain":
            return f"""**{user_type}**로 분석됩니다! ✅

{current_plan} 요금제 사용률이 {usage_pct:.1f}%로 적절한 수준입니다.
{data_gb:.1f}GB가 남아있어 월말까지 안정적으로 사용 가능합니다.

**📊 현재 상태:**
• **{recommended_plans[0].name}** ({_safe_price_value(recommended_plans[0].price):,}원)
→ 사용 패턴과 요금제가 잘 매칭됨
→ 비슷한 가격대에서 더 나은 혜택 선택 가능

현재 상태를 유지하시거나, 더 나은 혜택의 요금제로 변경을 고려해보세요."""

        elif recommendation_type == "downgrade":
            return f"""**{user_type}**로 분석됩니다! 💰

사용률 {usage_pct:.1f}%로 현재 요금제가 과도한 상태입니다.
{data_gb:.1f}GB나 남아있어 상당한 절약 기회가 있습니다.

**💸 절약 효과:**
• **{recommended_plans[0].name}** ({_safe_price_value(recommended_plans[0].price):,}원)
→ 월 {monthly_saving:,}원 절약 (연간 {monthly_saving*12:,}원!)
→ 절약한 비용으로 다른 구독 서비스 이용 가능

더 경제적인 요금제로 변경하시면 합리적인 통신비 절약이 가능합니다."""

        else:  # alternative or cost_optimize
            return f"""**{user_type}** 사용자로 분석됩니다! 🎯

사용률 {usage_pct:.1f}%로 현재 요금제와 적절히 매칭되고 있습니다.
{current_plan}에서 {data_gb:.1f}GB 남은 상태로 안정적입니다.

**💡 최적화 옵션:**
• **{recommended_plans[0].name}** ({_safe_price_value(recommended_plans[0].price):,}원)
→ 비슷한 가격대에서 더 나은 혜택 선택 가능
→ 사용 패턴에 최적화된 맞춤형 요금제 적용

고객님의 사용 습관에 가장 적합한 요금제를 선택하시면 됩니다."""

@router.post("/usage/recommend", summary="사용량 기반 추천", description="사용자의 실제 사용량 데이터를 분석하여 최적의 요금제를 추천합니다.")
async def usage_based_recommendation(
    user_id: int = Query(..., description="사용자 ID"),
    tone: str = Query("general", description="응답 톤 (general: 정중한 말투, muneoz: 친근한 말투)")
):
    """
    사용자 사용량 기반 요금제 추천 - 스트리밍 지원
    """
    async def generate_stream():
        try:
            print(f"[DEBUG] Usage recommendation request - user_id: {user_id}, tone: {tone}")

            # 1. 사용자 정보 존재 여부 확인
            user_usage = get_user_current_usage(user_id)

            # 2. 전체 요금제 목록 조회
            all_plans = get_all_plans()
            if not all_plans:
                error_data = {
                    "type": "error",
                    "message": "요금제 데이터를 불러올 수 없습니다." if tone == "general" else "앗! 요금제 데이터가 없어! 😅"
                }
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
                return

            # 3. 사용자 정보가 없을 때 폴백 처리
            if not user_usage:
                print(f"[WARNING] User {user_id} not found, providing fallback recommendation")

                # 기본 사용량 데이터로 폴백
                fallback_usage_data = _create_fallback_usage_data(user_id, tone)

                # 폴백 사용량 분석 결과 전송
                usage_summary = {
                    "type": "usage_analysis",
                    "data": fallback_usage_data
                }
                yield f"data: {json.dumps(usage_summary, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.1)

                # 기본 인기 요금제 추천 (상위 2개)
                recommended_plans = all_plans[:2] if len(all_plans) >= 2 else all_plans

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
                    yield f"data: {json.dumps(plan_data, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.1)

                # 스트리밍 시작 신호
                yield f"data: {json.dumps({'type': 'message_start'}, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.05)

                # 폴백 메시지 스트리밍
                fallback_message = _generate_fallback_explanation(user_id, recommended_plans, tone)
                words = fallback_message.split(' ')
                for i, word in enumerate(words):
                    chunk_data = {
                        "type": "message_chunk",
                        "content": word + (" " if i < len(words) - 1 else "")
                    }
                    yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.05)

                # 스트리밍 완료 신호
                yield f"data: {json.dumps({'type': 'message_end'}, ensure_ascii=False)}\n\n"
                return

            # 4. 정상 사용자 처리
            # 사용량 분석 결과 먼저 전송
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

            # 5. 추천 요금제 카드 데이터 전송
            recommendation_type = _analyze_usage_pattern(user_usage)
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

            # 6. 스트리밍 시작 신호
            yield f"data: {json.dumps({'type': 'message_start'}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.05)

            # 7. 맞춤 설명 스트리밍
            simple_explanation = _generate_simple_explanation(user_usage, recommendation_type, recommended_plans, tone)

            words = simple_explanation.split(' ')
            for i, word in enumerate(words):
                chunk_data = {
                    "type": "message_chunk",
                    "content": word + (" " if i < len(words) - 1 else "")
                }
                yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.05)

            # 8. 스트리밍 완료 신호
            yield f"data: {json.dumps({'type': 'message_end'}, ensure_ascii=False)}\n\n"

        except Exception as e:
            print(f"[ERROR] Usage recommendation failed: {e}")
            import traceback
            print(f"[ERROR] Traceback: {traceback.format_exc()}")

            error_data = {
                "type": "error",
                "message": f"추천 생성 실패: {str(e)}" if tone == "general" else f"앗! 뭔가 꼬였어! 😅 다시 시도해봐~"
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate_stream(), media_type="text/event-stream")

@router.get("/usage/{user_id}", summary="사용량 조회", description="특정 사용자의 현재 요금제 사용량 및 상태를 조회합니다.")
async def get_user_usage(user_id: int):
    """
    사용자 사용량 조회 - 실제 DB 연동
    """
    try:
        # 실제 DB에서 사용량 데이터 조회
        user_usage = get_user_current_usage(user_id)

        if not user_usage:
            # 폴백 데이터 제공
            fallback_data = _create_fallback_usage_data(user_id, "general")
            return {
                "success": True,
                "message": f"사용자 {user_id}의 정보를 찾을 수 없어 기본 정보로 대체합니다.",
                "data": {
                    "user_id": fallback_data["user_id"],
                    "current_plan": {
                        "name": fallback_data["current_plan"],
                        "price": fallback_data["current_price"]
                    },
                    "remaining": {
                        "data": f"{fallback_data['remaining_data']}MB",
                        "voice": f"{fallback_data['remaining_voice']}분",
                        "sms": f"{fallback_data['remaining_sms']}건"
                    },
                    "usage_percentage": fallback_data["usage_percentage"],
                    "status": _get_usage_status(fallback_data["usage_percentage"])
                }
            }

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
        # 에러 시에도 폴백 데이터 제공
        fallback_data = _create_fallback_usage_data(user_id, "general")
        return {
            "success": False,
            "message": f"사용량 조회 실패, 기본 데이터로 대체: {str(e)}",
            "data": {
                "user_id": fallback_data["user_id"],
                "current_plan": {
                    "name": fallback_data["current_plan"],
                    "price": fallback_data["current_price"]
                },
                "remaining": {
                    "data": f"{fallback_data['remaining_data']}MB",
                    "voice": f"{fallback_data['remaining_voice']}분",
                    "sms": f"{fallback_data['remaining_sms']}건"
                },
                "usage_percentage": fallback_data["usage_percentage"],
                "status": _get_usage_status(fallback_data["usage_percentage"])
            }
        }

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