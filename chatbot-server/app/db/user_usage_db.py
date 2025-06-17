from app.db.database import SessionLocal
from app.schemas.usage import UserUsageInfo
from typing import Optional

def get_user_current_usage(user_id: int) -> Optional[UserUsageInfo]:
    """사용자 현재 요금제 사용량 조회 (Mock 데이터, 추후 수정 예정)"""

    # Mock 데이터 (실제 환경에서는 DB에서 조회)
    mock_usage_data = {
        1: UserUsageInfo(
            user_id=1,
            current_plan_name="라이트 23",
            current_plan_price=23000,
            remaining_data=500,  # 0.5GB 남음
            remaining_share_data=0,
            remaining_voice=50,  # 50분 남음
            remaining_sms=100,
            usage_percentage=85.5
        ),
        2: UserUsageInfo(
            user_id=2,
            current_plan_name="너겟 34",
            current_plan_price=34000,
            remaining_data=15000,  # 15GB 남음
            remaining_share_data=2000,
            remaining_voice=300,
            remaining_sms=500,
            usage_percentage=25.3
        ),
        3: UserUsageInfo(
            user_id=3,
            current_plan_name="프리미엄 52",
            current_plan_price=52000,
            remaining_data=100,  # 0.1GB 남음
            remaining_share_data=50,
            remaining_voice=20,  # 20분 남음
            remaining_sms=50,
            usage_percentage=95.2
        )
    }

    return mock_usage_data.get(user_id)