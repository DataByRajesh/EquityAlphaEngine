#!/usr/bin/env bash
set -euo pipefail

#
# Deploy EquityAlphaEngine API to GCP Cloud Run (local-friendly)
# --------------------------------------------------------------
# Usage:
#   export GCP_PROJECT_ID="your-project" \
#          GCP_REGION="europe-west2" \
#          REPO="containers" \
#          CLOUD_RUN_SERVICE="equity-api"
#   # optional:
#   export IMAGE_TAG="$(git rev-parse --short HEAD)"  # or any tag
#   export VPC_CONNECTOR_NAME="equity-vpc-connector"  # if you have one
#   export SERVICE_ACCOUNT_EMAIL="svc@your-project.iam.gserviceaccount.com"  # optional
#
#   bash infra/gcp/deploy-cloud-run.sh
#
# This script:
#   - Ensures the Artifact Registry repo exists
#   - Builds and pushes the container (Cloud Build)
#   - Deploys to Cloud Run with free-tier friendly flags

###############################################
# 1) Validate/prepare variables
###############################################
GCP_PROJECT_ID=${GCP_PROJECT_ID:?"GCP_PROJECT_ID is required"}
GCP_REGION=${GCP_REGION:?"GCP_REGION is required (e.g. europe-west2)"}
REPO=${REPO:-containers}
CLOUD_RUN_SERVICE=${CLOUD_RUN_SERVICE:-equity-api}
IMAGE_TAG=${IMAGE_TAG:-$(git rev-parse --short HEAD 2>/dev/null || date +%Y%m%d%H%M%S)}
IMAGE_URI="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${REPO}/${CLOUD_RUN_SERVICE}"
VPC_CONNECTOR_NAME=${VPC_CONNECTOR_NAME:-}
SERVICE_ACCOUNT_EMAIL=${SERVICE_ACCOUNT_EMAIL:-}

# App env configuration
USE_GCP_SECRET_MANAGER=${USE_GCP_SECRET_MANAGER:-true}

echo "Project:        $GCP_PROJECT_ID"
echo "Region:         $GCP_REGION"
echo "Repo:           $REPO"
echo "Service:        $CLOUD_RUN_SERVICE"
echo "Image tag:      $IMAGE_TAG"
echo "Image URI:      $IMAGE_URI:$IMAGE_TAG"
echo "VPC connector:  ${VPC_CONNECTOR_NAME:-<none>}"
echo "Service account:${SERVICE_ACCOUNT_EMAIL:-<default>}"

###############################################
# 2) gcloud auth and project
###############################################
if ! gcloud config get-value account >/dev/null 2>&1; then
  echo "Logging in to gcloud..."
  gcloud auth login
fi
gcloud config set project "$GCP_PROJECT_ID"

###############################################
# 3) Ensure Artifact Registry repo exists
###############################################
if ! gcloud artifacts repositories describe "$REPO" --location="$GCP_REGION" >/dev/null 2>&1; then
  echo "Creating Artifact Registry repo '$REPO' in $GCP_REGION..."
  gcloud artifacts repositories create "$REPO" \
    --repository-format=docker \
    --location="$GCP_REGION" \
    --immutable-tags
fi

###############################################
# 4) Build and push image using Cloud Build
###############################################
echo "Building and pushing image via Cloud Build..."
gcloud builds submit --tag "$IMAGE_URI:$IMAGE_TAG" .

###############################################
# 5) Deploy to Cloud Run (no-cost tier settings)
###############################################
echo "Deploying to Cloud Run..."

DEPLOY_ARGS=(
  "--image=$IMAGE_URI:$IMAGE_TAG"
  "--region=$GCP_REGION"
  "--platform=managed"
  "--cpu=1"
  "--memory=256Mi"
  "--min-instances=0"
  "--max-instances=1"
  "--timeout=600"
  "--allow-unauthenticated"
  "--set-env-vars=GCP_PROJECT_ID=$GCP_PROJECT_ID,GCP_REGION=$GCP_REGION,GMAIL_CREDENTIALS_SECRET_NAME=GMAIL_CLIENT_SECRET,USE_GCP_SECRET_MANAGER=$USE_GCP_SECRET_MANAGER"
  "--set-secrets=DATABASE_URL=DATABASE_URL:latest"
)

if [[ -n "$VPC_CONNECTOR_NAME" ]]; then
  DEPLOY_ARGS+=("--vpc-connector=projects/${GCP_PROJECT_ID}/locations/${GCP_REGION}/connectors/${VPC_CONNECTOR_NAME}")
fi

if [[ -n "$SERVICE_ACCOUNT_EMAIL" ]]; then
  DEPLOY_ARGS+=("--service-account=$SERVICE_ACCOUNT_EMAIL")
fi

gcloud run deploy "$CLOUD_RUN_SERVICE" "${DEPLOY_ARGS[@]}"

URL=$(gcloud run services describe "$CLOUD_RUN_SERVICE" --region "$GCP_REGION" --format='value(status.url)')
echo ""
echo "Deployed: $URL"
echo "Done."
