
# 📊 EquityAlphaEngine - Local Deployment Guide

## Project Overview

**EquityAlphaEngine** is a UK Equity Analytics Platform that:
- Fetches financial fundamentals and historical data
- Ingests UK macroeconomic indicators (GDP growth and inflation)
- Computes multi-factor scoring models
- Caches data locally with expiry control
- Outputs data that can be visualized in tools like Tableau or PowerBI
- Sends Gmail alerts on data pipeline events

---

## Required Environment Variables

Create a `.env` file with entries such as:

```env
QUANDL_API_KEY=your_quandl_api_key
GMAIL_CREDENTIALS_FILE=credentials.json
GMAIL_TOKEN_FILE=token.json
DATABASE_URL=postgresql://user:password@host:5432/database
```

- `QUANDL_API_KEY` – required for macro indicators and UK market data; missing
  it blocks macro/UK data retrieval.
- `GMAIL_CREDENTIALS_FILE` – path to Gmail OAuth credentials.
- `GMAIL_TOKEN_FILE` – location to store the Gmail OAuth token.
- `DATABASE_URL` – connection string to the database.

Additional optional variables include `CACHE_BACKEND`, `CACHE_REDIS_URL`,
`CACHE_GCS_BUCKET`, `CACHE_GCS_PREFIX`, and `MAX_THREADS`.

---

## ✅ Local Deployment Checklist

### 1️⃣ Clone the Project Locally
```
git clone <your-repo-url>
cd EquityAlphaEngine/data_pipeline
```

### 2️⃣ Set Up Virtual Environment (Optional but Recommended)
```
python -m venv env
source env/bin/activate  # or env\Scripts\activate on Windows
pip install -r requirements.txt
```

### 3️⃣ Configure Your Environment
- ✅ Set the `DATABASE_URL` for a hosted database (e.g., Supabase/PostgreSQL)
- ✅ Set your cache expiry settings
- ✅ Ensure your Gmail credentials are available (optional for alerts). Use
  `GMAIL_CREDENTIALS_FILE` and `GMAIL_TOKEN_FILE` to override default paths.

#### Required credentials

Set the following variables in a `.env` file:

```env
QUANDL_API_KEY=your_quandl_key
DATABASE_URL=postgresql://user:password@host:5432/database
CACHE_GCS_BUCKET=your-bucket
CACHE_GCS_PREFIX=cache/prefix
```

- `QUANDL_API_KEY` – used by `Macro_data.py` to pull macroeconomic data.
- `DATABASE_URL` – consumed by `config.py` and all database helpers.
- `CACHE_GCS_BUCKET` and `CACHE_GCS_PREFIX` – identify the Cloud Storage
  location for cached fundamentals in `cache_utils.py`.

### 4️⃣ Initialize Cache & Database (Optional)
- Cache will create itself on first run
- Ensure your hosted database is reachable by the `DATABASE_URL`

---

## 🔑 Required API Credentials

Set these environment variables so the pipeline can
access external services:

- `QUANDL_API_KEY` – used to download macroeconomic data. **If this key is
  missing, macro data cannot be fetched.**
- `GMAIL_CREDENTIALS_FILE` – path to the Gmail API OAuth credentials JSON.
- `GMAIL_TOKEN_FILE` – path to the Gmail OAuth token file generated after
  authorization.

Example `.env` file:

```bash
QUANDL_API_KEY=your_quandl_key
GMAIL_CREDENTIALS_FILE=credentials.json
GMAIL_TOKEN_FILE=token.json
```

---

## ✅ Running the Data Pipeline Locally
This will fetch data, compute factors, and update the database.
```
python market_data.py --start_date 2020-01-01 --end_date 2025-07-17
```
The pipeline also pulls UK GDP growth and inflation figures and stores them in
the `macro_data_tbl` table.

## ✅ Notes on Cache & Data Persistence

- **Cache backend** configurable via environment variables:
  - `CACHE_BACKEND` – `local` (default), `redis`, or `gcs`
  - `CACHE_REDIS_URL` – Redis connection string when using the Redis backend
  - `CACHE_GCS_BUCKET` / `CACHE_GCS_PREFIX` – Cloud Storage bucket (and optional key prefix)
  - **In-memory fundamentals cache** keeps entries for the session and only writes modified tickers back to the chosen backend (`cache_utils.py`)
- Optional packages for remote backends:

  ```bash
  pip install redis   # required for CACHE_BACKEND=redis
  pip install google-cloud-storage   # required for CACHE_BACKEND=gcs
  ```
   - **Database configuration**:
      1. The app first checks the `DATABASE_URL` environment variable (recommended for production).
      2. If not set, it falls back to a **local SQLite database** (`data/app.db`) for development/testing.
      - **Hosted database** (e.g., Supabase/PostgreSQL) is strongly recommended for production to ensure persistence across runs.
      - Gmail alerts use credentials from `GMAIL_CREDENTIALS_FILE` (defaults to
        `credentials.json`) and store the token in `GMAIL_TOKEN_FILE`.

---

## 📝 Author's Note
This guide assumes a local dev environment.
Use this setup for testing, development, and proof of concept.

---

## ✅ Project by Rajesh Kumar Alagesan
