@echo off
REM UltraRAG Cloud Run Deployment Script for Windows
REM Usage: deploy.bat

echo ========================================
echo    UltraRAG Cloud Run Deployment
echo ========================================

REM Check if gcloud is installed
where gcloud >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Error: gcloud CLI is not installed
    echo Please install from: https://cloud.google.com/sdk/docs/install
    exit /b 1
)

REM Get current project
for /f "tokens=*" %%i in ('gcloud config get-value project 2^>nul') do set PROJECT_ID=%%i
if "%PROJECT_ID%"=="" (
    echo Error: No GCP project set
    echo Run: gcloud config set project YOUR_PROJECT_ID
    exit /b 1
)

echo Current Project: %PROJECT_ID%

REM Check for required environment variables
if "%GOOGLE_API_KEY%"=="" (
    echo Error: GOOGLE_API_KEY not set
    echo Run: set GOOGLE_API_KEY=your_api_key
    exit /b 1
)

REM Set defaults
if "%REGION%"=="" set REGION=us-west1
echo Region: %REGION%

REM Navigate to project root
cd /d "%~dp0..\.."

REM Enable required APIs
echo Enabling required APIs...
call gcloud services enable cloudbuild.googleapis.com
call gcloud services enable run.googleapis.com
call gcloud services enable containerregistry.googleapis.com

REM Build and deploy using Cloud Build
echo Building and deploying...
call gcloud builds submit ^
    --config docker/cloudrun/cloudbuild.yaml ^
    --substitutions="_REGION=%REGION%,_GOOGLE_API_KEY=%GOOGLE_API_KEY%,_MILVUS_URI=%MILVUS_URI%,_MILVUS_TOKEN=%MILVUS_TOKEN%"

REM Get the service URL
for /f "tokens=*" %%i in ('gcloud run services describe ultrarag --region=%REGION% --format="value(status.url)"') do set SERVICE_URL=%%i

echo ========================================
echo    Deployment Complete!
echo ========================================
echo Service URL: %SERVICE_URL%
echo.
echo To view logs:
echo gcloud run services logs read ultrarag --region=%REGION%

pause
