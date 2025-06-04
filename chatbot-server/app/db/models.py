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


class UBType(Base):
    __tablename__ = "ubti_types"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), unique=True, nullable=False)
    name = Column(String(50), nullable=False)
    emoji = Column(String(10))
    description = Column(Text, nullable=False)
