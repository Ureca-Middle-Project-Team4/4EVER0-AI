from pydantic import BaseModel, EmailStr
from typing import Optional

class UserRead(BaseModel):
    id: int
    name: Optional[str]
    email: Optional[str]
    phone_number: Optional[str]
    plan_id: Optional[int]
    data_usage: Optional[int]
    voice_usage: Optional[int]
    sms_usage: Optional[int]
    attendance_streak: Optional[int]
    point: Optional[int]

    class Config:
        orm_mode = True
