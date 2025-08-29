#!/bin/bash
set -euo pipefail

# Step-by-step deployment script for EquityAlphaEngine on GCP Cloud Run
# Usage: bash infra/gcp/deploy-cloud-run.sh

###############################################
# 1. Set essential and mandatory variables
###############################################
GCP_PROJECT_ID=${secrets.GCP_PROJECT_ID}
GCP_REGION=${vars.GCP_REGION:-}
CLOUD_RUN_SERVICE=${vars.CLOUD_RUN_SERVICE:-}
REPO=${vars.REPO:-}
IMAGE_TAG=${{ github.sha }}
IMAGE_URI=${secrets.IMAGE_URI:-$GCP_REGION-docker.pkg.dev/$GCP_PROJECT_ID/$REPO/$CLOUD_RUN_SERVICE}
DATABASE_URL=${secrets.DATABASE_URL:-}
GCP_SA_KEY=${secrets.GCP_SA_KEY:-}
GMAIL_CREDENTIALS_FILE=${secrets.GMAIL_CREDENTIALS_FILE:-}
QUANDL_API_KEY=${secrets.QUANDL_API_KEY:-}
BUILD_SHA=${secrets.BUILD_SHA:-$IMAGE_TAG}

# Warn if any required variable is missing
for var in GCP_PROJECT_ID GCP_REGION CLOUD_RUN_SERVICE REPO DATABASE_URL GCP_SA_KEY GMAIL_CREDENTIALS_FILE QUANDL_API_KEY; do
  if [ -z "${!var}" ]; then
    echo "ERROR: $var is not set. Please set it as an environment variable or in a .env file."
    exit 1
  fi
done

IMAGE_NAME="$IMAGE_URI:$IMAGE_TAG"

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

gcloud run deploy "$CLOUD_RUN_SERVICE" \
  --image "$IMAGE_NAME" \
  --region "$GCP_REGION" \
  --platform managed \
  --cpu=1 \
  --memory=256Mi \
  --min-instances=0 \
  --max-instances=1 \
  --set-env-vars "GCP_PROJECT_ID=${GCP_PROJECT_ID},GCP_REGION=${GCP_REGION},CLOUD_RUN_SERVICE=${CLOUD_RUN_SERVICE},REPO=${REPO},IMAGE_TAG=${IMAGE_TAG},IMAGE_URI=${IMAGE_URI},DATABASE_URL=${DATABASE_URL},GCP_SA_KEY=${GCP_SA_KEY},GMAIL_CREDENTIALS_FILE=${GMAIL_CREDENTIALS_FILE},QUANDL_API_KEY=${QUANDL_API_KEY},BUILD_SHA=${BUILD_SHA}" \
  --allow-unauthenticated \
  --quiet

echo "Cloud Run service deployed: $SERVICE_NAME"

# 6. (Optional) Replace with YAML config
# gcloud run services replace infra/gcp/cloudrun-service.yaml --region $REGION

echo "Deployment complete."
