#!/bin/bash
# Build, push, and deploy Streamlit app to Cloud Run

PROJECT_ID="your-gcp-project-id"
REGION="europe-west2"
REPOSITORY="your-artifact-repo"
IMAGE_NAME="streamlit-app"

# Build Docker image
docker build -f Dockerfile.streamlit -t $IMAGE_NAME:latest .

# Tag image for Artifact Registry
docker tag $IMAGE_NAME:latest $REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/$IMAGE_NAME:latest

# Authenticate Docker with Google Cloud
gcloud auth configure-docker $REGION-docker.pkg.dev

# Push image to Artifact Registry
docker push $REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/$IMAGE_NAME:latest

# Deploy to Cloud Run
gcloud run deploy $IMAGE_NAME \
  --image=$REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/$IMAGE_NAME:latest \
  --platform=managed \
  --region=$REGION \
  --allow-unauthenticated
