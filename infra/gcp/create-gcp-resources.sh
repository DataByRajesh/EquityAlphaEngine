#!/bin/bash

# Script to create GCP resources for EquityAlphaEngine migration
# Run this script after setting up authentication with: gcloud auth login

set -e

# Configuration
PROJECT_ID="equity-alpha-engine-uk"
REGION="europe-west2"
BUCKET_NAME="equity-alpha-engine-uk-bucket"
VPC_CONNECTOR_NAME="equity-vpc-connector-uk"
SERVICE_ACCOUNT_NAME="equity-alpha-engine-sa"

echo "Setting up GCP project: $PROJECT_ID"
echo "Region: $REGION"

# Set the project
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "Enabling required APIs..."
gcloud services enable secretmanager.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable vpcaccess.googleapis.com
gcloud services enable gmail.googleapis.com

# Create Cloud Storage bucket
echo "Creating Cloud Storage bucket: $BUCKET_NAME"
gcloud storage buckets create gs://$BUCKET_NAME \
    --location=$REGION \
    --storage-class=STANDARD \
    --uniform-bucket-level-access

# Set lifecycle policy for cache cleanup
gcloud storage buckets lifecycle set lifecycle.json gs://$BUCKET_NAME

# Create VPC network and subnet
echo "Creating VPC network and subnet..."
gcloud compute networks create equity-alpha-engine-vpc \
    --subnet-mode=custom

gcloud compute networks subnets create equity-alpha-engine-subnet \
    --network=equity-alpha-engine-vpc \
    --region=$REGION \
    --range=10.0.0.0/24

# Create VPC connector
echo "Creating VPC connector: $VPC_CONNECTOR_NAME"
gcloud compute networks vpc-access connectors create $VPC_CONNECTOR_NAME \
    --region=$REGION \
    --network=equity-alpha-engine-vpc \
    --range=10.8.0.0/28 \
    --min-instances=2 \
    --max-instances=10

# Create Cloud SQL instance
echo "Creating Cloud SQL instance..."
gcloud sql instances create equity-alpha-engine-db \
    --database-version=POSTGRES_15 \
    --region=$REGION \
    --tier=db-f1-micro \
    --storage-size=10GB \
    --storage-type=SSD \
    --backup-start-time=02:00 \
    --maintenance-window-day=SUN \
    --maintenance-window-hour=3 \
    --network=equity-alpha-engine-vpc \
    --no-assign-ip

# Create database
echo "Creating database..."
gcloud sql databases create equity_alpha_engine \
    --instance=equity-alpha-engine-db

# Create service account
echo "Creating service account: $SERVICE_ACCOUNT_NAME"
gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME \
    --display-name="Equity Alpha Engine Service Account"

SERVICE_ACCOUNT_EMAIL="$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com"

# Grant IAM roles to service account
echo "Granting IAM roles to service account..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/storage.objectAdmin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/gmail.send"

# Create service account key
echo "Creating service account key..."
gcloud iam service-accounts keys create service-account-key.json \
    --iam-account=$SERVICE_ACCOUNT_EMAIL

echo "GCP resources created successfully!"
echo "Service account key saved to: service-account-key.json"
echo "Please store this key securely and update your GitHub secrets."
echo ""
echo "Next steps:"
echo "1. Create secrets in Secret Manager for DATABASE_URL, GMAIL_CREDENTIALS, etc."
echo "2. Update GitHub repository secrets with new values"
echo "3. Deploy the application using the updated configuration"
