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

# Initialize session state for filters
if "min_mktcap" not in st.session_state:
    st.session_state.min_mktcap = 0
if "top_n" not in st.session_state:
    st.session_state.top_n = 10
if "sector_filter" not in st.session_state:
    st.session_state.sector_filter = "All"
if "company_filter" not in st.session_state:
    st.session_state.company_filter = ""

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
            value=int(st.session_state.min_mktcap),
            step=1_000_000,
            help="Filter out companies below this market cap"
        )
        top_n = col2.slider(
            "Number of Top Stocks",
            min_value=1,
            max_value=100,
            value=int(st.session_state.top_n)
        )
        col3,col4 = st.columns(2)
        company_input = col3.text_input("Company Name", st.session_state.company_filter)
        sector_filter = col4.selectbox(
            "Sector",
            sectors,
            index=sectors.index(st.session_state.sector_filter) if st.session_state.sector_filter in sectors else 0
        )
        submitted = st.form_submit_button("🚀 Apply Filters")

    if st.button("🗑️ Clear Filters"):
        st.session_state.min_mktcap = 0
        st.session_state.top_n = 10
        st.session_state.sector_filter = "All"
        st.session_state.company_filter = ""
        st.rerun()

if submitted:
    st.session_state.min_mktcap = min_mktcap
    st.session_state.top_n = top_n
    st.session_state.sector_filter = sector_filter
    st.session_state.company_filter = company_input.strip()

min_mktcap_val = st.session_state.min_mktcap
top_n_val = st.session_state.top_n
sector_val = st.session_state.sector_filter
company_filter_val = st.session_state.company_filter

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
if name != "Macro Data Visualization":
    params = {"min_mktcap": int(min_mktcap_val), "top_n": int(top_n_val)}
    if company_filter_val:
        params["company"] = company_filter_val
    if sector_val != "All":
        params["sector"] = sector_val

    # OHLCV toggle for endpoints that support it
    ohlcv_supported = name not in {
        "Undervalued Stocks", "Overvalued Stocks", "Top Combined Screener", "Macro Data Visualization"
    }
    if ohlcv_supported:
        require_ohlcv = st.checkbox("Only stocks with valid OHLCV", value=False)
        if require_ohlcv:
            params["require_ohlcv"] = True

if not health_ok:
    st.info("API is unavailable. Showing cached results if available.")

with st.spinner("Loading data..."):
    df = get_data(endpoints[name], params=params)

if not df.empty:
    df_display = format_df(df.copy())
    if name == "Macro Data Visualization":
        df_display['Date'] = pd.to_datetime(df_display['Date'])
        c1, c2 = st.columns(2)
        c1.line_chart(df_display.set_index('Date')['GDP_Growth_YoY'])
        c2.line_chart(df_display.set_index('Date')['Inflation_YoY'])
    st.dataframe(df_display, use_container_width=True)
    st.download_button(
        "Download CSV",
        df.to_csv(index=False),
        f"{name.replace(' ', '_').lower()}.csv",
        "text/csv",
    )
else:
    st.info(f"No {name.lower()} found for this filter/search.")
