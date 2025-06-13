from pydantic import BaseModel
from typing import Optional

class ChatRequest(BaseModel):
    session_id: str
    message: str
    tone: Optional[str] = "general"  # 기본값: 일반 말투

class UBTIRequest(BaseModel):
    session_id: str
    message: Optional[str] = None
    tone: Optional[str] = "general"  # 기본값: 일반 말투

class LikesChatRequest(BaseModel):
    session_id: str
    tone: Optional[str] = "general"  # 기본값: 일반 말투