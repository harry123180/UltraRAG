# UltraRAG Cloud Run 部署指南

## 架構圖

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   Cloud Run     │─────▶│   Gemini API    │      │  Milvus Cloud   │
│   (UltraRAG)    │      │   (Google AI)   │      │  (向量數據庫)    │
└─────────────────┘      └─────────────────┘      └─────────────────┘
        │                                                  │
        └──────────────────────────────────────────────────┘
```

## 部署前準備

### 1. 申請 Milvus Cloud（免費額度）

1. 前往 [Milvus Cloud](https://cloud.zilliz.com/)
2. 註冊帳號（可用 Google 登入）
3. 創建 Free Tier Cluster：
   - 選擇 **Free** 方案
   - Region: `gcp-us-west1` (Oregon) - 免費版唯一選項
   - Cluster Name: `ultrarag-prod`
4. 創建完成後，記錄：
   - **Public Endpoint** (例如: `https://xxx.api.gcp-us-west1.zillizcloud.com`)
   - **API Key** (在 "API Keys" 頁面創建)

### 2. 準備 Google Cloud 環境

確保你已安裝 Google Cloud SDK：
```bash
# 檢查安裝
gcloud --version

# 登入
gcloud auth login

# 設定專案
gcloud config set project YOUR_PROJECT_ID
```

### 3. 啟用 Gemini API

1. 前往 [Google AI Studio](https://aistudio.google.com/)
2. 創建 API Key
3. 記錄你的 **GOOGLE_API_KEY**

## 部署步驟

### Windows 部署

```batch
# 1. 設定環境變數
set GOOGLE_API_KEY=your_gemini_api_key
set MILVUS_URI=https://xxx.api.gcp-asia-east1.zillizcloud.com
set MILVUS_TOKEN=your_milvus_api_key
set REGION=us-west1

# 2. 執行部署
cd D:\AWORKSPACE\Github\UltraRAG
docker\cloudrun\deploy.bat
```

### Linux/Mac 部署

```bash
# 1. 設定環境變數
export GOOGLE_API_KEY=your_gemini_api_key
export MILVUS_URI=https://xxx.api.gcp-asia-east1.zillizcloud.com
export MILVUS_TOKEN=your_milvus_api_key
export REGION=us-west1

# 2. 執行部署
cd /path/to/UltraRAG
chmod +x docker/cloudrun/deploy.sh
./docker/cloudrun/deploy.sh
```

## 手動部署（如果自動腳本失敗）

```bash
# 1. 啟用 API
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com

# 2. 建置並推送映像
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/ultrarag

# 3. 部署到 Cloud Run
gcloud run deploy ultrarag \
  --image gcr.io/YOUR_PROJECT_ID/ultrarag \
  --region us-west1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --set-env-vars "GOOGLE_API_KEY=xxx,MILVUS_URI=xxx,MILVUS_TOKEN=xxx"
```

## 部署後設定

### 上傳知識庫文件

部署完成後，需要通過 UI 上傳企業文件到知識庫：

1. 訪問 Cloud Run 服務 URL
2. 進入知識庫管理頁面
3. 上傳 PDF/DOCX/TXT 文件
4. 等待文件處理完成

### 查看日誌

```bash
gcloud run services logs read ultrarag --region=asia-east1
```

### 更新部署

修改代碼後，重新執行部署腳本即可自動更新。

## 費用估算

| 服務 | 免費額度 | 超出後費用 |
|------|----------|------------|
| Cloud Run | 2M requests/月 | ~$0.40/M requests |
| Milvus Cloud | 免費額度 5GB | 依用量計費 |
| Gemini API | 免費額度 | 依用量計費 |

**預估月費（低流量）：$0 - $50**

## 常見問題

### Q: 部署失敗，提示 "Permission denied"
A: 確保你的 GCP 帳號有以下權限：
- Cloud Build Editor
- Cloud Run Admin
- Storage Admin

### Q: 服務啟動後無法連接 Milvus
A: 檢查 Milvus Cloud 的：
- Public Endpoint 是否正確
- API Key 是否有效
- 網路是否允許外部連接（Milvus Cloud 預設允許）

### Q: 冷啟動太慢
A: 可以設定最小實例數：
```bash
gcloud run services update ultrarag --min-instances=1 --region=asia-east1
```
（注意：這會增加費用）
