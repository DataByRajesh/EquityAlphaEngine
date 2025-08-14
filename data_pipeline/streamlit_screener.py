import logging
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import SQLAlchemyError

try:
    from . import config, UK_data
except ImportError:  # fallback when run as a script
    import config
    import UK_data

# The screener expects `DATABASE_URL` to point to a hosted PostgreSQL database
# such as Supabase.  Streamlit Cloud users should set this in `.streamlit/secrets.toml`.

st.set_page_config(page_title="InvestWiseUK Multi-Factor Screener", layout="wide")

st.title("📊 InvestWiseUK Multi-Factor Stock Screener")

st.sidebar.header("Filter Options")
st.sidebar.info(
    "Requires `DATABASE_URL` to connect to a hosted database such as "
    "Supabase/PostgreSQL. If omitted, falls back to a local SQLite database."
)

db_type = (
    "local SQLite" if config.DATABASE_URL.startswith("sqlite://") else "hosted"
)
st.sidebar.caption(f"Using {db_type} database")
years = st.sidebar.number_input("Years of history", min_value=1, value=10)
min_mktcap = st.sidebar.number_input("Min Market Cap", min_value=0)
top_n = st.sidebar.slider("Number of Top Stocks", min_value=5, max_value=50, value=10)

today = datetime.today()
end_date = today.strftime("%Y-%m-%d")
start_date = (today - timedelta(days=years * 365)).strftime("%Y-%m-%d")


@st.cache_data(show_spinner=False)
def load_data(start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch data and load from database, caching the result."""

    engine = create_engine(config.DATABASE_URL)
    try:
        inspector = inspect(engine)
        needs_fetch = True
        if inspector.has_table("financial_tbl"):
            # Check existing data range
            date_range = pd.read_sql(
                "SELECT MIN(Date) AS min_date, MAX(Date) AS max_date FROM financial_tbl",
                engine,
            )
            if not date_range.empty:
                min_date = pd.to_datetime(date_range["min_date"].iloc[0])
                max_date = pd.to_datetime(date_range["max_date"].iloc[0])
                if pd.notna(min_date) and pd.notna(max_date):
                    if min_date <= pd.to_datetime(start_date) and max_date >= pd.to_datetime(end_date):
                        needs_fetch = False

        if needs_fetch:
            try:
                UK_data.main(config.FTSE_100_TICKERS, start_date, end_date)
            except Exception as exc:  # pragma: no cover - best effort logging
                logging.error("Error fetching data: %s", exc)
            inspector = inspect(engine)

        if not inspector.has_table("financial_tbl"):
            st.error(
                "Table `financial_tbl` not found. Please run `python data_pipeline/UK_data.py` to populate the database.",
            )
            return pd.DataFrame()

        df = pd.read_sql("SELECT * FROM financial_tbl", engine)
    except SQLAlchemyError as exc:
        logging.error("Error loading financial data: %s", exc)
        st.error(
            "Unable to load financial data. Please ensure the database is initialized.",
        )
        return pd.DataFrame()
    finally:
        engine.dispose()

    for col in [
        "factor_composite",
        "return_12m",
        "earnings_yield",
        "norm_quality_score",
    ]:
        if col in df.columns:
            df[col] = df[col].replace([np.inf, -np.inf], np.nan).fillna(0)
    return df


with st.spinner("Loading data..."):
    df = load_data(start_date, end_date)

if df is None or df.empty:
    st.stop()


# Ensure we have the necessary columns
required_columns = [
    "Ticker",
    "CompanyName",
    "factor_composite",
    "return_12m",
    "earnings_yield",
    "norm_quality_score",
    "marketCap",
]
if not all(col in df.columns for col in required_columns):
    st.error("Data is missing required columns. Please check your database.")

# --- Filter and process data ---
# 1. Filter by market cap
filtered = df[df["marketCap"] >= min_mktcap]

# 2. For each ticker, select the row with the latest date (or highest factor_composite)
if "Date" in filtered.columns:
    # Use latest date per ticker
    filtered = filtered.sort_values("Date").groupby("Ticker", as_index=False).last()
else:
    # Use highest factor_composite per ticker
    filtered = (
        filtered.sort_values("factor_composite", ascending=False)
        .groupby("Ticker", as_index=False)
        .first()
    )

# 3. Sort by factor_composite
filtered = filtered.sort_values("factor_composite", ascending=False).reset_index(drop=True)

# 4. Ensure CompanyName exists — if not, fetch it separately or add placeholder
if "CompanyName" not in filtered.columns:
    filtered["CompanyName"] = "Unknown Company"

# 5. Add proper rank
filtered["rank"] = filtered.index + 1

st.markdown(f"### Top {top_n} UK Stocks by Multi-Factor Composite Score")
cols_to_show = [
    "Ticker",
    "CompanyName",
    "factor_composite",
    "return_12m",
    "earnings_yield",
    "norm_quality_score",
    "marketCap",
    "rank",
]
cols_to_show = [c for c in cols_to_show if c in filtered.columns]
st.dataframe(filtered.head(top_n)[cols_to_show])

st.markdown("#### 📈 Factor Composite Score Bar Chart")
st.bar_chart(filtered.head(top_n).set_index("Ticker")["factor_composite"])

st.download_button(
    label="Download as CSV",
    data=filtered.head(top_n).to_csv(index=False),
    file_name="screener_output.csv",
    mime="text/csv",
)

st.info(
    "Uses InvestWiseUK analytics engine pipeline. Replace with your real factor output for production if demoing."
)

