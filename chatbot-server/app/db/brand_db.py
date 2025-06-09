from app.db.database import SessionLocal
from app.db.models import Brand

def get_life_brands_from_db():
    db = SessionLocal()
    try:
        return db.query(Brand).all()
    finally:
        db.close()
