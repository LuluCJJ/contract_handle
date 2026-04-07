@echo off
:: [V14.0 绝命补丁：系统级全局封杀已知的 Paddle 3.3.0/3.4.0 PIR & oneDNN Bug]
set FLAGS_use_mkldnn=0
set FLAGS_use_onednn=0
set FLAGS_enable_pir_api=0
set PADDLE_INF_PIR_API=0
set PADDLE_ONEDNN_ENABLED=0

:: Explicitly set to UTF-8 for the session
chcp 65001 >nul

echo =================================================
echo    Bank Audit Demo - One-Click Launcher (V14.0)
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
:: Pass the same flags to the sub-process
start "Bank Audit Backend" cmd /k "set FLAGS_use_mkldnn=0 && set FLAGS_enable_pir_api=0 && venv\Scripts\python.exe -m backend.main"

:: 5. Open Browser
echo [Status] Opening browser...
timeout /t 5 >nul
start http://127.0.0.1:8000/

echo =================================================
echo    The system is ready! (Flags: PIR=0, MKLDNN=0)
echo    Please use the browser window.
echo    Close the black command window when done.
echo =================================================
pause
