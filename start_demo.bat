@echo off
:: [V19.0 - FIX: Always install into venv explicitly using venv\Scripts\python.exe -m pip]
set FLAGS_use_mkldnn=0
set FLAGS_use_onednn=0
set FLAGS_enable_pir_api=0
set FLAGS_enable_pir_in_executor=0
set FLAGS_enable_new_executor=0
set PADDLE_INF_PIR_API=0
set PADDLE_ONEDNN_ENABLED=0

chcp 65001 >nul

echo =================================================
echo    Bank Audit Demo - Portable Launcher (V19.0)
echo =================================================

:: 1. Check Python
echo [Status] Checking Python environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [Error] Python not found.
    pause
    exit /b
)

:: 2. Setup Venv
if not exist "venv\Scripts\python.exe" (
    echo [Status] Creating virtual environment...
    python -m venv venv
)

:: 3. Install Requirements into the VENV explicitly
echo [Status] Syncing dependencies into venv...
:: This guarantees packages are installed INTO the venv, NOT into global Python
venv\Scripts\python.exe -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

:: 4. Start Backend
echo [Status] Starting analytical services...
set B_CMD=set FLAGS_use_mkldnn=0^&set FLAGS_enable_pir_api=0^&set FLAGS_enable_new_executor=0^&venv\Scripts\python.exe -m backend.main
start "BankAuditBackend" cmd /c "%B_CMD%"

:: 5. Open UI
echo [Status] Launching browser...
timeout /t 5 >nul
start http://127.0.0.1:8000/

echo =================================================
echo    READY!
echo =================================================
pause
