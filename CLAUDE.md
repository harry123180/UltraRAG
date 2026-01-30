# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

UltraRAG is a lightweight RAG (Retrieval-Augmented Generation) development framework based on the Model Context Protocol (MCP) architecture. It standardizes core RAG components (Retriever, Generation, etc.) as independent MCP Servers, enabling workflow orchestration through YAML configuration files.

## Common Commands

```bash
# Install dependencies (using uv package manager)
uv sync              # Core dependencies only
uv sync --all-extras # Full installation (retriever, generation, corpus, evaluation)

# Activate virtual environment
.venv\Scripts\activate.bat  # Windows CMD
.venv\Scripts\Activate.ps1  # Windows PowerShell
source .venv/bin/activate   # Linux/macOS

# Run a pipeline
ultrarag run examples/rag.yaml                    # Basic RAG
ultrarag run examples/sayhello.yaml               # Verify installation

# Run with custom parameters
ultrarag run examples/rag.yaml -p examples/parameter/custom.yaml

# Launch UI
ultrarag ui                    # Chat mode (default port 5050)
ultrarag ui --admin            # Admin mode for pipeline building
ultrarag ui --port 8080        # Custom port

# Run tests
pytest
```

## Architecture

### MCP Client-Server Model
The framework uses a client-server architecture where:
- **MCP Client** (`src/ultrarag/client.py`): Orchestrates pipeline execution by calling tools on MCP servers
- **MCP Servers** (`servers/`): Independent modules exposing tools via the MCP protocol

### Directory Structure
```
src/ultrarag/           # Core framework code
  client.py             # Pipeline runner and MCP client
  server.py             # UltraRAG_MCP_Server base class
  api.py                # Python API (ToolCall, PipelineCall)

servers/                # MCP server modules
  retriever/            # Dense/sparse retrieval (FAISS, Milvus, BM25)
  generation/           # LLM generation (vLLM, OpenAI API)
  benchmark/            # Dataset loading
  evaluation/           # Metrics (acc, F1, EM, ROUGE, etc.)
  prompt/               # Prompt templates
  router/               # Conditional branching logic
  corpus/               # Document processing and chunking
  custom/               # Custom utility functions
  reranker/             # Reranking models

ui/                     # Web UI
  backend/              # Flask app (app.py, pipeline_manager.py)
  frontend/             # Static HTML/JS/CSS

examples/               # Pipeline YAML files
  parameter/            # Parameter override files
```

### Creating an MCP Server
Servers are Python files in `servers/<name>/src/<name>.py`:
```python
from ultrarag.server import UltraRAG_MCP_Server

app = UltraRAG_MCP_Server("myserver")

@app.tool(output="input_var->output_var")
def my_tool(input_var: str) -> dict:
    return {"output_var": "result"}

if __name__ == "__main__":
    app.run(transport="stdio")
```

Server parameters are defined in `servers/<name>/parameter.yaml`.

### Pipeline YAML Structure
Pipelines define servers and execution steps:
```yaml
servers:
  retriever: servers/retriever
  generation: servers/generation

pipeline:
- retriever.retriever_init
- retriever.retriever_search
- generation.generate
```

Control structures:
- **Sequential**: List of step names
- **Loop**: `loop: { times: N, steps: [...] }`
- **Branch**: `branch: { router: [...], branches: { case1: [...], case2: [...] } }`

Input/output mapping:
```yaml
- generation.generate:
    input:
      prompt: custom_prompt
    output:
      ans_ls: subq_ls
```

## Python API

```python
from ultrarag.api import initialize, ToolCall, PipelineCall

# Direct tool calls
initialize(["retriever", "benchmark"], server_root="servers")
result = ToolCall.retriever.retriever_search(query_list=queries, top_k=5)

# Run full pipeline
result = PipelineCall("examples/rag.yaml", "params.yaml")
```

## Key Configuration Files

- `servers/<server>/parameter.yaml`: Default parameters for each server
- `examples/parameter/*.yaml`: Pipeline-specific parameter overrides
- `.env`: Environment variables (API keys, etc.)

## Retrieval Backends

The retriever server supports multiple backends configured in `servers/retriever/parameter.yaml`:
- `sentence_transformers`: Local embedding models
- `infinity`: Optimized inference backend
- `openai`: OpenAI embeddings API
- `bm25`: Sparse retrieval

Index backends: `faiss` (local), `milvus` (vector database)

## Generation Backends

Configured in `servers/generation/parameter.yaml`:
- `vllm`: Local LLM serving
- `openai`: OpenAI-compatible API
- `hf`: Hugging Face transformers

## GCP Cloud Run 部署

詳細文檔: `docs/GCP_DEPLOYMENT_GUIDE.md`

### 快速部署命令

```bash
# 1. 設定 GCP 專案
gcloud config set project YOUR_PROJECT_ID

# 2. 啟用必要 API
gcloud services enable cloudbuild.googleapis.com run.googleapis.com containerregistry.googleapis.com

# 3. 建置映像
gcloud builds submit --config cloudbuild.yaml

# 4. 部署到 Cloud Run
gcloud run deploy ultrarag \
  --image gcr.io/YOUR_PROJECT_ID/ultrarag:latest \
  --region us-west1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --set-env-vars "GOOGLE_API_KEY=xxx,MILVUS_URI=xxx,MILVUS_TOKEN=xxx"
```

### 環境變數

| 變數 | 說明 |
|------|------|
| GOOGLE_API_KEY | Gemini API Key |
| MILVUS_URI | Milvus Cloud Endpoint |
| MILVUS_TOKEN | Milvus 認證 (user:password) |

### 常用命令

```bash
# 查看日誌
gcloud run services logs read ultrarag --region us-west1

# 更新部署
gcloud builds submit --config cloudbuild.yaml && \
gcloud run deploy ultrarag --image gcr.io/$(gcloud config get-value project)/ultrarag:latest --region us-west1
```

### 當前部署

- **Service URL**: https://ultrarag-556560931446.us-west1.run.app
- **Region**: us-west1 (Oregon)
- **Project**: my-website-harry123
