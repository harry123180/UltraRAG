#!/bin/bash
# UltraRAG Cloud Run Deployment Script
# Usage: ./deploy.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   UltraRAG Cloud Run Deployment${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed${NC}"
    echo "Please install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Get current project
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Error: No GCP project set${NC}"
    echo "Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo -e "${YELLOW}Current Project: ${PROJECT_ID}${NC}"

# Check for required environment variables
if [ -z "$GOOGLE_API_KEY" ]; then
    echo -e "${RED}Error: GOOGLE_API_KEY not set${NC}"
    echo "Run: export GOOGLE_API_KEY=your_api_key"
    exit 1
fi

# Optional: Milvus Cloud configuration
MILVUS_URI=${MILVUS_URI:-""}
MILVUS_TOKEN=${MILVUS_TOKEN:-""}

# Set region
REGION=${REGION:-"us-west1"}
echo -e "${YELLOW}Region: ${REGION}${NC}"

# Navigate to project root
cd "$(dirname "$0")/../.."

# Enable required APIs
echo -e "${YELLOW}Enabling required APIs...${NC}"
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com

# Build and deploy using Cloud Build
echo -e "${YELLOW}Building and deploying...${NC}"
gcloud builds submit \
    --config docker/cloudrun/cloudbuild.yaml \
    --substitutions="_REGION=${REGION},_GOOGLE_API_KEY=${GOOGLE_API_KEY},_MILVUS_URI=${MILVUS_URI},_MILVUS_TOKEN=${MILVUS_TOKEN}"

# Get the service URL
SERVICE_URL=$(gcloud run services describe ultrarag --region=$REGION --format='value(status.url)')

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Service URL: ${SERVICE_URL}${NC}"
echo ""
echo -e "${YELLOW}To view logs:${NC}"
echo "gcloud run services logs read ultrarag --region=$REGION"
