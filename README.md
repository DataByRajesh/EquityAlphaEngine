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

### Deploying to AWS ECS

#### Prerequisites

- Docker installed and available on your machine.
- AWS CLI configured with credentials and default region.
- An Amazon ECR repository to store container images.
- An ECS task-definition JSON template describing the service.

#### Build and push the image

```bash
# Build the Docker image
docker build -t $ECR_REPO_URI:latest .

# Authenticate Docker to Amazon ECR and push the image
aws ecr get-login-password --region $AWS_DEFAULT_REGION | \
  docker login --username AWS --password-stdin $ECR_REPO_URI
docker push $ECR_REPO_URI:latest
```

#### Launch or update the service

Use the AWS CLI to register the task definition and update the ECS service:

```bash
aws ecs register-task-definition --cli-input-json file://task-definition.json
aws ecs update-service --cluster $CLUSTER_NAME \
  --service $SERVICE_NAME --force-new-deployment
```

#### Troubleshooting

- **Networking** – verify that the service's subnets and security groups allow the necessary inbound and outbound traffic.
- **IAM permissions** – ensure the task execution role can pull from ECR and access any required AWS services.
- **Environment variables** – confirm that all required variables and secrets are provided in the task definition or ECS service configuration.

