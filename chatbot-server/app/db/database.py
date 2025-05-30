from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

MYSQL_URL = os.getenv("MYSQL_URL")  # secrets에서 가져오도록 수정

engine = create_engine(MYSQL_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# app/db/models.py
from sqlalchemy import Column, Integer, String, Text
from app.db.database import Base

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255))
    description = Column(Text)
    image_url = Column(String(512))
    detail_url = Column(String(512))
    category = Column(String(100), default="유독")
    tags = Column(Text)  # JSON string or comma-separated