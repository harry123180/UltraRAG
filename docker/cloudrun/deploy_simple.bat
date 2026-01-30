@echo off
REM UltraRAG Cloud Run Simple Deployment Script
REM Usage: deploy_simple.bat

echo ========================================
echo    UltraRAG Cloud Run Deployment
echo ========================================

REM Load environment variables from .env.cloudrun
for /f "tokens=1,2 delims==" %%a in ('type "%~dp0.env.cloudrun" ^| findstr /v "^#" ^| findstr /v "^$"') do (
    set "%%a=%%b"
)

echo.
echo Loaded configuration:
echo   REGION: %REGION%
echo   MILVUS_URI: %MILVUS_URI%
echo   GOOGLE_API_KEY: %GOOGLE_API_KEY:~0,10%...
echo.

REM Check if gcloud is installed
where gcloud >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Error: gcloud CLI is not installed
    echo Please install from: https://cloud.google.com/sdk/docs/install
    pause
    exit /b 1
)

REM Get current project
for /f "tokens=*" %%i in ('gcloud config get-value project 2^>nul') do set PROJECT_ID=%%i
if "%PROJECT_ID%"=="" (
    echo Error: No GCP project set
    echo Run: gcloud config set project YOUR_PROJECT_ID
    pause
    exit /b 1
)

echo GCP Project: %PROJECT_ID%
echo.

REM Confirm deployment
set /p CONFIRM="Proceed with deployment? (y/n): "
if /i not "%CONFIRM%"=="y" (
    echo Deployment cancelled.
    pause
    exit /b 0
)

REM Navigate to project root
cd /d "%~dp0..\.."

REM Enable required APIs
echo.
echo [1/3] Enabling required APIs...
call gcloud services enable cloudbuild.googleapis.com
call gcloud services enable run.googleapis.com
call gcloud services enable containerregistry.googleapis.com

REM Build and deploy
echo.
echo [2/3] Building container image...
echo This may take 5-10 minutes on first build...
echo.

call gcloud builds submit ^
    --config docker/cloudrun/cloudbuild.yaml ^
    --substitutions="_REGION=%REGION%,_GOOGLE_API_KEY=%GOOGLE_API_KEY%,_MILVUS_URI=%MILVUS_URI%,_MILVUS_TOKEN=%MILVUS_TOKEN%"

if %ERRORLEVEL% neq 0 (
    echo.
    echo Build failed! Check the error messages above.
    pause
    exit /b 1
)

REM Get the service URL
echo.
echo [3/3] Getting service URL...
for /f "tokens=*" %%i in ('gcloud run services describe ultrarag --region=%REGION% --format="value(status.url)" 2^>nul') do set SERVICE_URL=%%i

echo.
echo ========================================
echo    Deployment Complete!
echo ========================================
echo.
echo Service URL: %SERVICE_URL%
echo.
echo Next steps:
echo   1. Open %SERVICE_URL% in your browser
echo   2. Upload knowledge base documents
echo   3. Start chatting!
echo.
echo To view logs:
echo   gcloud run services logs read ultrarag --region=%REGION%
echo.

pause
