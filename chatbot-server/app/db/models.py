from sqlalchemy import Column, Integer, String, Text, Enum, ForeignKey, Boolean, DateTime
from app.db.database import Base
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))  # 한국 시간대 정의

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

class CouponLike(Base):
    __tablename__ = "coupon_likes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    coupon_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)
    brand_id = Column(Integer, nullable=False)
    is_liked = Column(Boolean, nullable=False, default=False)
#     created_at = Column(DateTime, default=lambda: datetime.now(KST))

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=True)
    email = Column(String(255), nullable=True)
    phone_number = Column(String(20), nullable=True)
    current_plan_id = Column(Integer, ForeignKey("plans.id"))
    remaining_data = Column(Integer, default=0)  # MB 단위
    remaining_share_data = Column(Integer, default=0)
    remaining_voice = Column(Integer, default=0)  # 분 단위
    remaining_sms = Column(Integer, default=0)
    last_updated = Column(DateTime, default=lambda: datetime.now(KST))

