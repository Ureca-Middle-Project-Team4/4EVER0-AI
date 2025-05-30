from dotenv import load_dotenv
import os
from pathlib import Path

# .env 파일 경로 명시적으로 지정
dotenv_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=dotenv_path)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MYSQL_URL = os.getenv("MYSQL_URL")

# ✅ 디버그 출력
print("✅ MYSQL_URL =", MYSQL_URL)
