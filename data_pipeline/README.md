
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
- Local JSON cache used for fundamentals (`cache_utils.py`)
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

## 📝 Author's Note
This guide assumes a local dev environment.
Use this setup for testing, development, and proof of concept.

---

## ✅ Project by Rajesh Kumar Alagesan
