# GCP Deployment

This directory contains configuration and scripts for deploying the EquityAlphaEngine to [Cloud Run](https://cloud.google.com/run).
Container images are stored in an [Artifact Registry](https://cloud.google.com/artifact-registry) repository.

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
