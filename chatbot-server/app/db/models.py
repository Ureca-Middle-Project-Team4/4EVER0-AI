# app/db/models.py
from sqlalchemy import Column, Integer, String, Text
from app.db.database import Base

class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = {"extend_existing": True}  # ✅ 이 줄 추가

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255))
    description = Column(Text)
    image_url = Column(String(512))
    detail_url = Column(String(512))
    category = Column(String(100), default="유독")
    tags = Column(Text)
