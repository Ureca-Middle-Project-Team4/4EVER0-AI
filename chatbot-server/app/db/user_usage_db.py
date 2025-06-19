from app.db.database import SessionLocal
from app.db.models import Plan
from app.schemas.usage import UserUsageInfo
from typing import Optional
import io

def get_user_current_usage(user_id: int) -> Optional[UserUsageInfo]:
    """사용자 현재 요금제 사용량 조회 - CSV id(PK) 기반"""

    # 🔥 CSV 기반 목업 데이터 (id가 Primary Key)
    # CSV 구조: id(PK), plan_id, user_id(문자열), email, phone_number, name, birth,
    #          attendance_streaks, point, attendance_streak, data_usage, voice_usage, sms_usage

    mock_csv_data = {
        1: {  # id (Primary Key)
            "id": 1,
            "plan_id": 2,
            "user_id": "user001",
            "data_usage": 1200,    # 사용한 데이터 (MB)
            "voice_usage": 180,    # 사용한 통화 (분)
            "sms_usage": 45        # 사용한 문자 (건)
        },
        2: {
            "id": 2,
            "plan_id": 5,
            "user_id": "user002",
            "data_usage": 2500,
            "voice_usage": 90,
            "sms_usage": 20
        },
        3: {
            "id": 3,
            "plan_id": 3,
            "user_id": "user003",
            "data_usage": 7800,
            "voice_usage": 280,
            "sms_usage": 95
        }
    }

    # user_id로 조회 (user_id = CSV의 id 컬럼)
    if user_id not in mock_csv_data:
        print(f"[ERROR] User with id {user_id} not found in CSV data")
        return None

    user_data = mock_csv_data[user_id]

    # Plan 정보 조회
    db = SessionLocal()
    try:
        plan_id = user_data["plan_id"]
        current_plan = db.query(Plan).filter(Plan.id == plan_id).first()

        if not current_plan:
            print(f"[ERROR] Plan {plan_id} not found for user {user_id}")
            return None

        # 요금제 한도 추출
        plan_data_mb = _extract_data_limit_mb(current_plan.data)
        plan_voice_min = _extract_voice_limit_min(current_plan.voice)
        plan_sms_count = _extract_sms_limit(current_plan.sms)

        # 남은 용량 계산 (전체 한도 - 사용량)
        remaining_data = max(0, plan_data_mb - user_data["data_usage"])
        remaining_voice = max(0, plan_voice_min - user_data["voice_usage"])
        remaining_sms = max(0, plan_sms_count - user_data["sms_usage"])

        # 공유 데이터 남은 용량 계산
        plan_share_data_mb = _extract_share_data_mb(current_plan.share_data)
        remaining_share_data = max(0, plan_share_data_mb - user_data["data_usage"])

        # 사용률 계산
        usage_percentage = _calculate_usage_percentage(
            remaining_data=remaining_data,
            remaining_voice=remaining_voice,
            remaining_sms=remaining_sms,
            total_data=plan_data_mb,
            total_voice=plan_voice_min,
            total_sms=plan_sms_count
        )

        return UserUsageInfo(
            user_id=user_id,  # CSV의 id (Primary Key)
            current_plan_name=current_plan.name,
            current_plan_price=current_plan.price,
            remaining_data=remaining_data,  # 계산된 남은 데이터 (MB)
            remaining_share_data=remaining_share_data,  # 계산된 남은 공유 데이터 (MB)
            remaining_voice=remaining_voice,  # 계산된 남은 통화 (분)
            remaining_sms=remaining_sms,  # 계산된 남은 문자 (건)
            usage_percentage=usage_percentage
        )

    except Exception as e:
        print(f"[ERROR] Database error in get_user_current_usage: {e}")
        return None
    finally:
        db.close()

def get_user_from_csv(user_id: int, csv_content: str) -> Optional[dict]:
    """CSV에서 사용자 정보 조회 (id 기반)"""
    try:
        # 간단한 CSV 파싱
        lines = csv_content.strip().split('\n')
        if len(lines) < 2:
            return None

        # 헤더 파싱
        headers = [h.strip() for h in lines[0].split(',')]

        # 데이터 찾기 (id 컬럼으로 검색)
        for line in lines[1:]:
            values = [v.strip() for v in line.split(',')]
            row_data = dict(zip(headers, values))

            # id 컬럼으로 매칭 (user_id 파라미터 = CSV의 id)
            if row_data.get('id') == str(user_id):
                return {
                    "id": int(row_data.get('id')),
                    "plan_id": float(row_data.get('plan_id', 0)),
                    "user_id": row_data.get('user_id'),  # 문자열 필드
                    "data_usage": int(row_data.get('data_usage', 0)),  # MB
                    "voice_usage": int(row_data.get('voice_usage', 0)),  # 분
                    "sms_usage": int(row_data.get('sms_usage', 0)),  # 건
                    "point": int(row_data.get('point', 0)),
                    "attendance_streak": int(row_data.get('attendance_streak', 0))
                }

        return None

    except Exception as e:
        print(f"[ERROR] CSV parsing error: {e}")
        return None

def _extract_data_limit_mb(data_str: str) -> int:
    """데이터 제한량을 MB로 변환 (예: '8GB' -> 8000MB, '무제한' -> 999999MB)"""
    if not data_str or data_str == '무제한':
        return 999999  # 무제한의 경우 큰 값

    try:
        if 'GB' in data_str:
            gb_value = float(data_str.replace('GB', '').strip())
            return int(gb_value * 1000)  # GB를 MB로 변환
        elif 'MB' in data_str:
            return int(data_str.replace('MB', '').strip())
        else:
            # 숫자만 있는 경우 GB로 가정
            return int(float(data_str) * 1000)
    except:
        return 0

def _extract_voice_limit_min(voice_str: str) -> int:
    """음성 제한량을 분으로 변환 (예: '부가통화 300분' -> 300)"""
    if not voice_str or voice_str == '무제한':
        return 999999

    try:
        # 숫자 추출
        import re
        numbers = re.findall(r'\d+', voice_str)
        if numbers:
            return int(numbers[0])
        return 0
    except:
        return 0

def _extract_sms_limit(sms_str: str) -> int:
    """SMS 제한량 추출 (예: '기본제공' -> 999999)"""
    if not sms_str or sms_str == '기본제공' or sms_str == '무제한':
        return 999999

    try:
        import re
        numbers = re.findall(r'\d+', sms_str)
        if numbers:
            return int(numbers[0])
        return 999999  # 기본적으로 제한 없음
    except:
        return 999999

def _extract_share_data_mb(share_data_str: str) -> int:
    """공유 데이터 용량을 MB로 변환"""
    if not share_data_str or share_data_str == '무제한' or share_data_str == '-':
        return 999999

    try:
        if 'GB' in share_data_str:
            gb_value = float(share_data_str.replace('GB', '').strip())
            return int(gb_value * 1000)
        elif 'MB' in share_data_str:
            return int(share_data_str.replace('MB', '').strip())
        else:
            return int(float(share_data_str) * 1000)
    except:
        return 0

def _calculate_usage_percentage(remaining_data: int, remaining_voice: int, remaining_sms: int,
                               total_data: int, total_voice: int, total_sms: int) -> float:
    """전체 사용률 계산 (가중평균)"""
    try:
        # 각 항목별 사용률 계산
        data_usage_rate = max(0, (total_data - remaining_data) / total_data * 100) if total_data > 0 else 0
        voice_usage_rate = max(0, (total_voice - remaining_voice) / total_voice * 100) if total_voice > 0 else 0
        sms_usage_rate = max(0, (total_sms - remaining_sms) / total_sms * 100) if total_sms > 0 else 0

        # 가중평균 (데이터 60%, 음성 30%, SMS 10%)
        weighted_usage = (data_usage_rate * 0.6 + voice_usage_rate * 0.3 + sms_usage_rate * 0.1)

        return min(100.0, max(0.0, weighted_usage))
    except:
        return 0.0