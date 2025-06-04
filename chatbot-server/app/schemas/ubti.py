# app/schemas/ubti.py
from pydantic import BaseModel

class UBTIRequest(BaseModel):
    session_id: str
    message: str  # 성향 분석용 단일 응답만 받음
