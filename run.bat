@echo off
chcp 65001 > nul
echo 🚀 LG U+ AI 챗봇 서버 시작...

REM 가상환경 확인
if not exist "venv" (
    echo ❌ 가상환경이 없습니다. setup.bat을 먼저 실행해주세요.
    pause
    exit /b 1
)

REM chatbot-server 디렉토리 확인
if not exist "chatbot-server" (
    echo ❌ chatbot-server 디렉토리가 없습니다.
    echo    프로젝트 루트 디렉토리에서 실행해주세요.
    pause
    exit /b 1
)

REM 가상환경 활성화
echo ✅ 가상환경 활성화...
call venv\Scripts\activate.bat

REM 환경변수 확인
if not exist "chatbot-server\.env" (
    echo ❌ .env 파일이 없습니다. setup.bat을 먼저 실행해주세요.
    pause
    exit /b 1
)

REM 서버 실행
echo 🎉 챗봇 서버 시작!
echo 📍 서버 주소: http://localhost:8000
echo 🛑 서버를 종료하려면 Ctrl+C를 누르세요.
cd chatbot-server
python run.py

echo.
echo 🔄 서버가 종료되었습니다.
pause