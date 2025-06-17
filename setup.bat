@echo off
chcp 65001 > nul
echo 🚀 LG U+ AI 챗봇 설정 시작...

REM Python 버전 확인
echo 🐍 Python 버전 확인...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python이 설치되지 않았습니다.
    echo    https://www.python.org/downloads/ 에서 다운로드하세요.
    pause
    exit /b 1
)

REM 가상환경 생성
echo 📦 가상환경 생성 중...
python -m venv venv

REM 가상환경 활성화
echo ✅ 가상환경 활성화...
call venv\Scripts\activate.bat

REM 의존성 설치 (Windows용 최적화)
echo 📚 패키지 설치 중...
python -m pip install --upgrade pip
pip install -r chatbot-server\requirements-windows.txt

REM .env 파일 확인
echo 🔧 환경변수 확인...
if not exist "chatbot-server\.env" (
    echo 📝 .env 파일 생성...
    (
        echo OPENAI_API_KEY=your_openai_api_key_here
        echo MYSQL_URL=mysql+pymysql://user:password@localhost:3306/database_name
    ) > chatbot-server\.env
    echo ⚠️  chatbot-server\.env 파일에 실제 API 키를 입력해주세요!
)

echo ✅ 설정 완료!
echo.
echo 🎯 다음 명령어로 서버를 실행하세요:
echo    venv\Scripts\activate.bat
echo    cd chatbot-server
echo    python run.py

pause