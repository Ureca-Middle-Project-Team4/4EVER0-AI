@echo off
chcp 65001 > nul
echo 🚀 LG U+ AI 챗봇 설정 시작...

REM 관리자 권한 확인
net session >nul 2>&1
if %errorLevel% == 0 (
    echo ✅ 관리자 권한으로 실행 중
) else (
    echo ⚠️  관리자 권한이 없습니다. 일부 패키지 설치 시 오류가 발생할 수 있습니다.
    echo.
)

REM Python 버전 확인
echo 🐍 Python 버전 확인...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python이 설치되지 않았습니다.
    echo    https://www.python.org/downloads/ 에서 다운로드하세요.
    echo    ⚠️  설치 시 "Add Python to PATH" 옵션을 체크하세요!
    pause
    exit /b 1
)

REM 가상환경 생성
echo 📦 가상환경 생성 중...
if exist "venv" (
    echo ⚠️  기존 가상환경이 있습니다. 삭제 후 재생성합니다.
    rmdir /s /q venv 2>nul
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

REM pip 업그레이드 (사용자 모드로)
echo 🔄 pip 업그레이드...
python -m pip install --upgrade pip --user

REM 의존성 파일 확인 및 설치 (사용자 모드로)
echo 📚 패키지 설치 중...
if exist "chatbot-server\requirements-windows.txt" (
    echo 📦 Windows용 requirements 파일 발견
    pip install -r chatbot-server\requirements-windows.txt --user
) else if exist "chatbot-server\requirements.txt" (
    echo 📦 일반 requirements 파일 사용
    pip install -r chatbot-server\requirements.txt --user
) else (
    echo ❌ requirements 파일을 찾을 수 없습니다.
    pause
    exit /b 1
)

REM 설치 실패 시 재시도
if %errorlevel% neq 0 (
    echo.
    echo ⚠️  일부 패키지 설치에 실패했습니다. 개별 설치를 시도합니다...
    echo.

    REM 핵심 패키지만 먼저 설치
    pip install fastapi uvicorn python-dotenv openai langchain --user
    pip install pydantic sqlalchemy redis requests --user
    pip install numpy scikit-learn --user

    echo.
    echo ✅ 핵심 패키지 설치 완료! 일부 선택적 패키지는 나중에 설치할 수 있습니다.
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

echo.
echo ✅ 설정 완료!
echo.
echo 🎯 다음으로 run.bat을 실행하여 서버를 시작하세요!
echo    또는 수동으로 실행하려면:
echo    1. venv\Scripts\activate.bat
echo    2. cd chatbot-server
echo    3. python run.py
echo.

pause