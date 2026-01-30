@echo off
REM Enterprise Agent POC Startup Script
REM 企業 Agent POC 啟動腳本

echo ========================================
echo    企業 Agent POC - 啟動中...
echo ========================================

REM Activate conda environment
call conda activate enterprise-agent
if errorlevel 1 (
    echo [ERROR] 無法啟動 enterprise-agent 環境
    echo 請先執行: conda create -n enterprise-agent python=3.11
    pause
    exit /b 1
)

REM Check for .env file
if not exist ".env" (
    echo [WARNING] 未找到 .env 檔案
    echo 正在從 .env.dev 複製...
    copy .env.dev .env
    echo [INFO] 請編輯 .env 檔案設定 API Keys:
    echo   - GOOGLE_API_KEY: 用於 Gemini API
    echo   - TAVILY_API_KEY: 用於網路搜尋 (選用)
)

REM Start the UI
echo.
echo [INFO] 啟動 UI 服務...
echo [INFO] 預設帳號:
echo   - 管理員: admin / admin123
echo   - 使用者: user / user123
echo.
echo [INFO] 開啟瀏覽器: http://localhost:5050
echo.

ultrarag ui --admin

pause
