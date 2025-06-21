from typing import Optional, List
from sqlalchemy.orm import Session
from app.db.models import User

def get_user(db: Session, user_id: int) -> Optional[User]:
    """ID로 사용자 조회"""
    return db.query(User).filter(User.id == user_id).first()

def get_all_users(db: Session) -> List[User]:
    """모든 사용자 조회"""
    return db.query(User).all()
