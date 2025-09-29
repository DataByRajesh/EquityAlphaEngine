#!/bin/bash

# Script: setup-gcp-project-idempotent.sh
# Purpose: Grant necessary IAM roles and enable required APIs for Terraform deployment
#          in an idempotent way (safe to rerun)
# Usage: bash setup-gcp-project-idempotent.sh

set -euo pipefail

# -----------------------------
# Configuration
# -----------------------------
PROJECT_ID="equity-alpha-engine-uk"
USER_EMAIL="rajanalyst98@gmail.com"  # Replace with your email
REGION="europe-west2"

# Required IAM roles
IAM_ROLES=(
    "roles/owner"
    "roles/serviceusage.serviceUsageAdmin"
    "roles/resourcemanager.projectIamAdmin"
    "roles/storage.admin"
    "roles/compute.admin"
    "roles/cloudsql.admin"
    "roles/secretmanager.admin"
    "roles/run.admin"
)

# Required APIs
APIS=(
    "compute.googleapis.com"
    "sqladmin.googleapis.com"
    "storage.googleapis.com"
    "run.googleapis.com"
    "vpcaccess.googleapis.com"
    "gmail.googleapis.com"
    "secretmanager.googleapis.com"
    "servicenetworking.googleapis.com"   # Required for Cloud SQL private IP
)

# -----------------------------
# Helper Functions
# -----------------------------

grant_role_if_missing() {
    local role=$1
    local member="user:$USER_EMAIL"

    # Check if role already granted
    if gcloud projects get-iam-policy $PROJECT_ID \
        --flatten="bindings[].members" \
        --format="value(bindings.role,bindings.members)" \
        | grep -q "$role $member"; then
        echo "Role $role already granted to $USER_EMAIL"
    else
        echo "Granting role $role to $USER_EMAIL..."
        gcloud projects add-iam-policy-binding $PROJECT_ID \
            --member="$member" \
            --role="$role"
    fi
}

enable_api_if_missing() {
    local api=$1
    # Check if API is already enabled
    if gcloud services list --enabled --project="$PROJECT_ID" \
        | grep -q "^$api$"; then
        echo "API $api is already enabled"
    else
        echo "Enabling API: $api..."
        gcloud services enable "$api" --project="$PROJECT_ID"
    fi
}

# -----------------------------
# Set project
# -----------------------------
echo "Setting project to $PROJECT_ID..."
gcloud config set project $PROJECT_ID

# -----------------------------
# Grant IAM roles
# -----------------------------
echo "Granting required IAM roles..."
for role in "${IAM_ROLES[@]}"; do
    grant_role_if_missing "$role"
done

# -----------------------------
# Enable required APIs
# -----------------------------
echo "Enabling required APIs..."
for api in "${APIS[@]}"; do
    enable_api_if_missing "$api"
done

# -----------------------------
# Done
# -----------------------------
echo ""
echo "✅ GCP project setup completed successfully!"
echo "Next steps:"
echo "1. Wait a few minutes for IAM changes and API enabling to propagate."
echo "2. Run your Terraform deployment:"
echo "   terraform init"
echo "   terraform apply -auto-approve"
