from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from app.schemas.usage import CurrentUsageRequest
from app.db.user_usage_db import get_user_current_usage
from app.db.plan_db import get_all_plans
from app.db.database import SessionLocal
from app.db.models import Plan
import json
import asyncio
import random
from typing import Optional

router = APIRouter()

def get_plan_by_id(plan_id: int) -> Optional[dict]:
    """plan_id로 실제 DB에서 요금제 정보 조회"""
    db = SessionLocal()
    try:
        plan = db.query(Plan).filter(Plan.id == plan_id).first()
        if not plan:
            return None

        return {
            "id": plan.id,
            "name": plan.name,
            "price": int(plan.price) if isinstance(plan.price, str) else plan.price,
            "data": plan.data,
            "voice": plan.voice,
            "sms": plan.sms
        }
    finally:
        db.close()

def parse_plan_limits(plan_data: dict) -> dict:
    """요금제 데이터에서 실제 한도 추출"""

    # 데이터 한도 파싱
    data_str = plan_data.get("data", "").lower()
    if "무제한" in data_str:
        total_data = 999999
    elif "gb" in data_str:
        try:
            gb_amount = float(data_str.replace("gb", "").strip())
            total_data = int(gb_amount * 1000)  # MB로 변환
        except:
            total_data = 5000  # 기본값 5GB
    else:
        total_data = 5000

    # 음성 한도 파싱
    voice_str = plan_data.get("voice", "").lower()
    if "무제한" in voice_str:
        total_voice = 999999
    else:
        # 일반적으로 300분 제공
        total_voice = 300

    # SMS는 보통 무제한
    total_sms = 999999

    return {
        "total_data": total_data,
        "total_voice": total_voice,
        "total_sms": total_sms
    }

def generate_usage_for_plan(plan_id: int) -> dict:
    """특정 plan_id에 대한 랜덤 사용량 데이터 생성"""

    # plan_id로 실제 요금제 정보 조회
    plan_data = get_plan_by_id(plan_id)
    if not plan_data:
        return None

    # 요금제 한도 파싱
    limits = parse_plan_limits(plan_data)

    # plan_id를 시드로 사용해서 일관된 랜덤 데이터 생성
    random.seed(plan_id)

    # 다양한 사용 패턴 (plan_id % 4로 패턴 결정)
    usage_pattern = plan_id % 4

    if usage_pattern == 0:  # 헤비 사용자 (80-95%)
        data_usage_rate = random.uniform(0.80, 0.95)
        voice_usage_rate = random.uniform(0.70, 0.90)
        user_type_hint = "헤비"
    elif usage_pattern == 1:  # 균형 사용자 (50-75%)
        data_usage_rate = random.uniform(0.50, 0.75)
        voice_usage_rate = random.uniform(0.40, 0.70)
        user_type_hint = "균형"
    elif usage_pattern == 2:  # 절약형 사용자 (20-45%)
        data_usage_rate = random.uniform(0.20, 0.45)
        voice_usage_rate = random.uniform(0.15, 0.40)
        user_type_hint = "절약"
    else:  # 라이트 사용자 (5-30%)
        data_usage_rate = random.uniform(0.05, 0.30)
        voice_usage_rate = random.uniform(0.05, 0.25)
        user_type_hint = "라이트"

    # 사용량 계산
    if limits["total_data"] == 999999:  # 무제한 데이터
        used_data = random.randint(15000, 50000)  # 15-50GB 사용한 것으로 가정
        remaining_data = 999999
        usage_percentage = random.uniform(30, 70)  # 무제한이므로 가상의 사용률
    else:
        used_data = int(limits["total_data"] * data_usage_rate)
        remaining_data = max(0, limits["total_data"] - used_data)
        usage_percentage = data_usage_rate * 100

    if limits["total_voice"] == 999999:  # 무제한 음성
        used_voice = random.randint(100, 600)
        remaining_voice = 999999
    else:
        used_voice = int(limits["total_voice"] * voice_usage_rate)
        remaining_voice = max(0, limits["total_voice"] - used_voice)

    # SMS는 보통 적게 사용
    used_sms = random.randint(10, 80)
    remaining_sms = 999999

    return {
        "user_id": f"plan_{plan_id}",  # 가상의 user_id
        "current_plan_name": plan_data["name"],
        "current_plan_price": plan_data["price"],
        "remaining_data": remaining_data,
        "remaining_voice": remaining_voice,
        "remaining_sms": remaining_sms,
        "usage_percentage": round(usage_percentage, 1),
        "used_data": used_data,
        "used_voice": used_voice,
        "used_sms": used_sms,
        "total_data": limits["total_data"],
        "total_voice": limits["total_voice"],
        "total_sms": limits["total_sms"],
        "user_type_hint": user_type_hint,
        "has_plan": True
    }

def _analyze_usage_pattern(usage_data: dict) -> str:
    """사용 패턴 분석"""
    usage_pct = usage_data["usage_percentage"]

    if usage_pct >= 90:
        return "urgent_upgrade"
    elif usage_pct >= 75:
        return "upgrade"
    elif usage_pct >= 50:
        return "maintain"
    elif usage_pct <= 25:
        return "downgrade"
    elif usage_pct <= 45:
        return "cost_optimize"
    else:
        return "alternative"

def _filter_plans_by_usage(all_plans: list, usage_data: dict, recommendation_type: str) -> list:
    """사용 패턴에 따른 요금제 필터링"""
    if not all_plans:
        return []

    current_price = usage_data["current_plan_price"]

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
    else:
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
    if usage_pct >= 80:
        return "헤비 사용자"
    elif usage_pct >= 60:
        return "안정 추구형"
    elif usage_pct >= 35:
        return "균형잡힌 사용자" if data_gb > 2 else "스마트 선택형"
    elif usage_pct >= 20:
        return "절약형 사용자"
    else:
        return "라이트 사용자"

def _generate_no_plan_message(tone: str) -> str:
    """요금제 없을 때 안내 메시지"""
    if tone == "muneoz":
        return """어? 너의 사용량 데이터를 못 찾겠어! 😅

아직 요금제를 가입하지 않았거나,
데이터가 준비되지 않은 것 같아!

이런 걸 해봐:
📱 **요금제를 먼저 가입해보고**
📊 **며칠 사용한 후에** 다시 와줘!

지금은 일반 채팅으로 "요금제 추천해줘"라고 하면
네 상황에 맞는 추천을 받을 수 있어~ 🐙💜"""
    else:
        return """사용량 데이터 정보가 아직 부족해요..😔

다음과 같은 경우일 수 있어요:
• 아직 요금제를 가입하지 않으신 경우
• 가입 후 3-4일 이상 충분한 사용 데이터가 쌓이지 않은 경우

권장사항:
📱 **요금제 가입 후 며칠 사용해보시기**
💬 **일반 채팅으로 "요금제 추천해주세요"**라고
   말씀해주시면 기본 상담을 받으실 수 있어요!

사용량이 쌓인 후 다시 이용해주시면
더 정확한 맞춤 추천을 받으실 수 있습니다. 😊"""

def _generate_usage_explanation(usage_data: dict, recommendation_type: str, recommended_plans: list, tone: str) -> str:
    """사용량 기반 맞춤 설명 생성"""

    usage_pct = usage_data["usage_percentage"]
    current_plan = usage_data["current_plan_name"]
    current_price = usage_data["current_plan_price"]

    # 데이터 표시 방식 개선
    if usage_data["remaining_data"] == 999999:
        data_display = "무제한"
        data_gb = "무제한"
    else:
        data_gb = f"{usage_data['remaining_data'] / 1000:.1f}GB"
        data_display = data_gb

    # 음성 표시 방식 개선
    if usage_data["remaining_voice"] == 999999:
        voice_display = "무제한"
    else:
        voice_display = f"{usage_data['remaining_voice']}분"

    # 추천 요금제 최고 가격과 최저 가격
    plan_prices = [_safe_price_value(plan.price) for plan in recommended_plans] if recommended_plans else [current_price]
    min_price = min(plan_prices)
    max_price = max(plan_prices)
    monthly_saving = current_price - min_price if current_price > min_price else 0
    additional_cost = max_price - current_price if max_price > current_price else 0

    # 사용자 타입 분석
    user_type = _analyze_user_type(usage_pct, float(data_gb.replace('GB', '')) if 'GB' in str(data_gb) else 0, usage_data["remaining_voice"] if usage_data["remaining_voice"] != 999999 else 300)

    if tone == "muneoz":
        if recommendation_type == "urgent_upgrade":
            return f"""헉! 너는 완전 **{user_type}** 타입이구나! 🔥

사용률이 {usage_pct:.1f}%나 돼서 거의 다 썼어! 🚨
{current_plan}에서 데이터 {data_display}, 음성 {voice_display}밖에 안 남았네!

**🎯 급하게 업그레이드 필요:**
• **{recommended_plans[0].name}** ({_safe_price_value(recommended_plans[0].price):,}원)
→ 월 {additional_cost:,}원 더 내면 데이터 걱정 뚝!
→ 속도 제한 걸리기 전에 미리미리 바꾸자!

지금 바꾸면 완전 럭키비키할 거야! ✨""" if recommended_plans else f"""헉! 너는 완전 **{user_type}** 타입이구나! 🔥

사용률이 {usage_pct:.1f}%나 돼서 거의 다 썼어!
더 큰 요금제로 급하게 바꾸는 걸 추천해! 🚨"""

        elif recommendation_type == "maintain":
            return f"""오~ 너는 **{user_type}** 사용자네! 😊

{current_plan} 사용률 {usage_pct:.1f}%로 딱 적당해!
데이터 {data_display}, 음성 {voice_display} 남아있고 균형 잡혔어!

**🎯 현재 상태가 완전 좋아:**
• **{recommended_plans[0].name}** ({_safe_price_value(recommended_plans[0].price):,}원)
→ 지금 요금제가 네 패턴이랑 찰떡궁합!
→ 혹시 더 좋은 혜택 있는 것도 확인해봐

현재 패턴 유지하면 완전 굿! 💜""" if recommended_plans else f"""오~ 너는 **{user_type}** 사용자네! 😊

{current_plan} 사용률 {usage_pct:.1f}%로 딱 적당해!
현재 요금제가 네 패턴이랑 완전 찰떡이야! 💜"""

        elif recommendation_type == "downgrade":
            return f"""완전 **{user_type}**구나! 💸

사용률 {usage_pct:.1f}%밖에 안 돼서 돈 아까워!
데이터 {data_display}나 남았는데 완전 오버스펙이야!

**🎯 절약 각:**
• **{recommended_plans[0].name}** ({_safe_price_value(recommended_plans[0].price):,}원)
→ 월 {monthly_saving:,}원 절약! (연간 {monthly_saving*12:,}원!)
→ 그 돈으로 맛있는 거 사먹자!

확 바꿔서 싹싹김치하자! ✨""" if recommended_plans else f"""완전 **{user_type}**구나! 💸

사용률 {usage_pct:.1f}%밖에 안 돼서 돈 아까워!
더 저렴한 요금제로 바꾸면 절약할 수 있어! ✨"""

        else:  # upgrade, alternative, cost_optimize
            return f"""너는 **{user_type}** 사용자야! 🎯

사용률 {usage_pct:.1f}%보니까 적당한 수준이네!
{current_plan}에서 데이터 {data_display}, 음성 {voice_display} 상태야~

**🎯 이런 선택지도 있어:**
• **{recommended_plans[0].name}** ({_safe_price_value(recommended_plans[0].price):,}원)
→ 네 패턴이랑 알잘딱깔센하게 맞아!
→ 비슷하거나 더 좋은 혜택 받을 수 있어

어떤 게 마음에 들어? 💜""" if recommended_plans else f"""너는 **{user_type}** 사용자야! 🎯

사용률 {usage_pct:.1f}%보니까 적당한 수준!
현재 요금제 패턴이 괜찮은 것 같아~ 💜"""

    else:  # general tone
        if recommendation_type == "urgent_upgrade":
            return f"""**{user_type}**로 분석됩니다! 📊

현재 사용률이 {usage_pct:.1f}%로 매우 높아 곧 한도에 도달할 수 있습니다.
{current_plan} 요금제에서 데이터 {data_display}, 음성 {voice_display}만 남은 상황입니다.

**💡 업그레이드 권장:**
• **{recommended_plans[0].name}** ({_safe_price_value(recommended_plans[0].price):,}원)
→ 월 {additional_cost:,}원 추가로 충분한 데이터 확보
→ 속도 제한 없이 안정적인 사용 가능

상위 요금제로 변경하시면 더 쾌적한 환경을 경험하실 수 있습니다.""" if recommended_plans else f"""**{user_type}**로 분석됩니다! 📊

현재 사용률이 {usage_pct:.1f}%로 매우 높습니다.
더 큰 데이터 용량의 요금제 변경을 권장합니다."""

        elif recommendation_type == "maintain":
            return f"""**{user_type}**로 분석됩니다! ✅

{current_plan} 요금제 사용률이 {usage_pct:.1f}%로 적절한 수준입니다.
데이터 {data_display}, 음성 {voice_display}가 남아있어 안정적입니다.

**📊 현재 상태:**
• **{recommended_plans[0].name}** ({_safe_price_value(recommended_plans[0].price):,}원)
→ 사용 패턴과 요금제가 잘 매칭됨
→ 비슷한 조건에서 더 나은 혜택도 확인 가능

현재 패턴을 유지하시거나 더 나은 혜택을 고려해보세요.""" if recommended_plans else f"""**{user_type}**로 분석됩니다! ✅

{current_plan} 요금제 사용률이 {usage_pct:.1f}%로 적절한 수준입니다.
현재 요금제를 유지하시면 됩니다."""

        elif recommendation_type == "downgrade":
            return f"""**{user_type}**로 분석됩니다! 💰

사용률 {usage_pct:.1f}%로 현재 요금제 대비 사용량이 적습니다.
데이터 {data_display}나 남아있어 비용 절약 기회가 있습니다.

**💸 절약 효과:**
• **{recommended_plans[0].name}** ({_safe_price_value(recommended_plans[0].price):,}원)
→ 월 {monthly_saving:,}원 절약 (연간 {monthly_saving*12:,}원!)
→ 절약된 비용으로 다른 서비스 이용 가능

더 경제적인 요금제로 합리적인 절약이 가능합니다.""" if recommended_plans else f"""**{user_type}**로 분석됩니다! 💰

사용률 {usage_pct:.1f}%로 현재 요금제가 과도할 수 있습니다.
더 저렴한 요금제를 고려해보시기 바랍니다."""

        else:  # upgrade, alternative, cost_optimize
            return f"""**{user_type}** 사용자로 분석됩니다! 🎯

사용률 {usage_pct:.1f}%로 적절한 수준입니다.
{current_plan}에서 데이터 {data_display}, 음성 {voice_display} 남은 상태입니다.

**💡 추천 옵션:**
• **{recommended_plans[0].name}** ({_safe_price_value(recommended_plans[0].price):,}원)
→ 사용 패턴에 최적화된 요금제
→ 비슷한 조건에서 더 나은 혜택 가능

고객님의 사용 패턴에 가장 적합한 선택을 하시면 됩니다.""" if recommended_plans else f"""**{user_type}** 사용자로 분석됩니다! 🎯

사용률 {usage_pct:.1f}%로 적절한 수준입니다.
현재 요금제가 패턴에 맞는 것 같습니다."""

@router.post("/usage/recommend", summary="사용량 기반 추천", description="plan_id가 있으면 해당 요금제의 사용량 데이터를 생성하여 추천합니다.")
async def usage_based_recommendation(
    plan_id: Optional[int] = Query(None, description="요금제 ID (없으면 안내 메시지)"),
    tone: str = Query("general", description="응답 톤 (general: 정중한 말투, muneoz: 친근한 말투)")
):
    """
    사용량 기반 요금제 추천 - plan_id 기반 더미데이터 생성
    """
    async def generate_stream():
        try:
            print(f"[DEBUG] Usage recommendation request - plan_id: {plan_id}, tone: {tone}")

            # plan_id가 없으면 안내 메시지만 스트리밍
            if not plan_id:
                print(f"[DEBUG] No plan_id provided, showing guidance message")

                # 스트리밍 시작 신호
                yield f"data: {json.dumps({'type': 'message_start'}, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.05)

                # 안내 메시지 스트리밍
                guidance_message = _generate_no_plan_message(tone)
                words = guidance_message.split(' ')
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

            # plan_id로 더미데이터 생성
            usage_data = generate_usage_for_plan(plan_id)
            if not usage_data:
                error_data = {
                    "type": "error",
                    "message": f"요금제 ID {plan_id}를 찾을 수 없습니다." if tone == "general" else f"어? {plan_id}번 요금제가 없어! 😅"
                }
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
                return

            print(f"[DEBUG] Generated usage data for plan {plan_id}: {usage_data['usage_percentage']:.1f}% usage")

            # 2. 전체 요금제 목록 조회
            all_plans = get_all_plans()
            if not all_plans:
                error_data = {
                    "type": "error",
                    "message": "요금제 데이터를 불러올 수 없습니다." if tone == "general" else "앗! 요금제 데이터가 없어! 😅"
                }
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
                return

            # 3. 사용량 분석 카드 데이터 먼저 전송
            usage_summary = {
                "type": "usage_analysis",
                "data": {
                    "user_id": usage_data["user_id"],
                    "current_plan": usage_data["current_plan_name"],
                    "current_price": usage_data["current_plan_price"],
                    "remaining_data": usage_data["remaining_data"],
                    "remaining_voice": usage_data["remaining_voice"],
                    "remaining_sms": usage_data["remaining_sms"],
                    "usage_percentage": usage_data["usage_percentage"],
                    "used_data": usage_data["used_data"],
                    "used_voice": usage_data["used_voice"],
                    "used_sms": usage_data["used_sms"],
                    "total_data": usage_data["total_data"],
                    "total_voice": usage_data["total_voice"],
                    "total_sms": usage_data["total_sms"]
                }
            }
            yield f"data: {json.dumps(usage_summary, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.1)

            # 4. 추천 요금제 분석 및 카드 데이터 전송
            recommendation_type = _analyze_usage_pattern(usage_data)
            recommended_plans = _filter_plans_by_usage(all_plans, usage_data, recommendation_type)

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

            # 5. 스트리밍 시작 신호
            yield f"data: {json.dumps({'type': 'message_start'}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.05)

            # 6. 맞춤 설명 스트리밍
            usage_explanation = _generate_usage_explanation(usage_data, recommendation_type, recommended_plans, tone)

            words = usage_explanation.split(' ')
            for i, word in enumerate(words):
                chunk_data = {
                    "type": "message_chunk",
                    "content": word + (" " if i < len(words) - 1 else "")
                }
                yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.05)

            # 7. 스트리밍 완료 신호
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
    사용자 사용량 조회 - plan_id 기반으로 수정 필요시 사용
    """
    try:
        # 실제로는 user 테이블에서 plan_id를 조회해서 generate_usage_for_plan() 호출
        # 현재는 user_id를 plan_id로 간주하여 처리
        usage_data = generate_usage_for_plan(user_id)

        if not usage_data:
            return {
                "success": False,
                "message": f"사용자 {user_id}의 요금제 정보를 찾을 수 없습니다.",
                "data": None
            }

        # 응답 데이터 구성
        response_data = {
            "user_id": usage_data["user_id"],
            "current_plan": {
                "name": usage_data["current_plan_name"],
                "price": usage_data["current_plan_price"]
            },
            "remaining": {
                "data": f"{usage_data['remaining_data']}MB" if usage_data['remaining_data'] != 999999 else "무제한",
                "voice": f"{usage_data['remaining_voice']}분" if usage_data['remaining_voice'] != 999999 else "무제한",
                "sms": f"{usage_data['remaining_sms']}건" if usage_data['remaining_sms'] != 999999 else "무제한"
            },
            "used": {
                "data": f"{usage_data['used_data']}MB",
                "voice": f"{usage_data['used_voice']}분",
                "sms": f"{usage_data['used_sms']}건"
            },
            "total": {
                "data": f"{usage_data['total_data']}MB" if usage_data['total_data'] != 999999 else "무제한",
                "voice": f"{usage_data['total_voice']}분" if usage_data['total_voice'] != 999999 else "무제한",
                "sms": f"{usage_data['total_sms']}건" if usage_data['total_sms'] != 999999 else "무제한"
            },
            "usage_percentage": usage_data["usage_percentage"],
            "status": _get_usage_status(usage_data["usage_percentage"])
        }

        return {
            "success": True,
            "message": "사용량 조회 성공",
            "data": response_data
        }

    except Exception as e:
        print(f"[ERROR] Usage data retrieval failed: {e}")
        return {
            "success": False,
            "message": f"사용량 조회 실패: {str(e)}",
            "data": None
        }

def _get_usage_status(usage_percentage: float) -> dict:
    """사용률에 따른 상태 정보"""
    if usage_percentage >= 90:
        return {
            "level": "critical",
            "message": "사용량이 거의 소진되었습니다",
            "recommendation": "요금제 업그레이드를 권장합니다"
        }
    elif usage_percentage >= 75:
        return {
            "level": "warning",
            "message": "사용량이 많습니다",
            "recommendation": "사용량을 확인하시거나 상위 요금제를 고려해보세요"
        }
    elif usage_percentage >= 40:
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