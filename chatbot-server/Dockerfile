FROM python:3.10-slim

WORKDIR /app

# 패키지 최소화
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    --no-install-recommends && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# requirements.txt 복사 및 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 실제 코드 복사
COPY . .

# FastAPI는 8000 포트 사용
EXPOSE 8000

# worker 수 제한
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]