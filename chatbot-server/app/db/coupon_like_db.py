from app.db.database import SessionLocal
from app.db.models import CouponLike

def get_liked_brand_ids(session_id: str) -> list[int]:
    db = SessionLocal()
    try:
        result = db.query(CouponLike.brand_id).filter(CouponLike.is_liked == True).all()
        brand_ids = list({row[0] for row in result})  # 중복 제거
        return brand_ids
    finally:
        db.close()
