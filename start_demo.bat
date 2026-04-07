@echo off
:: Explicitly set to UTF-8 for the session
chcp 65001 >nul

echo =================================================
echo    Bank Audit Demo - One-Click Launcher
echo =================================================

:: 1. Check Python
echo [Status] Checking Python environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [Error] Python not found. Please install Python.
    pause
    exit /b
)

:: 2. Create Virtual Env
if not exist "venv\Scripts\python.exe" (
    echo [Status] First time setup: Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [Error] Failed to create virtual environment.
        pause
        exit /b
    )
)

:: 3. Install Dependencies
echo [Status] Checking and installing dependencies...
call venv\Scripts\activate.bat
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

:: 4. Start Server
echo [Status] Starting Backend Service...
start "Bank Audit Backend" cmd /k "venv\Scripts\python.exe -m backend.main"

:: 5. Open Browser
echo [Status] Opening browser...
timeout /t 5 >nul
start http://127.0.0.1:8000/

echo =================================================
echo    The system is ready!
echo    Please use the browser window.
echo    Close the black command window when done.
echo =================================================
pause
