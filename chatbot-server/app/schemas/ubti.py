from pydantic import BaseModel
from typing import Optional, Union

class UBTIRequest(BaseModel):
    session_id: str
    message: Optional[str] = None

class UBTIQuestion(BaseModel):
    question: str
    step: int

class UBTIResult(BaseModel):
    message: str

class UBTIComplete(BaseModel):
    completed: bool = True
    message: str = "모든 질문이 완료되었습니다."
