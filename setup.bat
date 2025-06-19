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
if exist "venv" (
    echo ⚠️  기존 가상환경이 있습니다. 삭제 후 재생성합니다.
    rmdir /s /q venv
)
python -m venv venv

REM 가상환경 활성화
echo ✅ 가상환경 활성화...
call venv\Scripts\activate.bat

REM chatbot-server 디렉토리 확인
if not exist "chatbot-server" (
    echo ❌ chatbot-server 디렉토리가 없습니다.
    echo    프로젝트 루트 디렉토리에서 실행해주세요.
    pause
    exit /b 1
)

REM 의존성 파일 확인 및 설치
echo 📚 패키지 설치 중...
python -m pip install --upgrade pip

if exist "chatbot-server\requirements-windows.txt" (
    pip install -r chatbot-server\requirements-windows.txt
) else if exist "chatbot-server\requirements.txt" (
    pip install -r chatbot-server\requirements.txt
) else (
    echo ❌ requirements 파일을 찾을 수 없습니다.
    pause
    exit /b 1
)

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
echo 🎯 다음으로 run.bat을 실행하여 서버를 시작하세요!
echo    또는 수동으로 실행하려면:
echo    1. venv\Scripts\activate.bat
echo    2. cd chatbot-server
echo    3. python run.py

pause