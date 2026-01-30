# UltraRAG Cloud Run Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster dependency installation
RUN pip install uv

# Copy project files
COPY pyproject.toml .
COPY src/ ./src/
COPY servers/ ./servers/
COPY prompt/ ./prompt/
COPY examples/ ./examples/
COPY ui/ ./ui/
COPY data/ ./data/

# Install dependencies
RUN uv pip install --system -e .

# Install additional dependencies for cloud deployment
RUN uv pip install --system google-generativeai litellm gunicorn

# Create necessary directories
RUN mkdir -p /app/index /app/output /app/data/knowledge_base

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=ui/backend/app.py
ENV PORT=8080

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

# Run with gunicorn for production
CMD exec gunicorn --bind :$PORT --workers 2 --threads 4 --timeout 120 "ui.backend.app:app"
