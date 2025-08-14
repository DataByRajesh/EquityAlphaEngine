
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

### 3️⃣ Configure Your `config.py`
- ✅ Check your database path (`DB_PATH`)
- ✅ Set your cache expiry settings
- ✅ Ensure your Gmail credentials are correct (optional for alerts)

### 4️⃣ Initialize Cache & Database (Optional)
- Cache will create itself on first run
- SQLite database should exist or be created by `UK_data.py`

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
- Cache backend configurable via environment variables:
  - `CACHE_BACKEND` – `local` (default), `redis` or `s3`
  - `CACHE_REDIS_URL` – Redis connection string when using the Redis backend
  - `CACHE_S3_BUCKET` / `CACHE_S3_PREFIX` – S3 bucket (and optional key prefix)
- Local JSON cache is used when `CACHE_BACKEND` is `local` (`cache_utils.py`)
- SQLite database stores computed financials (`data/stocks_data.db`)
- Gmail alerts use credentials from `credentials.json` (optional)

---

## ☁️ Persistent Storage Recommendations
For deployments requiring durable storage of datasets or logs, point the
`DATA_DIR`, `CACHE_DIR`, and `LOG_DIR` environment variables to cloud object
storage such as:

- **Amazon S3**
- **Supabase Storage**

These services keep pipeline outputs across restarts and can be mounted or
accessed via SDKs, allowing the application to treat them like local folders.

---

## ✅ When Ready for Cloud Deployment
- Switch to a hosted DB like Supabase/PostgreSQL
- Consider using an online cache or removing file-based cache
- Set up environment variables for sensitive credentials

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
