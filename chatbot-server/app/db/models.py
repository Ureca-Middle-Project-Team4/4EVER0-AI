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

class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    price = Column(String(20), nullable=False)
    data = Column(String(50), nullable=True)
    voice = Column(String(50), nullable=True)
    description = Column(String(255), nullable=True)
