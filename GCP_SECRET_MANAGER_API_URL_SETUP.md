# 🔐 Google Cloud Secret Manager - API URL Setup Guide

## Overview
This guide shows how to properly configure and retrieve the API URL from Google Cloud Secret Manager for the Equity Alpha Engine project.

## Prerequisites
- Google Cloud Project: `equity-alpha-engine-alerts`
- Google Cloud CLI (`gcloud`) installed and authenticated
- Proper IAM permissions for Secret Manager

## Step 1: Authenticate with Google Cloud

### Option A: Using Service Account Key (Recommended for Local Development)
```bash
# Set the service account key file path
export GOOGLE_APPLICATION_CREDENTIALS="path/to/your/service-account-key.json"

# Or set it in your environment
set GOOGLE_APPLICATION_CREDENTIALS=path\to\your\service-account-key.json  # Windows
```

### Option B: Using gcloud CLI
```bash
# Login to Google Cloud
gcloud auth login

# Set the project
gcloud config set project equity-alpha-engine-alerts
```

## Step 2: Create/Update API_URL Secret in Secret Manager

### Check if API_URL secret exists
```bash
gcloud secrets describe API_URL --project=equity-alpha-engine-alerts
```

### Create the API_URL secret (if it doesn't exist)
```bash
# Create the secret with the production API URL
echo "https://equity-api-248891289968.europe-west2.run.app" | gcloud secrets create API_URL --data-file=- --project=equity-alpha-engine-alerts
```

### Update the API_URL secret (if it already exists)
```bash
# Update the secret with the correct API URL
echo "https://equity-api-248891289968.europe-west2.run.app" | gcloud secrets versions add API_URL --data-file=- --project=equity-alpha-engine-alerts
```

## Step 3: Verify Secret Manager Access

### Test retrieving the secret
```bash
gcloud secrets versions access latest --secret="API_URL" --project=equity-alpha-engine-alerts
```

**Expected Output:**
```
https://equity-api-248891289968.europe-west2.run.app
```

## Step 4: Configure IAM Permissions

### Grant Secret Manager access to your service account
```bash
# Replace YOUR_SERVICE_ACCOUNT_EMAIL with your actual service account email
gcloud projects add-iam-policy-binding equity-alpha-engine-alerts \
    --member="serviceAccount:YOUR_SERVICE_ACCOUNT_EMAIL" \
    --role="roles/secretmanager.secretAccessor"
```

### For Cloud Run service account (if using Cloud Run)
```bash
# Get the Cloud Run service account
gcloud run services describe equity-alpha-engine --region=europe-west2 --format="value(spec.template.spec.serviceAccountName)"

# Grant access (replace with actual service account)
gcloud projects add-iam-policy-binding equity-alpha-engine-alerts \
    --member="serviceAccount:CLOUD_RUN_SERVICE_ACCOUNT@equity-alpha-engine-alerts.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

## Step 5: Environment Variables Setup

### For Local Development
```bash
# Windows
set USE_GCP_SECRET_MANAGER=true
set GCP_PROJECT_ID=equity-alpha-engine-alerts

# Linux/Mac
export USE_GCP_SECRET_MANAGER=true
export GCP_PROJECT_ID=equity-alpha-engine-alerts
```

### For Cloud Run Deployment
The environment variables are automatically set via the deployment scripts in `.github/workflows/`.

## Step 6: Test the Integration

### Create a test script to verify Secret Manager access
```python
# test_secret_manager.py
import os
from data_pipeline.utils import get_secret

try:
    api_url = get_secret("API_URL")
    print(f"✅ Successfully retrieved API_URL: {api_url}")
    
    # Test the API URL
    import requests
    response = requests.get(f"{api_url}/health", timeout=10)
    if response.status_code == 200:
        print(f"✅ API health check successful: {response.json()}")
    else:
        print(f"❌ API health check failed: {response.status_code}")
        
except Exception as e:
    print(f"❌ Error retrieving API_URL from Secret Manager: {e}")
    print("Falling back to localhost:8000")
```

### Run the test
```bash
python test_secret_manager.py
```

## Step 7: Troubleshooting

### Common Issues and Solutions

#### Issue 1: "Permission denied" error
**Solution:**
```bash
# Check current authentication
gcloud auth list

# Re-authenticate if needed
gcloud auth application-default login
```

#### Issue 2: "Secret not found" error
**Solution:**
```bash
# List all secrets to verify
gcloud secrets list --project=equity-alpha-engine-alerts

# Create the secret if missing
echo "https://equity-api-248891289968.europe-west2.run.app" | gcloud secrets create API_URL --data-file=- --project=equity-alpha-engine-alerts
```

#### Issue 3: "Invalid credentials" error
**Solution:**
```bash
# Check service account key file exists and is valid
ls -la $GOOGLE_APPLICATION_CREDENTIALS  # Linux/Mac
dir %GOOGLE_APPLICATION_CREDENTIALS%    # Windows

# Verify the key file format (should be JSON)
head -n 5 $GOOGLE_APPLICATION_CREDENTIALS
```

## Step 8: Verify Streamlit App Configuration

The Streamlit app (`streamlit_app.py`) should automatically:
1. Try to get API_URL from Secret Manager
2. Fall back to `http://localhost:8000` if Secret Manager fails
3. Log which source is being used

### Check the logs when running Streamlit:
```bash
streamlit run streamlit_app.py
```

**Expected log output:**
```
2025-09-19 21:32:33,416 [INFO] __main__: Using API_URL from secret manager: https://equity-api-248891289968.europe-west2.run.app
```

## Summary

After following these steps:
1. ✅ API_URL secret is stored in Google Cloud Secret Manager
2. ✅ Proper IAM permissions are configured
3. ✅ Environment variables are set correctly
4. ✅ Streamlit app can retrieve the API URL automatically
5. ✅ Fallback to localhost works for local development

The system will automatically use the production API URL from Secret Manager when properly configured, and fall back to local development URL when needed.
