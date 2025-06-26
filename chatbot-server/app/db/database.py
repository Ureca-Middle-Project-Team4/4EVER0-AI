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

engine = create_engine(
    MYSQL_URL,
    pool_size=5,         # 동시에 유지할 수 있는 연결 수
    max_overflow=0,      # 초과 연결 금지
    pool_recycle=1800,   # 오래된 커넥션 재사용
    pool_pre_ping=True,  # 커넥션 살아있는지 확인
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
