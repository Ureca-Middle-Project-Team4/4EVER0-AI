from pydantic import BaseModel
from typing import Optional, Union, Dict, List

class PlanOrSubscription(BaseModel):
    name: str
    description: str

class Recommendation(BaseModel):
    plan: PlanOrSubscription
    subscription: PlanOrSubscription

class MatchingType(BaseModel):
    code: str
    name: str
    emoji: str
    reason: str

class UBTIType(BaseModel):
    code: str
    name: str
    emoji: str
    description: str

class UBTIRequest(BaseModel):
    session_id: str
    message: Optional[str] = None

class UBTIQuestion(BaseModel):
    question: str
    step: int

class UBTIResult(BaseModel):
    ubti_type: UBTIType
    summary: str
    recommendation: Recommendation
    matching_type: UBTIType

class UBTIComplete(BaseModel):
    completed: bool = True
    message: str = "모든 질문이 완료되었습니다."

