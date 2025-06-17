@echo off
chcp 65001 > nul
echo 🚀 LG U+ AI 챗봇 서버 시작...

REM 가상환경 확인
if not exist "venv" (
    echo ❌ 가상환경이 없습니다. setup.bat을 먼저 실행해주세요.
    pause
    exit /b 1
)

REM 가상환경 활성화
call venv\Scripts\activate.bat

REM 환경변수 확인
if not exist "chatbot-server\.env" (
    echo ❌ .env 파일이 없습니다.
    pause
    exit /b 1
)

REM 서버 실행
echo 🎉 챗봇 서버 시작!
cd chatbot-server
python run.py