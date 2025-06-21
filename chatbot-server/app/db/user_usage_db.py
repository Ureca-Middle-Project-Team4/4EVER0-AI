from typing import Optional
from app.db.database import SessionLocal
from app.db.models import Plan, User
from app.schemas.usage import UserUsageInfo

def get_user_current_usage(user_id: int) -> Optional[UserUsageInfo]:
    """DB에서 user_id로 사용자 사용량 조회"""

    db = SessionLocal()
    try:
        # 1) 사용자 레코드 조회
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            print(f"[ERROR] User {user_id} not found")
            return None

        # 2) Plan 정보 조회
        plan = db.query(Plan).filter(Plan.id == user.plan_id).first()
        if not plan:
            print(f"[ERROR] Plan {user.plan_id} not found")
            return None

        # 3) Plan 한도 추출 (MB, 분, 건수)
        total_data_mb   = _extract_data_limit_mb(plan.data)
        total_voice_min = _extract_voice_limit_min(plan.voice)
        total_sms_count = _extract_sms_limit(plan.sms)

        # 4) DB에 저장된 사용량(또는 남은량) 컬럼 사용
        #    실제 컬럼명에 맞춰 user.data_usage, user.voice_usage, user.sms_usage 사용
        used_data_mb   = user.data_usage
        used_voice_min = user.voice_usage
        used_sms_count = user.sms_usage

        # 5) 남은 용량 계산
        remaining_data       = max(0, total_data_mb - used_data_mb)
        remaining_voice      = max(0, total_voice_min - used_voice_min)
        remaining_sms        = max(0, total_sms_count - used_sms_count)
        remaining_share_data = 0   # 공유 데이터 컬럼이 없으면 0으로 고정

        # 6) 사용률 계산
        usage_percentage = _calculate_usage_percentage(
            remaining_data=remaining_data,
            remaining_voice=remaining_voice,
            remaining_sms=remaining_sms,
            total_data=total_data_mb,
            total_voice=total_voice_min,
            total_sms=total_sms_count
        )

        # 7) UserUsageInfo 반환
        return UserUsageInfo(
            user_id=user.id,
            current_plan_name=plan.name,
            current_plan_price=plan.price,
            remaining_data=remaining_data,
            remaining_share_data=remaining_share_data,
            remaining_voice=remaining_voice,
            remaining_sms=remaining_sms,
            usage_percentage=usage_percentage
        )

    except Exception as e:
        print(f"[ERROR] get_user_current_usage failed: {e}")
        return None
    finally:
        db.close()


def _extract_data_limit_mb(data_str: str) -> int:
    """데이터 제한량을 MB로 변환"""
    if not data_str or data_str == '무제한':
        return 999999
    try:
        if 'GB' in data_str:
            return int(float(data_str.replace('GB','').strip()) * 1000)
        if 'MB' in data_str:
            return int(data_str.replace('MB','').strip())
        return int(float(data_str) * 1000)
    except:
        return 0

def _extract_voice_limit_min(voice_str: str) -> int:
    """음성 제한량을 분으로 변환"""
    if not voice_str or voice_str == '무제한':
        return 999999
    import re
    nums = re.findall(r'\d+', voice_str)
    return int(nums[0]) if nums else 0

def _extract_sms_limit(sms_str: str) -> int:
    """SMS 제한량 추출"""
    if not sms_str or sms_str in ('무제한', '기본제공'):
        return 999999
    import re
    nums = re.findall(r'\d+', sms_str)
    return int(nums[0]) if nums else 999999

def _calculate_usage_percentage(
    remaining_data: int,
    remaining_voice: int,
    remaining_sms: int,
    total_data: int,
    total_voice: int,
    total_sms: int
) -> float:
    """가중평균 사용률 계산 (데이터60, 음성30, SMS10)"""
    try:
        data_rate  = (total_data - remaining_data) / total_data * 100 if total_data else 0
        voice_rate = (total_voice - remaining_voice) / total_voice * 100 if total_voice else 0
        sms_rate   = (total_sms - remaining_sms) / total_sms * 100 if total_sms else 0
        weighted   = data_rate * 0.6 + voice_rate * 0.3 + sms_rate * 0.1
        return max(0.0, min(100.0, weighted))
    except:
        return 0.0
