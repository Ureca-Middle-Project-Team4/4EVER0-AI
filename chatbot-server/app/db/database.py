from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

MYSQL_URL = os.getenv("MYSQL_URL")
if not MYSQL_URL:
    raise ValueError("❌ MYSQL_URL 환경변수가 설정되지 않았습니다.")

engine = create_engine(MYSQL_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()