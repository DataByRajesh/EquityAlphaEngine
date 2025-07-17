
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
- SQLite database stores computed financials (`data/stocks_data.db`)
- Gmail alerts use credentials from `credentials.json` (optional)

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
