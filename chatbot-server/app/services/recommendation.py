from app.db.database import SessionLocal
from app.db.models import Subscription
from app.schemas.recommend import UserProfile

RULES = {
    ("10대", "OTT"): ["넷플릭스", "유튜브"],
    ("20대", "웹툰"): ["웹툰", "도서"],
    ("30대", "카페"): ["디저트", "편의점"],
    ("애완견", "배달"): ["펫"]
}

def get_recommendations(user: UserProfile):
    db = SessionLocal()
    keywords = set(user.interests + user.time_usage + [user.age_group])

    result = db.query(Subscription).all()
    db.close()

    def matches(sub):
        return any(keyword in sub.description or keyword in (sub.tags or "") for keyword in keywords)

    return [
        {
            "title": s.title,
            "description": s.description,
            "image_url": s.image_url,
            "detail_url": s.detail_url
        }
        for s in result if matches(s)
    ]
