# GCP Infrastructure and Deployment

This directory contains configuration and scripts for setting up GCP infrastructure and deploying the EquityAlphaEngine to [Cloud Run](https://cloud.google.com/run).
Container images are stored in an [Artifact Registry](https://cloud.google.com/artifact-registry) repository.

## Project Setup and Migration

### Initial Project Setup
If setting up a new GCP project for EquityAlphaEngine:

1. Create a new GCP project in the [Google Cloud Console](https://console.cloud.google.com/)
2. Authenticate with gcloud:
   ```bash
   gcloud auth login
   gcloud config set project <PROJECT_ID>
   ```
3. Grant necessary permissions to your account:
   ```bash
   cd infra/gcp
   bash grant-permissions.sh
   ```
   This script grants all required IAM roles to enable API management and resource creation.

4. Create GCP resources (VPC, Cloud SQL, Cloud Storage, service accounts):
   ```bash
   bash create-gcp-resources.sh
   ```
   This script enables APIs and creates all necessary infrastructure.

Alternatively, use Terraform for infrastructure as code (run from infra/gcp directory):
```bash
cd infra/gcp
terraform init
terraform plan
terraform apply -auto-approve
```

### Migrating from Existing Project
To migrate EquityAlphaEngine to a new GCP project:

1. Follow steps 1-4 above for the new project
2. Update `../../data_pipeline/config.py` with the new project ID and bucket name
3. Update GitHub repository secrets with new service account credentials
4. Deploy the application (see below)

## Deploying

1. Authenticate with gcloud and set your project:
   ```bash
   gcloud auth login
   gcloud config set project <PROJECT_ID>
   ```
2. Configure Docker to authenticate to Artifact Registry (replace REGION with your deploy region):
   ```bash
   gcloud auth configure-docker REGION-docker.pkg.dev
   ```
3. Build and deploy using the provided script. The script pushes the container image to the `AR_REPO` Artifact Registry repository in your project:
   ```bash
   cd infra/gcp
   ./deploy-cloud-run.sh
   ```
   The script uses `gcloud builds submit` to build the container image and `gcloud run deploy` to create or update the Cloud Run service.

Alternatively you can deploy using the YAML definition:

```bash
gcloud run services replace cloudrun-service.yaml --region <REGION>
```

## Required IAM Roles
The account running the deployment needs the following roles:

- `roles/run.admin` – deploy and manage Cloud Run services
- `roles/iam.serviceAccountUser` – use the service account on the service
- `roles/cloudbuild.builds.editor` – build container images with Cloud Build

## Network Settings
By default the service is deployed to the public internet. To restrict access or connect to a VPC:

- Use `--ingress internal` to limit inbound traffic to internal sources
- Configure a [Serverless VPC Access Connector](https://cloud.google.com/run/docs/configuring/connecting-vpc) and deploy with `--vpc-connector CONNECTOR_NAME` and optional `--subnet SUBNET_NAME`

Update `cloudrun-service.yaml` or the deploy script with your desired network parameters.
