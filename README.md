## 📢 Project Release History

| Version | Description | Status | Link |
|---|---|---|---|
| **v1.0-beta** | Phase 1 Pre-Release — Data Pipeline & Screener | 🚧 Pre-Release | [View Release](https://github.com/DataByRajesh/EquityAlphaEngine/releases/tag/v1.0-beta) |

---

> 📝 **Note:**
> This is a **pre-release** version. The project is under active development.
> Macroeconomic data is integrated into the pipeline and stored alongside market
> data.

### Required credentials

The project expects several environment variables for external services. They
can be supplied via a local `.env` file.

```env
QUANDL_API_KEY=your_quandl_key
DATABASE_URL=postgresql://user:password@host:5432/database
GOOGLE_CLOUD_PROJECT=your_project_id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
GCS_BUCKET=your-bucket
GCS_PREFIX=cache/prefix
```

- `QUANDL_API_KEY` – used by `data_pipeline/Macro_data.py` and consumed by
  `data_pipeline/market_data.py` to persist macroeconomic indicators.
- `DATABASE_URL` – consumed throughout the pipeline for database connections.
- `GOOGLE_CLOUD_PROJECT` and `GOOGLE_APPLICATION_CREDENTIALS` – authenticate to
  Google Cloud when using the GCS cache backend.
- `GCS_BUCKET` and `GCS_PREFIX` – define the Google Cloud Storage location for
  cached fundamentals in `data_pipeline/cache_utils.py`.

### Dashboard integration

Connect business intelligence tools such as Tableau or PowerBI directly to the
database populated by the data pipeline to build visual dashboards.
For step-by-step instructions on connecting Tableau, see
[docs/tableau.md](docs/tableau.md).

### Fetching UK Market Data

Run the data pipeline script to download FTSE 100 data. The command below
fetches the last decade of data by default; adjust `--years` as needed:

```bash
python data_pipeline/market_data.py --years 10
```

### Concurrency configuration

The pipeline executes many network-bound requests in parallel. The default
thread count now scales with available CPU cores (roughly five threads per
core) for better performance on larger machines. You can override this by
setting the `MAX_THREADS` environment variable:

```bash
MAX_THREADS=20 python data_pipeline/market_data.py --years 10
```

### Optional cache backends

The pipeline defaults to a local filesystem cache. To use Redis or Google Cloud
Storage as the cache backend, install the corresponding optional packages:

```bash
pip install redis                   # required for CACHE_BACKEND=redis
pip install google-cloud-storage    # required for CACHE_BACKEND=gcs
```

These dependencies are not installed by default, so ensure they are available
before selecting the related backend. When using `CACHE_BACKEND=gcs`, set the
GCP credentials described in [GCP Configuration](#gcp-configuration).

### GCP Configuration

Configure the following variables when connecting to Google Cloud services or
the GCS cache backend:

- `GOOGLE_CLOUD_PROJECT` – your Google Cloud project ID.
- `GOOGLE_APPLICATION_CREDENTIALS` – path to a service account JSON key.
- `GCS_BUCKET` – bucket name used when `CACHE_BACKEND=gcs`.
- `GCS_PREFIX` – optional object prefix within the bucket.

If your database runs on Cloud SQL, set `DATABASE_URL` accordingly.

These variables are only needed when using GCP resources—particularly the GCS
cache backend described in [Optional cache backends](#optional-cache-backends).
For local caching and databases, they can be omitted.

#### GitHub Secrets

1. In GitHub, open **Settings → Secrets and variables → Actions**.
2. Add each variable above as a new repository secret using the same name.

#### Local development

Create a `.env` file in the project root (already ignored by Git) and populate it:

```bash
GOOGLE_CLOUD_PROJECT=your-project
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
GCS_BUCKET=your-bucket
GCS_PREFIX=your/prefix
```

Load the variables with a tool like [`python-dotenv`](https://github.com/theskumar/python-dotenv) or by running
`export $(grep -v '^#' .env | xargs)`.

### Deploying via Cloud Run or GKE

#### Prerequisites

- Docker installed and available on your machine.
- `gcloud` CLI configured with your project and default region.
- An Artifact Registry repository to store container images.

#### Build and push the image

```bash
# Build the Docker image and push to Artifact Registry
gcloud auth configure-docker $REGION-docker.pkg.dev
docker build -t $REGION-docker.pkg.dev/$GOOGLE_CLOUD_PROJECT/$AR_REPO/equity-alpha:latest .
docker push $REGION-docker.pkg.dev/$GOOGLE_CLOUD_PROJECT/$AR_REPO/equity-alpha:latest
```

#### Deploy to Cloud Run

```bash
gcloud run deploy equity-alpha \
  --image $REGION-docker.pkg.dev/$GOOGLE_CLOUD_PROJECT/$AR_REPO/equity-alpha:latest \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated
```

#### Deploy to GKE

```bash
gcloud container clusters create-auto $CLUSTER_NAME --region $REGION
gcloud container clusters get-credentials $CLUSTER_NAME --region $REGION
kubectl create deployment equity-alpha \
  --image=$REGION-docker.pkg.dev/$GOOGLE_CLOUD_PROJECT/$AR_REPO/equity-alpha:latest
kubectl expose deployment equity-alpha --type=LoadBalancer --port 80 --target-port 8080
```

#### Troubleshooting

- **Networking** – ensure your Cloud Run service or GKE cluster has access to any required external resources.
- **IAM permissions** – verify that the service account used for deployment can read from Artifact Registry and access GCP services.
- **Environment variables** – confirm that all required variables and secrets are provided during deployment.
