from pydantic import BaseModel
from typing import Optional, List

class CurrentUsageRequest(BaseModel):
    user_id: int
    tone: Optional[str] = "general"

class UserUsageInfo(BaseModel):
    user_id: int
    current_plan_name: str
    current_plan_price: int
    remaining_data: int  # MB 단위
    remaining_share_data: int  # MB 단위
    remaining_voice: int  # 분 단위
    remaining_sms: int  # 개수
    usage_percentage: float  # 전체 사용률 (0-100)

class PlanRecommendation(BaseModel):
    name: str
    price: int
    data: str
    voice: str
    reason: str

class UsageBasedRecommendation(BaseModel):
    current_status: UserUsageInfo
    recommendation_type: str  # "upgrade", "downgrade", "maintain", "alternative"
    recommended_plans: List[PlanRecommendation]
    reason: str
