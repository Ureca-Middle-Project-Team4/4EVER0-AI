#!/bin/bash

echo "🚀 LG U+ AI 챗봇 설정 시작..."

# Python 버전 확인
echo "🐍 Python 버전 확인..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3가 설치되지 않았습니다."
    echo "   macOS: brew install python3"
    echo "   Ubuntu: sudo apt-get install python3 python3-pip python3-venv"
    exit 1
fi

python3 --version

# 기존 가상환경 확인
if [ -d "venv" ]; then
    echo "⚠️  기존 가상환경이 있습니다. 삭제 후 재생성합니다."
    rm -rf venv
fi

# 가상환경 생성
echo "📦 가상환경 생성 중..."
python3 -m venv venv

# 가상환경 활성화
echo "✅ 가상환경 활성화..."
source venv/bin/activate

# chatbot-server 디렉토리 확인
if [ ! -d "chatbot-server" ]; then
    echo "❌ chatbot-server 디렉토리가 없습니다."
    echo "   프로젝트 루트 디렉토리에서 실행해주세요."
    exit 1
fi

# 의존성 설치
echo "📚 패키지 설치 중..."
pip install --upgrade pip

if [ -f "chatbot-server/requirements.txt" ]; then
    pip install -r chatbot-server/requirements.txt
else
    echo "❌ requirements.txt 파일을 찾을 수 없습니다."
    exit 1
fi

# Redis 설치 확인
echo "🔍 Redis 확인 중..."
if ! command -v redis-server &> /dev/null; then
    echo "⚠️  Redis가 설치되지 않았습니다."
    echo "   macOS: brew install redis"
    echo "   Ubuntu: sudo apt-get install redis-server"
    echo "   CentOS/RHEL: sudo yum install redis"
fi

# .env 파일 확인
echo "🔧 환경변수 확인..."
if [ ! -f "chatbot-server/.env" ]; then
    echo "📝 .env 파일 생성..."
    cat > chatbot-server/.env << 'EOF'
OPENAI_API_KEY=your_openai_api_key_here
MYSQL_URL=mysql+pymysql://user:password@localhost:3306/database_name
EOF
    echo "⚠️  chatbot-server/.env 파일에 실제 API 키를 입력해주세요!"
fi

echo "✅ 설정 완료!"
echo ""
echo "🎯 다음으로 ./run.sh를 실행하여 서버를 시작하세요!"
echo "   또는 수동으로 실행하려면:"
echo "   1. source venv/bin/activate"
echo "   2. cd chatbot-server"
echo "   3. python run.py"