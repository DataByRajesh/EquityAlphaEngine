#!/usr/bin/env bash
set -euo pipefail

# Step-by-step deployment script for EquityAlphaEngine on GCP Cloud Run
# Usage: bash infra/gcp/deploy-cloud-run.sh

# 1. Set variables
PROJECT_ID="equity-alpha-engine-alerts"
REGION="europe-west2"
AR_REPO="equity-images"
SERVICE_NAME="equity-alpha-engine"
IMAGE_NAME="$REGION-docker.pkg.dev/$PROJECT_ID/$AR_REPO/$SERVICE_NAME:latest"

# 2. Authenticate with GCP
gcloud auth login
gcloud config set project $PROJECT_ID

# 3. Build Docker image

docker build -t $IMAGE_NAME .

echo "Docker image built: $IMAGE_NAME"

# 4. Push image to Artifact Registry

gcloud auth configure-docker $REGION-docker.pkg.dev

docker push $IMAGE_NAME

echo "Docker image pushed to Artifact Registry"

# 5. Deploy to Cloud Run

gcloud run deploy $SERVICE_NAME \
  --image $IMAGE_NAME \
  --region $REGION \
  --platform managed \
  --cpu=1 \
  --memory=256Mi \
  --min-instances=0 \
  --max-instances=1 \
  --set-env-vars "APP_ENV=${APP_ENV},LOG_LEVEL=${LOG_LEVEL},BUILD_SHA=${IMAGE_TAG},DATABASE_URL=${DATABASE_URL}" \
  --allow-unauthenticated \
  --quiet

echo "Cloud Run service deployed: $SERVICE_NAME"

# 6. (Optional) Replace with YAML config
# gcloud run services replace infra/gcp/cloudrun-service.yaml --region $REGION

echo "Deployment complete."
