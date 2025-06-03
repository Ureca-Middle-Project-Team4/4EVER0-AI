from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
from pathlib import Path

# ✅ .env 파일을 명시적으로 로드
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

MYSQL_URL = os.getenv("MYSQL_URL")
if not MYSQL_URL:
    raise ValueError("❌ MYSQL_URL 환경변수가 설정되지 않았습니다.")

engine = create_engine(MYSQL_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
