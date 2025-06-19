#!/bin/bash

echo "🚀 LG U+ AI 챗봇 서버 시작..."

# 가상환경 확인
if [ ! -d "venv" ]; then
    echo "❌ 가상환경이 없습니다. ./setup.sh를 먼저 실행해주세요."
    exit 1
fi

# chatbot-server 디렉토리 확인
if [ ! -d "chatbot-server" ]; then
    echo "❌ chatbot-server 디렉토리가 없습니다."
    echo "   프로젝트 루트 디렉토리에서 실행해주세요."
    exit 1
fi

# 가상환경 활성화
echo "✅ 가상환경 활성화..."
source venv/bin/activate

# Redis 확인 및 시작
echo "🔄 Redis 서버 확인 중..."
if command -v redis-server &> /dev/null; then
    if ! pgrep -x "redis-server" > /dev/null; then
        echo "📡 Redis 서버 시작..."
        redis-server --daemonize yes
        sleep 2
    else
        echo "✅ Redis 서버가 이미 실행 중입니다."
    fi
else
    echo "⚠️  Redis가 설치되지 않았습니다. 일부 기능이 제한될 수 있습니다."
fi

# 환경변수 확인
if [ ! -f "chatbot-server/.env" ]; then
    echo "❌ .env 파일이 없습니다. ./setup.sh를 먼저 실행해주세요."
    exit 1
fi

# 서버 실행
echo "🎉 챗봇 서버 시작!"
echo "📍 서버 주소: http://localhost:8000"
echo "🛑 서버를 종료하려면 Ctrl+C를 누르세요."
cd chatbot-server
python run.py

echo ""
echo "🔄 서버가 종료되었습니다."