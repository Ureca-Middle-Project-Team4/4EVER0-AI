from app.db.database import SessionLocal
from app.db.models import Subscription

def get_products_from_db():
    db = SessionLocal()
    try:
        return db.query(Subscription).all()
    finally:
        db.close()
