from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.database import SessionLocal
from app.db.user_db import get_user, get_all_users
from app.schemas.user import UserRead
router = APIRouter(prefix="/users", tags=["Users"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/{user_id}", response_model=UserRead, summary="사용자 조회", description="사용자 ID로 특정 사용자의 정보를 조회합니다.")
def api_get_user(user_id: int, db: Session = Depends(get_db)):
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.get("/", response_model=List[UserRead], summary="전체 사용자 목록", description="등록된 모든 사용자의 목록을 조회합니다.")
def api_list_users(db: Session = Depends(get_db)):
    return get_all_users(db)
