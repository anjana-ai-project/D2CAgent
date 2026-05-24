@echo off
echo ============================================
echo  D2CAgent — AI Agent Orchestration Platform
echo  Kreactive Toys Demo Setup
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.11+
    pause
    exit /b 1
)

:: Check Node
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js not found. Install Node.js 18+
    pause
    exit /b 1
)

echo [1/6] Creating Python virtual environment...
python -m venv venv
call venv\Scripts\activate.bat

echo [2/6] Installing Python dependencies...
pip install -r requirements.txt -q
if errorlevel 1 (
    echo ERROR: Failed to install Python dependencies
    pause
    exit /b 1
)

echo [3/6] Installing frontend dependencies...
cd frontend
npm install -q
cd ..

echo [4/6] Seeding database with Kreactive Toys demo data...
python -m backend.database.seed
if errorlevel 1 (
    echo ERROR: Database seeding failed
    pause
    exit /b 1
)

echo [5/6] Seeding ChromaDB product catalog...
python -m backend.database.seed_chroma
if errorlevel 1 (
    echo ERROR: ChromaDB seeding failed
    pause
    exit /b 1
)

echo [6/6] Running tests to verify setup...
pytest tests/ -q
if errorlevel 1 (
    echo WARNING: Some tests failed — check test_results.txt
)

echo.
echo ============================================
echo  Setup Complete!
echo ============================================
echo.
echo Next steps:
echo.
echo 1. Add your API keys to .env file:
echo    GROQ_API_KEY=your_groq_key
echo    TELEGRAM_BOT_TOKEN=your_telegram_token
echo.
echo 2. Start ngrok in a new terminal:
echo    ngrok http 8000
echo.
echo 3. Start the backend:
echo    venv\Scripts\activate
echo    python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
echo.
echo 4. Start the frontend in another terminal:
echo    cd frontend
echo    npm run dev
echo.
echo 5. Set Telegram webhook via browser:
echo    http://localhost:8000/docs
echo    POST /setup/webhook with your ngrok URL
echo.
echo 6. Open the dashboard:
echo    http://localhost:5173
echo.
echo 7. Message your Telegram bot:
echo    @Kreactive_Toys_Bot
echo.
pause