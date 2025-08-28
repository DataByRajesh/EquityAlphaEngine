#!/usr/bin/env bash
set -euo pipefail

GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project)}
REGION=${REGION:-us-central1}
SERVICE_NAME=${SERVICE_NAME:-equity-alpha-engine}
AR_REPO=${AR_REPO:-containers}
IMAGE="${REGION}-docker.pkg.dev/${GOOGLE_CLOUD_PROJECT}/${AR_REPO}/${SERVICE_NAME}:latest"

# Build container image using Cloud Build
echo "Building image ${IMAGE}"
gcloud builds submit --tag "${IMAGE}" ..

# Deploy to Cloud Run
echo "Deploying ${SERVICE_NAME} to Cloud Run region ${REGION}"
gcloud run deploy "${SERVICE_NAME}" --image "${IMAGE}" --region "${REGION}" --platform managed --allow-unauthenticated
