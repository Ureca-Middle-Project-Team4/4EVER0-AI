from app.db.database import SessionLocal
from app.db.models import Plan

def get_all_plans():
    db = SessionLocal()
    plans = db.query(Plan).all()
    db.close()
    return plans
