from sqlalchemy import Column, Integer, String, Text, Enum, ForeignKey
from app.db.database import Base

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    image_url = Column(Text, nullable=False)
    category = Column(String(100), nullable=False)
    price = Column(Integer, nullable=False)

class Brand(Base):
    __tablename__ = "brands"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    image_url = Column(Text, nullable=True)
    description = Column(Text, nullable=True)

class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    price = Column(Integer, nullable=False)
    description = Column(Text, nullable=False)
    data = Column(String(50), nullable=True)
    speed = Column(String(50), nullable=True)
    share_data = Column(String(50), nullable=True)
    voice = Column(String(50), nullable=True)
    sms = Column(String(50), nullable=True, default="기본제공")


class UBType(Base):
    __tablename__ = "ubti_types"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code = Column(String(10), unique=True, nullable=False)
    name = Column(String(50), nullable=False)
    emoji = Column(String(10))
    description = Column(Text, nullable=False)
