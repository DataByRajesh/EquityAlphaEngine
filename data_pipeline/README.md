
# 📊 EquityAlphaEngine - Local Deployment Guide

## Project Overview

**EquityAlphaEngine** is a UK Equity Analytics Platform that:
- Fetches financial fundamentals and historical data
- Computes multi-factor scoring models
- Caches data locally with expiry control
- Provides an interactive stock screener via Streamlit
- Sends Gmail alerts on data pipeline events

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

### 4️⃣ Initialize Cache & Database (Optional)
- Cache will create itself on first run
- Ensure your hosted database is reachable by the `DATABASE_URL`

---

## 🔑 Required API Credentials

Set these environment variables or Streamlit secrets so the pipeline can
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

Example `.streamlit/secrets.toml`:

```toml
QUANDL_API_KEY = "your_quandl_key"
GMAIL_CREDENTIALS_FILE = "credentials.json"
GMAIL_TOKEN_FILE = "token.json"
```

---

## ✅ Running the Data Pipeline Locally
This will fetch data, compute factors, and update the database.
```
python UK_data.py --start_date 2020-01-01 --end_date 2025-07-17
```

---

## ✅ Running the Streamlit Screener Locally
From the project root:
```
streamlit run streamlit_app.py
```

This wrapper imports `data_pipeline.streamlit_screener` so the app can be
deployed easily on services like Streamlit Community Cloud. Set the app's entry
point to `streamlit_app.py` when deploying there.

- 🎛️ Use sidebar filters to refine your stock list
- 📈 View multi-factor rankings and charts
- 💾 Download the output CSV

---


## ✅ Notes on Cache & Data Persistence

- **Cache backend** configurable via environment variables:
  - `CACHE_BACKEND` – `local` (default), `redis`, or `s3`
  - `CACHE_REDIS_URL` – Redis connection string when using the Redis backend
  - `CACHE_S3_BUCKET` / `CACHE_S3_PREFIX` – S3 bucket (and optional key prefix)
  - **In-memory fundamentals cache** keeps entries for the session and only writes modified tickers back to the chosen backend (`cache_utils.py`)
- Optional packages for remote backends:

  ```bash
  pip install redis   # required for CACHE_BACKEND=redis
  pip install boto3   # required for CACHE_BACKEND=s3
  ```
- **Database configuration**:
  1. The app first checks the `DATABASE_URL` environment variable (recommended for production).
  2. If not set, it tries `st.secrets["DATABASE_URL"]` (common on Streamlit Cloud).
  3. If still missing, it falls back to a **local SQLite database** (`data/app.db`) for development/testing.
- **Hosted database** (e.g., Supabase/PostgreSQL) is strongly recommended for production to ensure persistence across runs.
- Gmail alerts use credentials from `GMAIL_CREDENTIALS_FILE` (defaults to
  `credentials.json`) and store the token in `GMAIL_TOKEN_FILE`.

---

## ☁️ Streamlit Cloud Deployment
When deploying on Streamlit Cloud:
- Add a `DATABASE_URL` entry to `.streamlit/secrets.toml`.
- In the Streamlit Cloud dashboard, open **App settings → Secrets** and paste the contents of your `secrets.toml` so the app can access the hosted database.
- Consider using an online cache or removing file-based cache for fully stateless deployments.

For persistent storage of other outputs or logs, point `DATA_DIR`, `CACHE_DIR`, and `LOG_DIR` to cloud object storage such as Amazon S3 or Supabase Storage.

---

## ☁️ Deploy to Streamlit Cloud
1. **Push the repo**
   - Commit and push your project to GitHub; Streamlit Cloud builds directly from your repository.
2. **Create a new app**
   - Go to [streamlit.io/cloud](https://streamlit.io/cloud) and connect your GitHub account.
   - Choose your repository and branch, then set the **App file** to `data_pipeline/streamlit_screener.py`.
3. **Configure secrets and environment variables**
   - In the app dashboard, open **Settings → Secrets** and add values such as:
     ```toml
     DATABASE_URL = "postgresql://user:pass@host/db"
     GMAIL_USER = "your_email"
     GMAIL_PASS = "your_password"
     ```
   - Any environment variable (e.g., `DATA_DIR`, `CACHE_DIR`, `LOG_DIR`) can be defined here.
4. **Persist your data**
   - Streamlit Cloud containers are ephemeral—use a hosted database like Supabase/PostgreSQL for persistence.
   - Point `DATABASE_URL` to the hosted DB and avoid relying on local JSON caches.
5. **Manage cache**
   - Remove file-based cache folders before deploying or clear them via **⚙️ Settings → Clear cache**.
   - From code you can call `st.cache_data.clear()` to reset cached data when needed.

Once configured, click **Deploy** and Streamlit Cloud will build and run the screener automatically.

---

## 📝 Author's Note
This guide assumes a local dev environment.
Use this setup for testing, development, and proof of concept.

---

## ✅ Project by Rajesh Kumar Alagesan
