from pydantic import BaseModel
from typing import List, Optional

class UserProfile(BaseModel):
    age_group: str
    interests: List[str]
    time_usage: List[str]

class MultiTurnRequest(BaseModel):
    session_id: str
    age_group: Optional[str] = None
    interests: Optional[List[str]] = None
    time_usage: Optional[List[str]] = None

class RecommendedItem(BaseModel):
    title: str
    description: str
    image_url: str
    detail_url: str
    price: str
    reason: Optional[str] = None
