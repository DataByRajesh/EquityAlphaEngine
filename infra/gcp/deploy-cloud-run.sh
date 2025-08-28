#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID=${PROJECT_ID:-$(gcloud config get-value project)}
REGION=${REGION:-us-central1}
SERVICE_NAME=${SERVICE_NAME:-equity-alpha-engine}
IMAGE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest"

# Build container image using Cloud Build
echo "Building image ${IMAGE}"
gcloud builds submit --tag "${IMAGE}" ..

# Deploy to Cloud Run
echo "Deploying ${SERVICE_NAME} to Cloud Run region ${REGION}"
gcloud run deploy "${SERVICE_NAME}" --image "${IMAGE}" --region "${REGION}" --platform managed --allow-unauthenticated
