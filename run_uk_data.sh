#!/bin/bash
# Cloud-native wrapper to update UK data for the last 10 years using GCP services

set -e
cd "$(dirname "$0")"

# Ensure required environment variables are set (fail fast if missing)
: "${DATABASE_URL:?Need to set DATABASE_URL}"
: "${QUANDL_API_KEY:?Need to set QUANDL_API_KEY}"
: "${GCP_PROJECT_ID:?Need to set GCP_PROJECT_ID}"

# Optionally activate GCP service account if running outside Cloud Run
# gcloud auth activate-service-account --key-file="$GOOGLE_APPLICATION_CREDENTIALS"

# Run the pipeline (all config/secrets loaded from env vars)
python data_pipeline/update_financial_data.py --years 10

# Optionally, trigger a Cloud Run job (uncomment if needed)
# gcloud run jobs execute equity-alpha-engine-job --region="$GCP_REGION" --project="$GCP_PROJECT_ID"
