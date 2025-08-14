import streamlit as st
import pandas as pd
import numpy as np
from sqlalchemy import create_engine

try:
    from . import config
except ImportError:  # fallback when run as a script
    import config

st.set_page_config(page_title="InvestWiseUK Multi-Factor Screener", layout="wide")

st.title("📊 InvestWiseUK Multi-Factor Stock Screener")

@st.cache_data
def load_data():
    engine = create_engine(config.DATABASE_URL)
    df = pd.read_sql("SELECT * FROM financial_tbl", engine)
    engine.dispose()
    # Clean NaNs/infs
    for col in ['factor_composite', 'return_12m', 'earnings_yield', 'norm_quality_score']:
        if col in df.columns:
            df[col] = df[col].replace([np.inf, -np.inf], np.nan).fillna(0)
    return df

print("Loading data...")
# Load the data
df = load_data()


# --- Sidebar filters ---
st.sidebar.header("Filter Options")
min_mktcap = st.sidebar.number_input("Min Market Cap", min_value=0)
top_n = st.sidebar.slider("Number of Top Stocks", min_value=5, max_value=50, value=10)


# Ensure we have the necessary columns
required_columns = ['Ticker', 'CompanyName', 'factor_composite', 'return_12m', 'earnings_yield', 'norm_quality_score', 'marketCap']
if not all(col in df.columns for col in required_columns):
    st.error("Data is missing required columns. Please check your database.")

# --- Filter and process data ---
# 1. Filter by market cap
filtered = df[df['marketCap'] >= min_mktcap]

# 2. For each ticker, select the row with the latest date (or highest factor_composite)
if 'Date' in filtered.columns:
    # Use latest date per ticker
    filtered = filtered.sort_values('Date').groupby('Ticker', as_index=False).last()
else:
    # Use highest factor_composite per ticker
    filtered = filtered.sort_values('factor_composite', ascending=False).groupby('Ticker', as_index=False).first()

# 3. Sort by factor_composite
filtered = filtered.sort_values('factor_composite', ascending=False).reset_index(drop=True)

# 4. Ensure CompanyName exists — if not, fetch it separately or add placeholder
if 'CompanyName' not in filtered.columns:
    filtered['CompanyName'] = "Unknown Company"

# 5. Add proper rank
filtered['rank'] = filtered.index + 1

st.markdown(f"### Top {top_n} UK Stocks by Multi-Factor Composite Score")
cols_to_show = ['Ticker','CompanyName','factor_composite','return_12m','earnings_yield','norm_quality_score','marketCap','rank']
cols_to_show = [c for c in cols_to_show if c in filtered.columns]
st.dataframe(filtered.head(top_n)[cols_to_show])

st.markdown("#### 📈 Factor Composite Score Bar Chart")
st.bar_chart(filtered.head(top_n).set_index('Ticker')['factor_composite'])

st.download_button(
    label="Download as CSV",
    data=filtered.head(top_n).to_csv(index=False),
    file_name='screener_output.csv',
    mime='text/csv',
)

st.info("Uses InvestWiseUK analytics engine pipeline. Replace with your real factor output for production if demoing.")