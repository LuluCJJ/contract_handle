@echo off
:: [V17.0 修正：修复启动命令语法 & 环境变量注入方式]
set FLAGS_use_mkldnn=0
set FLAGS_use_onednn=0
set FLAGS_enable_pir_api=0
set FLAGS_enable_pir_in_executor=0
set FLAGS_enable_new_executor=0
set PADDLE_INF_PIR_API=0
set PADDLE_ONEDNN_ENABLED=0

:: 设置字符编码为 UTF-8
chcp 65001 >nul

echo =================================================
echo    Bank Audit Demo - One-Click Launcher (V17.0)
echo =================================================

:: 1. 检查 Python 环境
echo [状态] 正在检查 Python 3...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python，请首先安装环境。
    pause
    exit /b
)

:: 2. 加载虚拟环境
if not exist "venv\Scripts\python.exe" (
    echo [状态] 首次运行：正在创建虚拟环境...
    python -m venv venv
)

:: 3. 激活环境并更新依赖
echo [状态] 正在同步依赖项...
call venv\Scripts\activate.bat
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

:: 4. 启动后端服务
echo [状态] 正在启动后台分析服务...
:: 采用更稳妥的 start 传参方式，避免 && 导致命令截断
start "BankAuditBackend" cmd /c "set FLAGS_use_mkldnn=0& set FLAGS_enable_pir_api=0& set FLAGS_enable_new_executor=0& venv\Scripts\python.exe -m backend.main"

:: 5. 跳转浏览器
echo [状态] 正在开启 Web 控制台...
timeout /t 5 >nul
start http://127.0.0.1:8000/

echo =================================================
echo    系统初始化完毕！ (PIR=OFF, oneDNN=OFF)
echo    请在浏览器窗口中操作，完成后关闭黑色窗口即可。
echo =================================================
pause
