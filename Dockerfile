# Dockerfile for EquityAlphaEngine
#
# Required environment variables:
#   QUANDL_API_KEY        Quandl API key for macroeconomic data
#   DATABASE_URL          Database connection string
#   AWS_ACCESS_KEY_ID     AWS credentials for S3 cache backend
#   AWS_SECRET_ACCESS_KEY AWS credentials for S3 cache backend
#   AWS_DEFAULT_REGION    Region for AWS resources
#   CACHE_S3_BUCKET       S3 bucket used when CACHE_BACKEND=s3
#   CACHE_S3_PREFIX       Prefix for cached data in S3 bucket
#   MAX_THREADS           Optional: override default concurrency
#
# Build with:
#   docker build -t equity-alpha-engine .
#
# Run with environment variables (e.g. via --env-file):
#   docker run --rm --env-file .env equity-alpha-engine --years 10

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENTRYPOINT ["python", "data_pipeline/market_data.py"]
