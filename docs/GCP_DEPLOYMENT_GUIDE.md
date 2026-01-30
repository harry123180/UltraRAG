# UltraRAG GCP Cloud Run 部署指南

## 架構概覽

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   Cloud Run     │─────▶│   Gemini API    │      │  Milvus Cloud   │
│   (UltraRAG)    │      │   (Google AI)   │      │  (Zilliz)       │
│   us-west1      │      │                 │      │  us-west1       │
└─────────────────┘      └─────────────────┘      └─────────────────┘
```

## 前置需求

### 1. 安裝 Google Cloud SDK

**Windows:**
- 下載: https://cloud.google.com/sdk/docs/install
- 或使用 winget: `winget install Google.CloudSDK`

**驗證安裝:**
```bash
gcloud --version
```

### 2. GCP 專案設定

```bash
# 登入 Google Cloud
gcloud auth login

# 設定專案
gcloud config set project YOUR_PROJECT_ID

# 確認設定
gcloud config get-value project
```

### 3. 申請 Milvus Cloud (Zilliz)

1. 前往 https://cloud.zilliz.com/
2. 註冊/登入帳號
3. 創建 Free Tier Cluster:
   - Plan: **Free**
   - Cloud Provider: **GCP**
   - Region: **gcp-us-west1** (免費版唯一選項)
   - Cluster Name: 自訂名稱

4. 記錄以下資訊:
   - **Public Endpoint**: `https://in03-xxx.serverless.gcp-us-west1.cloud.zilliz.com`
   - **Username**: `db_xxx`
   - **Password**: `xxx`
   - **Token 格式**: `username:password`

### 4. 準備 Gemini API Key

1. 前往 https://aistudio.google.com/
2. 創建 API Key
3. 記錄 **GOOGLE_API_KEY**

---

## 部署步驟

### Step 1: 啟用 GCP API

```bash
gcloud services enable cloudbuild.googleapis.com run.googleapis.com containerregistry.googleapis.com
```

### Step 2: 建置 Docker 映像

```bash
cd D:\AWORKSPACE\Github\UltraRAG
gcloud builds submit --config cloudbuild.yaml
```

**預計時間:** 首次建置約 2-5 分鐘

### Step 3: 部署到 Cloud Run

```bash
gcloud run deploy ultrarag \
  --image gcr.io/YOUR_PROJECT_ID/ultrarag:latest \
  --region us-west1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --max-instances 10 \
  --set-env-vars "GOOGLE_API_KEY=xxx,MILVUS_URI=xxx,MILVUS_TOKEN=xxx"
```

**環境變數說明:**
| 變數 | 說明 | 範例 |
|------|------|------|
| GOOGLE_API_KEY | Gemini API Key | `AIzaSy...` |
| MILVUS_URI | Milvus Cloud Endpoint | `https://in03-xxx.serverless.gcp-us-west1.cloud.zilliz.com` |
| MILVUS_TOKEN | Milvus 認證 (user:password) | `db_xxx:password` |

### Step 4: 驗證部署

```bash
# 檢查健康狀態
curl https://YOUR_SERVICE_URL/api/health

# 預期回應
{"service":"ultrarag","status":"healthy"}
```

---

## 常用操作命令

### 查看服務狀態

```bash
gcloud run services describe ultrarag --region us-west1
```

### 查看日誌

```bash
# 最近日誌
gcloud run services logs read ultrarag --region us-west1 --limit 50

# 即時日誌
gcloud run services logs tail ultrarag --region us-west1
```

### 更新部署

```bash
# 重新建置並推送
gcloud builds submit --config cloudbuild.yaml

# 更新服務 (使用新映像)
gcloud run deploy ultrarag --image gcr.io/YOUR_PROJECT_ID/ultrarag:latest --region us-west1
```

### 更新環境變數

```bash
gcloud run services update ultrarag \
  --region us-west1 \
  --set-env-vars "GOOGLE_API_KEY=new_key"
```

### 擴展配置

```bash
# 設定最小實例 (避免冷啟動)
gcloud run services update ultrarag --min-instances 1 --region us-west1

# 調整資源
gcloud run services update ultrarag --memory 4Gi --cpu 4 --region us-west1
```

### 刪除服務

```bash
gcloud run services delete ultrarag --region us-west1
```

---

## 檔案結構

```
docker/cloudrun/
├── Dockerfile           # 容器映像定義
├── .dockerignore        # 建置時排除的檔案
├── cloudbuild.yaml      # Cloud Build 配置 (已棄用，使用根目錄的)
├── .env.cloudrun        # 環境變數範本 (勿提交)
├── deploy.bat           # Windows 部署腳本
├── deploy.sh            # Linux/Mac 部署腳本
└── README.md            # 部署說明

cloudbuild.yaml          # 根目錄的 Cloud Build 配置 (主要使用)
```

---

## 費用估算

| 服務 | 免費額度 | 超出費用 |
|------|----------|----------|
| Cloud Run | 2M requests/月, 360K GB-seconds | ~$0.00002400/GB-second |
| Cloud Build | 120 build-minutes/天 | ~$0.003/minute |
| Container Registry | 0.5 GB | ~$0.026/GB/月 |
| Milvus Cloud (Free) | 5GB 向量儲存 | 依方案計費 |
| Gemini API | 免費額度 | 依用量計費 |

**預估月費 (低流量):** $0 - $50

---

## 故障排除

### 問題: 503 Service Unavailable

**可能原因:** 冷啟動中或應用程式錯誤

**解決方案:**
```bash
# 查看日誌
gcloud run services logs read ultrarag --region us-west1 --limit 50

# 設定最小實例避免冷啟動
gcloud run services update ultrarag --min-instances 1 --region us-west1
```

### 問題: Failed to find attribute 'app'

**原因:** Flask 應用程式未正確導出

**解決方案:** 確保 `ui/backend/app.py` 最後有:
```python
# Create app instance for gunicorn (production)
app = create_app()
```

### 問題: Milvus 連接失敗

**檢查項目:**
1. MILVUS_URI 格式是否正確
2. MILVUS_TOKEN 是否為 `username:password` 格式
3. Milvus Cloud cluster 是否在運行中

### 問題: 建置失敗

```bash
# 查看建置日誌
gcloud builds list --limit 5

# 查看特定建置詳情
gcloud builds describe BUILD_ID
```

---

## 快速部署腳本

### Windows (deploy_simple.bat)

```batch
@echo off
REM 載入環境變數
for /f "tokens=1,2 delims==" %%a in ('type "docker\cloudrun\.env.cloudrun"') do set "%%a=%%b"

REM 建置並部署
gcloud builds submit --config cloudbuild.yaml
gcloud run deploy ultrarag --image gcr.io/%PROJECT_ID%/ultrarag:latest --region %REGION% --set-env-vars "GOOGLE_API_KEY=%GOOGLE_API_KEY%,MILVUS_URI=%MILVUS_URI%,MILVUS_TOKEN=%MILVUS_TOKEN%"
```

### 一鍵更新部署

```bash
gcloud builds submit --config cloudbuild.yaml && gcloud run deploy ultrarag --image gcr.io/$(gcloud config get-value project)/ultrarag:latest --region us-west1
```

---

## 當前部署資訊

| 項目 | 值 |
|------|-----|
| **Project ID** | my-website-harry123 |
| **Service URL** | https://ultrarag-556560931446.us-west1.run.app |
| **Region** | us-west1 (Oregon) |
| **Image** | gcr.io/my-website-harry123/ultrarag:latest |
| **Memory** | 2GB |
| **CPU** | 2 |
| **Max Instances** | 10 |

---

## 相關文件

- [Cloud Run 文檔](https://cloud.google.com/run/docs)
- [Cloud Build 文檔](https://cloud.google.com/build/docs)
- [Milvus Cloud 文檔](https://docs.zilliz.com/)
- [Gemini API 文檔](https://ai.google.dev/docs)
