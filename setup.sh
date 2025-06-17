# setup.sh (Linux/macOS용)
#!/bin/bash

echo "🚀 LG U+ AI 챗봇 설정 시작..."

# Python 버전 확인
echo "🐍 Python 버전 확인..."
python3 --version || { echo "❌ Python3가 설치되지 않았습니다."; exit 1; }

# 가상환경 생성
echo "📦 가상환경 생성 중..."
python3 -m venv venv

# 가상환경 활성화
echo "✅ 가상환경 활성화..."
source venv/bin/activate

# 의존성 설치
echo "📚 패키지 설치 중..."
pip install --upgrade pip
pip install -r chatbot-server/requirements.txt

# Redis 설치 확인
echo "🔍 Redis 확인 중..."
if ! command -v redis-server &> /dev/null; then
    echo "⚠️  Redis가 설치되지 않았습니다."
    echo "   macOS: brew install redis"
    echo "   Ubuntu: sudo apt-get install redis-server"
fi

# .env 파일 확인
echo "🔧 환경변수 확인..."
if [ ! -f "chatbot-server/.env" ]; then
    echo "📝 .env 파일 생성..."
    cat > chatbot-server/.env << EOF
OPENAI_API_KEY=your_openai_api_key_here
MYSQL_URL=mysql+pymysql://user:password@localhost:3306/database_name
EOF
    echo "⚠️  chatbot-server/.env 파일에 실제 API 키를 입력해주세요!"
fi

echo "✅ 설정 완료!"
echo ""
echo "🎯 다음 명령어로 서버를 실행하세요:"
echo "   source venv/bin/activate"
echo "   cd chatbot-server"
echo "   python run.py"