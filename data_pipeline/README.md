
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
- ✅ Ensure your Gmail credentials are correct (optional for alerts)

### 4️⃣ Initialize Cache & Database (Optional)
- Cache will create itself on first run
- Ensure your hosted database is reachable by the `DATABASE_URL`

---

## ✅ Running the Data Pipeline Locally
This will fetch data, compute factors, and update the database.
```
python UK_data.py --start_date 2020-01-01 --end_date 2025-07-17
```

---

## ✅ Running the Streamlit Screener Locally
From inside `data_pipeline/` folder:
```
streamlit run streamlit_screener.py
```

- 🎛️ Use sidebar filters to refine your stock list
- 📈 View multi-factor rankings and charts
- 💾 Download the output CSV

---

## ✅ Notes on Cache & Data Persistence
- Local JSON cache used for fundamentals (`cache_utils.py`)
- Hosted database stores computed financials (configured via `DATABASE_URL`)
- Gmail alerts use credentials from `credentials.json` (optional)

---

## ☁️ Streamlit Cloud Deployment
When deploying on Streamlit Cloud:
- Add a `DATABASE_URL` entry to `.streamlit/secrets.toml`.
- In the Streamlit Cloud dashboard, open **App settings → Secrets** and paste the contents of your `secrets.toml` so the app can access the hosted database.
- Consider using an online cache or removing file-based cache for fully stateless deployments.

For persistent storage of other outputs or logs, point `DATA_DIR`, `CACHE_DIR`, and `LOG_DIR` to cloud object storage such as Amazon S3 or Supabase Storage.

---

## 📝 Author's Note
This guide assumes a local dev environment.
Use this setup for testing, development, and proof of concept.

---

## ✅ Project by Rajesh Kumar Alagesan
