FROM python:3.10-slim

WORKDIR /app

# 시스템 패키지 및 python 의존성 설치 (MySQL 커넥터 등)
RUN apt-get update && apt-get install -y gcc default-libmysqlclient-dev

# requirements.txt 복사 및 패키지 설치
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# 실제 코드 복사
COPY . .

# FastAPI는 8000 포트 사용
EXPOSE 8000

# 실행 명령
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
