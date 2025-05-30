from sqlalchemy import Column, Integer, String, Text
from app.db.database import Base

class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    image_url = Column(String(512))
    detail_url = Column(String(512))
    category = Column(String(100), default="유독")
    price = Column(String(50))
