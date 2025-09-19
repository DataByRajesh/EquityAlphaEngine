# GCP Credentials Setup Guide

This guide explains how to properly configure GCP credentials for the EquityAlphaEngine project in different environments.

## Overview

The project uses Google Cloud Platform services including:
- Secret Manager (for storing sensitive configuration)
- Gmail API (for sending notifications)
- Cloud Storage (for caching)
- Cloud SQL (for database)

## Environment-Specific Setup

### 1. Cloud Run (Production)

**Automatic Setup**: When deployed to Cloud Run, the application automatically uses the service account attached to the Cloud Run service.

**Configuration**:
- Service account credentials are provided via the `GCP_SA_KEY` secret in GitHub
- The deployment pipeline automatically stores this in Secret Manager
- Environment variable `USE_GCP_SECRET_MANAGER=true` enables Secret Manager usage

**No manual setup required** - credentials are handled automatically by the deployment pipeline.

### 2. Local Development

**Option A: Service Account Key File (Recommended)**

1. Create a service account in the GCP Console
2. Download the service account key as JSON
3. Place the file in one of these locations:
   - `service-account-key.json` (project root)
   - `gcp-credentials.json` (project root)
   - `data_pipeline/service-account-key.json`
   - `data_pipeline/gcp-credentials.json`

**Option B: Environment Variable**

Set the `GCP_SA_KEY` environment variable with the JSON content:
```bash
export GCP_SA_KEY='{"type": "service_account", "project_id": "...", ...}'
```

**Option C: Google Cloud SDK**

Install and authenticate with gcloud:
```bash
gcloud auth application-default login
```

### 3. GitHub Actions (CI/CD)

Credentials are configured via GitHub repository secrets:
- `GCP_SA_KEY`: Service account key JSON
- `CLIENT_SECRET_JSON`: Gmail API client secrets

## Required Service Account Permissions

The service account needs the following IAM roles:
- `Secret Manager Secret Accessor` - to read secrets
- `Storage Object Admin` - for cache operations
- `Cloud SQL Client` - for database access
- Custom role with Gmail API permissions (if using Gmail features)

## Testing Credentials

Run the test script to verify your setup:
```bash
python test_gcp_credentials.py
```

Expected output:
- ✅ No "GCP credentials file not found" errors
- ✅ Secret Manager client creates successfully
- ⚠️ Warnings about missing credentials are normal in local development

## Troubleshooting

### Common Issues

**1. "No GCP service account credentials found"**
- This is a warning, not an error
- Normal in local development without service account key
- Application will still work if using gcloud authentication

**2. "Permission denied" errors**
- Check that the service account has the required IAM roles
- Verify the service account key is valid and not expired

**3. "Secret not found" errors**
- Ensure secrets exist in Secret Manager
- Check that the project ID is correct
- Verify the service account has Secret Manager access

### Environment Variables

Key environment variables for credential configuration:
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to service account key file
- `GCP_SA_KEY`: Service account key JSON content
- `USE_GCP_SECRET_MANAGER`: Enable/disable Secret Manager (default: true)
- `GCP_PROJECT_ID`: GCP project ID (set in config.py)

## Security Best Practices

1. **Never commit service account keys to version control**
2. **Use Secret Manager for sensitive configuration in production**
3. **Rotate service account keys regularly**
4. **Use least-privilege IAM roles**
5. **Monitor service account usage in GCP Console**

## Migration from Old Setup

If you're migrating from the old hardcoded credentials path:
1. Remove any hardcoded credential file paths
2. Follow the setup instructions above for your environment
3. Test with `python test_gcp_credentials.py`
4. Deploy and verify in Cloud Run

The new system automatically handles different environments and provides better error messages for troubleshooting.
