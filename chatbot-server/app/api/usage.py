from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from app.schemas.usage import CurrentUsageRequest
from app.db.user_usage_db import get_user_current_usage
from app.db.plan_db import get_all_plans
from app.db.database import SessionLocal
from app.db.models import Plan, User
import json
import asyncio
import random
from typing import Optional

router = APIRouter()

def _get_user_plan_status(user_id: int) -> dict:
    """사용자의 요금제 가입 상태 확인"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"has_user": False, "has_plan": False}

        return {
            "has_user": True,
            "has_plan": user.plan_id is not None,
            "plan_id": user.plan_id
        }
    except Exception as e:
        print(f"[ERROR] _get_user_plan_status failed: {e}")
        return {"has_user": False, "has_plan": False}
    finally:
        db.close()

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
    plan_data = get_plan_by_id(plan_id)
    if not plan_data:
        return None

    limits = parse_plan_limits(plan_data)
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
        "user_id": f"plan_{plan_id}",
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

def _analyze_usage_pattern(usage) -> str:
    """사용 패턴 분석"""
    if not usage:
        return "unknown"

    # Pydantic 모델인지 딕셔너리인지 확인
    if hasattr(usage, 'usage_percentage'):
        usage_pct = usage.usage_percentage
    else:
        usage_pct = usage.get('usage_percentage', 0)

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

    # Pydantic 모델인지 딕셔너리인지 확인
    if hasattr(usage, 'current_plan_price'):
        current_price = usage.current_plan_price
    else:
        current_price = usage.get('current_plan_price', 35000)

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

def _generate_no_plan_message(tone: str = "general") -> str:
    """요금제 미가입 시 안내 메시지"""
    if tone == "muneoz":
        return """어? 아직 요금제가 없구나! 😅

먼저 요금제를 가입하고 며칠 사용해봐야
네 사용 패턴을 분석할 수 있어!

**🎯 이렇게 해봐:**
• **"요금제 추천해줘"** 라고 말해봐
• 마음에 드는 걸로 가입하고
• 며칠 쓴 다음에 다시 와줘!

그럼 완전 럭키비키하게 맞춤 분석해줄게~ 🐙💜"""
    else:
        return """사용량 분석을 위해서는 먼저 요금제 가입이 필요합니다! 😊

현재 가입된 요금제가 없어서
사용 데이터를 분석할 수 없어요.

**💡 추천 방법:**
• **"요금제 추천해주세요"**라고 말씀해주시면
  기본 상담을 받으실 수 있어요
• 요금제 가입 후 며칠 사용하시면
  정확한 맞춤 분석이 가능합니다!

언제든지 다시 찾아주세요! 🙏"""

def _generate_no_usage_data_message(plan_name: str, tone: str = "general") -> str:
    """요금제는 있지만 사용량 데이터가 부족할 때"""
    if tone == "muneoz":
        return f"""어? **{plan_name}** 쓰고 있구나! 👍

근데 아직 사용량 데이터가 별로 없어서
정확한 분석이 어려워! 😅

**🎯 며칠 더 써보고 와줘:**
• 데이터 좀 쓰고
• 전화도 좀 하고
• 며칠 후에 다시 시도해봐!

그럼 완전 정확한 맞춤 분석 해줄게~ 🐙✨"""
    else:
        return f"""**{plan_name}** 요금제를 사용하고 계시네요! 👍

아직 사용량 데이터가 충분하지 않아
정확한 분석이 어려운 상황입니다.

**💡 권장사항:**
• 며칠 더 사용하신 후 다시 시도해주세요
• 데이터, 통화, 문자를 조금씩 사용하시면
  더 정확한 맞춤 분석이 가능합니다!

조금만 기다려주시면 완벽한 추천을 받으실 수 있어요! 😊"""

def _generate_usage_explanation(usage, recommendation_type: str, recommended_plans: list, tone: str) -> str:
    """사용량 기반 맞춤 설명 생성"""

    # Pydantic 모델인지 딕셔너리인지 확인
    if hasattr(usage, 'usage_percentage'):
        usage_pct = usage.usage_percentage
        current_plan = usage.current_plan_name
        current_price = usage.current_plan_price
        remaining_data = usage.remaining_data
        remaining_voice = usage.remaining_voice
    else:
        usage_pct = usage.get('usage_percentage', 0)
        current_plan = usage.get('current_plan_name', '현재 요금제')
        current_price = usage.get('current_plan_price', 0)
        remaining_data = usage.get('remaining_data', 0)
        remaining_voice = usage.get('remaining_voice', 0)

    # 데이터 표시 방식 개선
    if remaining_data == 999999:
        data_display = "무제한"
        data_gb = "무제한"
    else:
        data_gb = f"{remaining_data / 1000:.1f}GB"
        data_display = data_gb

    # 음성 표시 방식 개선
    if remaining_voice == 999999:
        voice_display = "무제한"
    else:
        voice_display = f"{remaining_voice}분"

    # 추천 요금제 최고 가격과 최저 가격
    plan_prices = [_safe_price_value(plan.price) for plan in recommended_plans] if recommended_plans else [current_price]
    min_price = min(plan_prices)
    max_price = max(plan_prices)
    monthly_saving = current_price - min_price if current_price > min_price else 0
    additional_cost = max_price - current_price if max_price > current_price else 0

    # 사용자 타입 분석
    try:
        data_gb_float = float(data_gb.replace('GB', '')) if 'GB' in str(data_gb) else 0
    except:
        data_gb_float = 0

    voice_min = remaining_voice if remaining_voice != 999999 else 300
    user_type = _analyze_user_type(usage_pct, data_gb_float, voice_min)

    if tone == "muneoz":
        if recommendation_type == "urgent_upgrade":
            plan_info = f"• **{recommended_plans[0].name}** ({_safe_price_value(recommended_plans[0].price):,}원)\n→ 월 {additional_cost:,}원 더 내면 데이터 걱정 뚝!\n→ 속도 제한 걸리기 전에 미리미리 바꾸자!" if recommended_plans else "더 큰 요금제로 급하게 바꾸는 걸 추천해! 🚨"

            return f"""헉! 너는 완전 **{user_type}** 타입이구나! 🔥

사용률이 {usage_pct:.1f}%나 돼서 거의 다 썼어! 🚨
{current_plan}에서 데이터 {data_display}, 음성 {voice_display}밖에 안 남았네!

**🎯 급하게 업그레이드 필요:**
{plan_info}

지금 바꾸면 완전 럭키비키할 거야! ✨"""

        elif recommendation_type == "maintain":
            plan_info = f"• **{recommended_plans[0].name}** ({_safe_price_value(recommended_plans[0].price):,}원)\n→ 지금 요금제가 네 패턴이랑 찰떡궁합!\n→ 혹시 더 좋은 혜택 있는 것도 확인해봐" if recommended_plans else "현재 요금제가 네 패턴이랑 완전 찰떡이야! 💜"

            return f"""오~ 너는 **{user_type}** 사용자네! 😊

{current_plan} 사용률 {usage_pct:.1f}%로 딱 적당해!
데이터 {data_display}, 음성 {voice_display} 남아있고 균형 잡혔어!

**🎯 현재 상태가 완전 좋아:**
{plan_info}

현재 패턴 유지하면 완전 굿! 💜"""

        elif recommendation_type == "downgrade":
            plan_info = f"• **{recommended_plans[0].name}** ({_safe_price_value(recommended_plans[0].price):,}원)\n→ 월 {monthly_saving:,}원 절약! (연간 {monthly_saving*12:,}원!)\n→ 그 돈으로 맛있는 거 사먹자!" if recommended_plans else "더 저렴한 요금제로 바꾸면 절약할 수 있어! ✨"

            return f"""완전 **{user_type}**구나! 💸

사용률 {usage_pct:.1f}%밖에 안 돼서 돈 아까워!
데이터 {data_display}나 남았는데 완전 오버스펙이야!

**🎯 절약 각:**
{plan_info}

확 바꿔서 싹싹김치하자! ✨"""

        else:  # upgrade, alternative, cost_optimize
            plan_info = f"• **{recommended_plans[0].name}** ({_safe_price_value(recommended_plans[0].price):,}원)\n→ 네 패턴이랑 알잘딱깔센하게 맞아!\n→ 비슷하거나 더 좋은 혜택 받을 수 있어" if recommended_plans else "현재 요금제 패턴이 괜찮은 것 같아~ 💜"

            return f"""너는 **{user_type}** 사용자야! 🎯

사용률 {usage_pct:.1f}%보니까 적당한 수준이네!
{current_plan}에서 데이터 {data_display}, 음성 {voice_display} 상태야~

**🎯 이런 선택지도 있어:**
{plan_info}

어떤 게 마음에 들어? 💜"""

    else:  # general tone
        if recommendation_type == "urgent_upgrade":
            plan_info = f"• **{recommended_plans[0].name}** ({_safe_price_value(recommended_plans[0].price):,}원)\n→ 월 {additional_cost:,}원 추가로 충분한 데이터 확보\n→ 속도 제한 없이 안정적인 사용 가능" if recommended_plans else "더 큰 데이터 용량의 요금제 변경을 권장합니다."

            return f"""**{user_type}**로 분석됩니다! 📊

현재 사용률이 {usage_pct:.1f}%로 매우 높아 곧 한도에 도달할 수 있습니다.
{current_plan} 요금제에서 데이터 {data_display}, 음성 {voice_display}만 남은 상황입니다.

**💡 업그레이드 권장:**
{plan_info}

상위 요금제로 변경하시면 더 쾌적한 환경을 경험하실 수 있습니다."""

        elif recommendation_type == "maintain":
            plan_info = f"• **{recommended_plans[0].name}** ({_safe_price_value(recommended_plans[0].price):,}원)\n→ 사용 패턴과 요금제가 잘 매칭됨\n→ 비슷한 조건에서 더 나은 혜택도 확인 가능" if recommended_plans else "현재 요금제를 유지하시면 됩니다."

            return f"""**{user_type}**로 분석됩니다! ✅

{current_plan} 요금제 사용률이 {usage_pct:.1f}%로 적절한 수준입니다.
데이터 {data_display}, 음성 {voice_display}가 남아있어 안정적입니다.

**📊 현재 상태:**
{plan_info}

현재 패턴을 유지하시거나 더 나은 혜택을 고려해보세요."""

        elif recommendation_type == "downgrade":
            plan_info = f"• **{recommended_plans[0].name}** ({_safe_price_value(recommended_plans[0].price):,}원)\n→ 월 {monthly_saving:,}원 절약 (연간 {monthly_saving*12:,}원!)\n→ 절약된 비용으로 다른 서비스 이용 가능" if recommended_plans else "더 저렴한 요금제를 고려해보시기 바랍니다."

            return f"""**{user_type}**로 분석됩니다! 💰

사용률 {usage_pct:.1f}%로 현재 요금제 대비 사용량이 적습니다.
데이터 {data_display}나 남아있어 비용 절약 기회가 있습니다.

**💸 절약 효과:**
{plan_info}

더 경제적인 요금제로 합리적인 절약이 가능합니다."""

        else:  # upgrade, alternative, cost_optimize
            plan_info = f"• **{recommended_plans[0].name}** ({_safe_price_value(recommended_plans[0].price):,}원)\n→ 사용 패턴에 최적화된 요금제\n→ 비슷한 조건에서 더 나은 혜택 가능" if recommended_plans else "현재 요금제가 패턴에 맞는 것 같습니다."

            return f"""**{user_type}** 사용자로 분석됩니다! 🎯

사용률 {usage_pct:.1f}%로 적절한 수준입니다.
{current_plan}에서 데이터 {data_display}, 음성 {voice_display} 남은 상태입니다.

**💡 추천 옵션:**
{plan_info}

고객님의 사용 패턴에 가장 적합한 선택을 하시면 됩니다."""

@router.post("/usage/recommend")
async def usage_based_recommendation(
    user_id: int = Query(..., description="사용자 ID"),
    tone: str = Query("general", description="응답 톤")
):
    async def generate_stream():
        try:
            print(f"[DEBUG] Usage recommendation request - user_id: {user_id}, tone: {tone}")

            # 1. 사용자 요금제 가입 상태 확인
            user_status = _get_user_plan_status(user_id)
            print(f"[DEBUG] User status: {user_status}")

            if not user_status["has_user"]:
                # 사용자 자체가 없음
                error_data = {
                    "type": "error",
                    "message": "사용자 정보를 찾을 수 없습니다." if tone == "general" else "어? 사용자를 못 찾겠어! 😅"
                }
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
                return

            if not user_status["has_plan"]:
                # 요금제 미가입 - 안내 메시지만 스트리밍
                print(f"[INFO] User {user_id} has no plan, providing guidance")

                yield f"data: {json.dumps({'type': 'message_start'}, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.05)

                guidance_message = _generate_no_plan_message(tone)
                words = guidance_message.split(' ')
                for i, word in enumerate(words):
                    chunk_data = {
                        "type": "message_chunk",
                        "content": word + (" " if i < len(words) - 1 else "")
                    }
                    yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.05)

                yield f"data: {json.dumps({'type': 'message_end'}, ensure_ascii=False)}\n\n"
                return

            # 2. 실제 DB에서 사용량 데이터 조회
            user_usage = get_user_current_usage(user_id)
            print(f"[DEBUG] Real DB usage data: {user_usage}")

            # 실제 데이터가 없거나 사용량이 모두 0이면 더미 데이터 생성
            should_use_fake_data = False

            if not user_usage:
                print(f"[INFO] No real usage data found")
                should_use_fake_data = True
            else:
                print(f"[DEBUG] Real usage percentage: {user_usage.usage_percentage}")
                print(f"[DEBUG] Real remaining data: {user_usage.remaining_data}")
                print(f"[DEBUG] Real current plan: {user_usage.current_plan_name}")

                # 사용량이 모두 0이거나 사용률이 0%면 더미 데이터 사용
                if user_usage.usage_percentage <= 0:
                    print(f"[INFO] Real usage data is all zero, using fake data instead")
                    should_use_fake_data = True

            if should_use_fake_data:
                print(f"[INFO] Generating fake data for user {user_id} with plan_id {user_status['plan_id']}")
                fake_usage_data = generate_usage_for_plan(user_status['plan_id'])
                print(f"[DEBUG] Generated fake data: {fake_usage_data}")

                if not fake_usage_data:
                    # Plan 이름 조회해서 안내 메시지
                    db = SessionLocal()
                    try:
                        user = db.query(User).filter(User.id == user_id).first()
                        plan = db.query(Plan).filter(Plan.id == user.plan_id).first()
                        plan_name = plan.name if plan else "현재 요금제"
                    finally:
                        db.close()

                    yield f"data: {json.dumps({'type': 'message_start'}, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.05)

                    no_data_message = _generate_no_usage_data_message(plan_name, tone)
                    words = no_data_message.split(' ')
                    for i, word in enumerate(words):
                        chunk_data = {
                            "type": "message_chunk",
                            "content": word + (" " if i < len(words) - 1 else "")
                        }
                        yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
                        await asyncio.sleep(0.05)

                    yield f"data: {json.dumps({'type': 'message_end'}, ensure_ascii=False)}\n\n"
                    return

                # 가짜 데이터 사용
                user_usage = fake_usage_data
                print(f"[DEBUG] Using fake data: usage_percentage={fake_usage_data['usage_percentage']}")

            # 3. 정상적인 사용량 분석 및 추천
            all_plans = get_all_plans()
            if not all_plans:
                error_data = {
                    "type": "error",
                    "message": "요금제 데이터를 불러올 수 없습니다." if tone == "general" else "앗! 요금제 데이터가 없어! 😅"
                }
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
                return

            # 사용량 분석 결과 전송
            if hasattr(user_usage, 'current_plan_name'):
                # Pydantic 모델
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
            else:
                # 딕셔너리 (생성된 데이터)
                usage_summary = {
                    "type": "usage_analysis",
                    "data": {
                        "user_id": user_id,
                        "current_plan": user_usage["current_plan_name"],
                        "current_price": user_usage["current_plan_price"],
                        "remaining_data": user_usage["remaining_data"],
                        "remaining_voice": user_usage["remaining_voice"],
                        "remaining_sms": user_usage["remaining_sms"],
                        "usage_percentage": round(user_usage["usage_percentage"], 1)
                    }
                }

            yield f"data: {json.dumps(usage_summary, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.1)

            # 추천 요금제 카드 데이터 전송
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

            # 맞춤 설명 스트리밍
            yield f"data: {json.dumps({'type': 'message_start'}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.05)

            explanation = _generate_usage_explanation(user_usage, recommendation_type, recommended_plans, tone)
            words = explanation.split(' ')
            for i, word in enumerate(words):
                chunk_data = {
                    "type": "message_chunk",
                    "content": word + (" " if i < len(words) - 1 else "")
                }
                yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.05)

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
    사용자 사용량 조회 - 실제 DB 데이터 또는 생성된 데이터 반환
    """
    try:
        # 먼저 실제 사용량 데이터 조회
        user_usage = get_user_current_usage(user_id)

        if user_usage and user_usage.usage_percentage > 0:
            # 실제 DB 데이터가 있고 사용량이 0이 아닌 경우
            usage_data = {
                "user_id": user_usage.user_id,
                "current_plan_name": user_usage.current_plan_name,
                "current_plan_price": user_usage.current_plan_price,
                "remaining_data": user_usage.remaining_data,
                "remaining_voice": user_usage.remaining_voice,
                "remaining_sms": user_usage.remaining_sms,
                "usage_percentage": user_usage.usage_percentage
            }
        else:
            # 실제 데이터가 없거나 사용량이 0이면 사용자의 plan_id로 생성
            user_status = _get_user_plan_status(user_id)
            if not user_status["has_plan"]:
                return {
                    "success": False,
                    "message": f"사용자 {user_id}의 요금제 정보를 찾을 수 없습니다.",
                    "data": None
                }

            usage_data = generate_usage_for_plan(user_status["plan_id"])
            if not usage_data:
                return {
                    "success": False,
                    "message": f"사용자 {user_id}의 사용량 데이터를 생성할 수 없습니다.",
                    "data": None
                }

        # 응답 데이터 구성
        if hasattr(usage_data, 'get'):
            # 딕셔너리인 경우 (생성된 데이터)
            response_data = {
                "user_id": usage_data.get("user_id", user_id),
                "current_plan": {
                    "name": usage_data["current_plan_name"],
                    "price": usage_data["current_plan_price"]
                },
                "remaining": {
                    "data": f"{usage_data['remaining_data']}MB" if usage_data['remaining_data'] != 999999 else "무제한",
                    "voice": f"{usage_data['remaining_voice']}분" if usage_data['remaining_voice'] != 999999 else "무제한",
                    "sms": f"{usage_data['remaining_sms']}건" if usage_data['remaining_sms'] != 999999 else "무제한"
                },
                "usage_percentage": usage_data["usage_percentage"],
                "status": _get_usage_status(usage_data["usage_percentage"])
            }

            # 생성된 데이터인 경우 추가 정보 포함
            if "used_data" in usage_data:
                response_data["used"] = {
                    "data": f"{usage_data['used_data']}MB",
                    "voice": f"{usage_data['used_voice']}분",
                    "sms": f"{usage_data['used_sms']}건"
                }
                response_data["total"] = {
                    "data": f"{usage_data['total_data']}MB" if usage_data['total_data'] != 999999 else "무제한",
                    "voice": f"{usage_data['total_voice']}분" if usage_data['total_voice'] != 999999 else "무제한",
                    "sms": f"{usage_data['total_sms']}건" if usage_data['total_sms'] != 999999 else "무제한"
                }
        else:
            # Pydantic 모델인 경우 (실제 DB 데이터)
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