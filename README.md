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
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-west-2
CACHE_S3_BUCKET=your-bucket
CACHE_S3_PREFIX=cache/prefix
```

- `QUANDL_API_KEY` – used by `data_pipeline/Macro_data.py` and consumed by
  `data_pipeline/market_data.py` to persist macroeconomic indicators.
- `DATABASE_URL` – consumed throughout the pipeline for database connections.
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` and `AWS_DEFAULT_REGION` –
  authenticate to Amazon S3 when using the S3 cache backend.
- `CACHE_S3_BUCKET` and `CACHE_S3_PREFIX` – define the S3 location for cached
  fundamentals in `data_pipeline/cache_utils.py`.

### Dashboard integration

Connect business intelligence tools such as Tableau or PowerBI directly to the
database populated by the data pipeline to build visual dashboards.

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

The pipeline defaults to a local filesystem cache. To use Redis or Amazon S3
as the cache backend, install the corresponding optional packages:

```bash
pip install redis   # required for CACHE_BACKEND=redis
pip install boto3   # required for CACHE_BACKEND=s3
```

These dependencies are not installed by default, so ensure they are available
before selecting the related backend. When using `CACHE_BACKEND=s3`, set the
AWS credentials described in [AWS Configuration](#aws-configuration).

### AWS Configuration

Configure the following variables when connecting to AWS services such as RDS
or the S3 cache backend:

- `AWS_ACCESS_KEY_ID` – access key for an IAM user with S3 permissions.
- `AWS_SECRET_ACCESS_KEY` – secret key associated with the IAM user.
- `AWS_DEFAULT_REGION` – AWS region for your resources.
- `CACHE_S3_BUCKET` – bucket name used when `CACHE_BACKEND=s3`.
- `CACHE_S3_PREFIX` – optional key prefix within the bucket.

If your database runs on AWS RDS, set `DATABASE_URL` accordingly. Example:

```bash
DATABASE_URL=postgresql://user:pass@mydb.xxxxx.us-east-1.rds.amazonaws.com:5432/dbname
```

These variables are only needed when using AWS resources—particularly the S3
cache backend described in [Optional cache backends](#optional-cache-backends).
For local caching and databases, they can be omitted.

### AWS Configuration

To enable Amazon S3 as a cache backend, define the following environment variables:

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_DEFAULT_REGION`
- `CACHE_S3_BUCKET`
- `CACHE_S3_PREFIX`

#### GitHub Secrets

1. In GitHub, open **Settings → Secrets and variables → Actions**.
2. Add each variable above as a new repository secret using the same name.

#### Local development

Create a `.env` file in the project root (already ignored by Git) and populate it:

```bash
AWS_ACCESS_KEY_ID=YOUR_KEY
AWS_SECRET_ACCESS_KEY=YOUR_SECRET
AWS_DEFAULT_REGION=us-east-1
CACHE_S3_BUCKET=your-bucket
CACHE_S3_PREFIX=your/prefix
```

Load the variables with a tool like [`python-dotenv`](https://github.com/theskumar/python-dotenv) or by running `export $(grep -v '^#' .env | xargs)`.

