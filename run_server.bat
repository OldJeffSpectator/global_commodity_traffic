@echo off
REM Global Commodity Traffic - Start both backend and frontend servers
REM Backend: http://localhost:16667
REM Frontend: http://localhost:16668

REM ===== UN Comtrade API Key (free tier) =====
REM Get yours at https://comtradedeveloper.un.org/
set COMTRADE_API_KEY=3bf9dc83d1834c5f9f262476104a238e

echo ============================================
echo  Global Commodity Traffic - Server Launcher
echo ============================================
echo.
echo Backend API:  http://localhost:16667
echo Frontend UI:  http://localhost:16668
echo.

REM Check if Python venv exists
if not exist "backend\.venv\Scripts\activate.bat" (
    echo [Setup] Creating Python virtual environment...
    cd backend
    python -m venv .venv
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt
    cd ..
) 

REM Check if node_modules exists
if not exist "frontend\node_modules" (
    echo [Setup] Installing frontend dependencies...
    cd frontend
    call npm install
    cd ..
)

REM Initialize DB if not exists
if not exist "backend\data\trade.db" (
    echo [Setup] Initializing database...
    cd backend
    call .venv\Scripts\activate.bat
    python -c "from app.db.seed import init_db; init_db()"
    python -m app.db.seed_demo_trades
    cd ..
)

REM Clear proxy for backend
set HTTP_PROXY=
set HTTPS_PROXY=
set http_proxy=
set https_proxy=
set NO_PROXY=*

echo.
echo [Starting] Backend server on port 16667...
start "GCT_Backend" /min cmd /c "cd /d %~dp0backend && .venv\Scripts\activate.bat && uvicorn app.main:app --host 0.0.0.0 --port 16667"

REM Wait for backend to start
timeout /t 3 /nobreak > nul

echo [Starting] Frontend dev server on port 16668...
start "GCT_Frontend" /min cmd /c "set PATH=C:\Program Files\nodejs;%PATH% && cd /d %~dp0frontend && npm run dev"

echo.
echo ============================================
echo  Servers started! Open http://localhost:16668
echo  Press any key to stop both servers...
echo ============================================
pause > nul

REM Kill servers by port - finds the exact PID listening on each port
echo Stopping servers...
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":16667.*LISTENING"') do (
    taskkill /pid %%a /f /t > nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":16668.*LISTENING"') do (
    taskkill /pid %%a /f /t > nul 2>&1
)
echo Servers stopped.
