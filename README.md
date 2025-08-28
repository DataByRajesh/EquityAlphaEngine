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
CACHE_GCS_BUCKET=your-bucket
CACHE_GCS_PREFIX=cache/prefix
```

- `QUANDL_API_KEY` – used by `data_pipeline/Macro_data.py` and consumed by
  `data_pipeline/market_data.py` to persist macroeconomic indicators.
- `DATABASE_URL` – consumed throughout the pipeline for database connections.
- `CACHE_GCS_BUCKET` and `CACHE_GCS_PREFIX` – define the Cloud Storage location
  for cached fundamentals in `data_pipeline/cache_utils.py`.

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
pip install redis   # required for CACHE_BACKEND=redis
pip install google-cloud-storage   # required for CACHE_BACKEND=gcs
```

These dependencies are not installed by default, so ensure they are available
before selecting the related backend.

### Deploying to Google Cloud Run

The repository includes a script and YAML definition for deploying the service to [Cloud Run](https://cloud.google.com/run).

#### Prerequisites

- Docker or a compatible container runtime.
- The `gcloud` CLI authenticated with your Google Cloud project.

#### Build and deploy

Use Cloud Build and Cloud Run to build and deploy the container image:

```bash
cd infra/gcp
./deploy-cloud-run.sh
```

The script invokes `gcloud builds submit` to build the image and `gcloud run deploy` to create or update the Cloud Run service.

Alternatively, deploy using the YAML definition:

```bash
gcloud run services replace cloudrun-service.yaml --region <REGION>
```

#### IAM & Networking

Ensure the deploying account has `roles/run.admin`, `roles/iam.serviceAccountUser`, and `roles/cloudbuild.builds.editor`.
To restrict network access or connect to a VPC, adjust the deploy command with `--ingress` and `--vpc-connector` as needed.

