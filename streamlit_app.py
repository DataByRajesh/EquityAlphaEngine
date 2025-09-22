import os, time, logging, random
from typing import Optional
import pandas as pd
import requests
import streamlit as st

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API config
API_URL = os.getenv("API_URL", "https://equity-api-248891289968.europe-west2.run.app").strip()
# Fetch cap for ranking base; UI slices this for display
TOP_FETCH_LIMIT = 100
MAX_RETRIES, RETRY_DELAY = 5, 1
CONNECTION_TIMEOUT, REQUEST_TIMEOUT = 10, 30
HEALTH_CHECK_TIMEOUT = 5

session = requests.Session()
session.mount('http://', requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=20))
session.mount('https://', requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=20))

def check_api_health() -> bool:
    try:
        return session.get(f"{API_URL}/health", timeout=HEALTH_CHECK_TIMEOUT).status_code == 200
    except: return False

def make_request(url, params=None):
    for attempt in range(MAX_RETRIES):
        try:
            return session.get(url, params=params, timeout=(CONNECTION_TIMEOUT, REQUEST_TIMEOUT))
        except (requests.ConnectionError, requests.Timeout):
            time.sleep(RETRY_DELAY*(2**attempt)+random.uniform(0.1,0.5))
    return None

@st.cache_data(ttl=300, show_spinner=False)
def get_data(endpoint, params=None):
    """Fetch data from API with caching and last-good fallback in session_state."""
    cache_key = f"{endpoint}:{str(sorted((params or {}).items()))}"

    # Macro endpoint ignores filters
    url = f"{API_URL}/{endpoint}"
    safe_params = None if endpoint == "get_macro_data" else (params or {})

    resp = make_request(url, params=safe_params)
    if resp and resp.status_code == 200:
        try:
            data = resp.json()
            df = pd.DataFrame(data) if isinstance(data, list) else pd.DataFrame()
            # Store last good result in session_state
            st.session_state.setdefault("_last_good_cache", {})[cache_key] = df
            return df
        except Exception:
            pass

    # Fallback to last good cached result if present
    last_good = st.session_state.get("_last_good_cache", {}).get(cache_key)
    return last_good if last_good is not None else pd.DataFrame()

@st.cache_data(ttl=600, show_spinner=False)
def get_sectors():
    default = ["Technology","Healthcare","Financial Services","Consumer Cyclical","Communication Services"]
    resp = make_request(f"{API_URL}/get_unique_sectors")
    try:
        data = resp.json()
        if isinstance(data, list) and data:
            # Store last good sectors
            st.session_state["_last_good_sectors"] = data
            return data
        return st.session_state.get("_last_good_sectors", default)
    except Exception:
        return st.session_state.get("_last_good_sectors", default)

def format_market_cap(x):
    if pd.isna(x): return x
    return f"£{x/1e9:.1f}B" if x>=1e9 else f"£{x/1e6:.1f}M" if x>=1e6 else f"£{x:,.0f}"

def format_df(df):
    if 'marketCap' in df.columns:
        df['marketCap'] = df['marketCap'].apply(format_market_cap)

    def fmt_pct(x):
        try:
            return f"{float(x):.2%}" if pd.notna(x) else x
        except Exception:
            return x

    def fmt_num(x):
        try:
            return f"{float(x):.2f}" if pd.notna(x) else x
        except Exception:
            return x

    pct_cols = [
        'dividendYield','returnOnEquity','grossMargins','operatingMargins','profitMargins',
        'return_12m','return_3m','vol_21d','vol_252d'
    ]
    num_cols = ['beta','priceToBook','trailingPE','forwardPE','priceToSalesTrailing12Months']

    for c in pct_cols:
        if c in df.columns:
            df[c] = df[c].apply(fmt_pct)
    for c in num_cols:
        if c in df.columns:
            df[c] = df[c].apply(fmt_num)
    return df

# Dashboard
st.set_page_config(page_title="Equity Alpha Engine", layout="wide")
st.title("📊 Equity Alpha Engine Dashboard")
st.caption("Screeners powered by an optimized API with caching, retries, and in-app caching.")

# Default (non-sticky) filter values
DEFAULT_MIN_MKTCAP = 0
DEFAULT_TOP_N = 10
DEFAULT_SECTOR = "All"
DEFAULT_COMPANY = ""

# API health indicator
health_ok = check_api_health()
with st.sidebar:
    if health_ok:
        st.success("API: healthy")
    else:
        st.warning("API: degraded/unavailable")

sectors = ["All"] + get_sectors()

with st.sidebar.expander("🔍 Filter Options", expanded=True):
    with st.form("filter_form"):
        st.markdown("### Customize Your Search")
        col1,col2 = st.columns(2)
        min_mktcap = col1.number_input(
            "Min Market Cap (£)",
            min_value=0,
            value=int(DEFAULT_MIN_MKTCAP),
            step=1_000_000,
            help="Filter out companies below this market cap"
        )
        top_n = col2.slider(
            "Number of Top Stocks",
            min_value=1,
            max_value=100,
            value=int(DEFAULT_TOP_N)
        )
        col3,col4 = st.columns(2)
        company_input = col3.text_input("Company Name", DEFAULT_COMPANY)
        sector_filter = col4.selectbox(
            "Sector",
            sectors,
            index=sectors.index(DEFAULT_SECTOR) if DEFAULT_SECTOR in sectors else 0
        )
        submitted = st.form_submit_button("🚀 Apply Filters")

    if st.button("🗑️ Clear Filters"):
        st.rerun()

min_mktcap_val = int(min_mktcap) if submitted else DEFAULT_MIN_MKTCAP
top_n_val = int(top_n) if submitted else DEFAULT_TOP_N
sector_val = sector_filter if submitted else DEFAULT_SECTOR
company_filter_val = company_input.strip() if submitted else DEFAULT_COMPANY

endpoints = {
    "Undervalued Stocks": "get_undervalued_stocks",
    "Overvalued Stocks": "get_overvalued_stocks",
    "High Quality Stocks": "get_high_quality_stocks",
    "High Earnings Yield": "get_high_earnings_yield_stocks",
    "Top Market Cap Stocks": "get_top_market_cap_stocks",
    "Low Beta Stocks": "get_low_beta_stocks",
    "High Dividend Yield": "get_high_dividend_yield_stocks",
    "High Momentum Stocks": "get_high_momentum_stocks",
    "Low Volatility Stocks": "get_low_volatility_stocks",
    "Short-Term Momentum": "get_top_short_term_momentum_stocks",
    "High Dividend & Low Beta": "get_high_dividend_low_beta_stocks",
    "Top Factor Composite": "get_top_factor_composite_stocks",
    "High Risk Stocks": "get_high_risk_stocks",
    "Top Combined Screener": "get_top_combined_screen_limited",
    "Macro Data Visualization": "get_macro_data",
}

# Render one view at a time (fewer API calls, faster UI)
st.markdown("### Select View")
view_names = list(endpoints.keys())
selected_view = st.radio("Screener", view_names, index=0, horizontal=True)

name = selected_view
st.header(f"📈 {name}")
params = {}
if name != "Macro Data Visualization" and submitted:
    # Always fetch the top TOP_FETCH_LIMIT for consistent ranking; UI will slice
    params = {"min_mktcap": int(min_mktcap_val), "top_n": TOP_FETCH_LIMIT}
    if company_filter_val:
        params["company"] = company_filter_val
    if sector_val != "All":
        params["sector"] = sector_val

    # OHLCV toggle for endpoints that support it
    ohlcv_supported = name != "Macro Data Visualization"
    if ohlcv_supported:
        require_ohlcv = st.checkbox("Only stocks with valid OHLCV", value=False)
        if require_ohlcv:
            params["require_ohlcv"] = True

if not health_ok:
    st.info("API is unavailable. Showing cached results if available.")

df = pd.DataFrame()
query_duration = None
should_query = (name == "Macro Data Visualization") or submitted
if should_query:
    start_time = time.time()
    with st.spinner("Loading data..."):
        df = get_data(endpoints[name], params=params)
    query_duration = time.time() - start_time

if not df.empty:
    # Slice for display only
    df_display = format_df(df.head(int(top_n_val)).copy())
    if name == "Macro Data Visualization":
        df_display['Date'] = pd.to_datetime(df_display['Date'])
        c1, c2 = st.columns(2)
        c1.line_chart(df_display.set_index('Date')['GDP_Growth_YoY'])
        c2.line_chart(df_display.set_index('Date')['Inflation_YoY'])
    st.dataframe(df_display, use_container_width=True)
    st.download_button(
        "Download CSV",
        df_display.to_csv(index=False),
        f"{name.replace(' ', '_').lower()}.csv",
        "text/csv",
    )
    # Metrics panel
    cols = st.columns(3)
    cols[0].metric("Rows", f"{len(df):,}")
    if "Date" in df.columns:
        try:
            last_dt = pd.to_datetime(df["Date"]).max()
            cols[1].metric("Last Date", str(last_dt.date()))
        except Exception:
            cols[1].metric("Last Date", "-")
    else:
        cols[1].metric("Last Date", "-")
    cols[2].metric("Query Time", f"{query_duration:.2f}s" if query_duration is not None else "cached")
else:
    if should_query:
        st.info(f"No {name.lower()} found for this filter/search.")
    else:
        st.info("Adjust filters and click Apply Filters to run the screener.")
