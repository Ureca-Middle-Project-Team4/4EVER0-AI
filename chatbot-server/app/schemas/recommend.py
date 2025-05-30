from pydantic import BaseModel
from typing import List, Optional

# Pydantic models
class UserProfile(BaseModel):
    age_group: str
    interests: List[str]
    time_usage: List[str]

class RecommendedItem(BaseModel):
    title: str
    description: str
    image_url: str
    detail_url: str
    price: str
    reason: Optional[str] = None

