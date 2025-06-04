from app.db.database import SessionLocal
from app.db.models import UBType

def get_all_ubti_types():
    db = SessionLocal()
    try:
        return db.query(UBType).all()
    finally:
        db.close()
