#!/bin/bash

echo "🚀 LG U+ AI 챗봇 서버 시작..."

# 가상환경 활성화 확인
if [ ! -d "venv" ]; then
    echo "❌ 가상환경이 없습니다. setup.sh를 먼저 실행해주세요."
    exit 1
fi

# 가상환경 활성화
source venv/bin/activate

# Redis 시작
echo "🔄 Redis 서버 확인 중..."
if ! pgrep -x "redis-server" > /dev/null; then
    echo "📡 Redis 서버 시작..."
    redis-server --daemonize yes
fi

# 환경변수 확인
if [ ! -f "chatbot-server/.env" ]; then
    echo "❌ .env 파일이 없습니다."
    exit 1
fi

# 서버 실행
echo "🎉 챗봇 서버 시작!"
cd chatbot-server
python run.py