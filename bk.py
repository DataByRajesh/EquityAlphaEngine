# standard libraries
import os
import time
import logging
import urllib.parse
import random
from typing import Optional

# third-party libraries
import pandas as pd
import requests

# local application imports
import streamlit as st
from data_pipeline.db_connection import get_db
from data_pipeline.utils import get_secret

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API URL configuration from environment variable or default
# Clean the URL to remove any carriage returns or whitespace that cause DNS issues
raw_api_url = os.getenv("API_URL", "https://equity-api-248891289968.europe-west2.run.app")
API_URL = raw_api_url.strip().replace('\r', '').replace('\n', '')
logger.info(f"Using API URL: {API_URL}")

# Optimized connection configuration for Cloud Run
MAX_RETRIES = 5
RETRY_DELAY = 1  # seconds, initial delay
CONNECTION_TIMEOUT = 10  # seconds, reduced for Cloud Run
REQUEST_TIMEOUT = 30  # seconds, reduced for Cloud Run
HEALTH_CHECK_TIMEOUT = 5  # seconds, for health checks

# Create a session for connection pooling
http_session = requests.Session()
http_session.mount('http://', requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=20))
http_session.mount('https://', requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=20))

def check_api_health() -> bool:
    """Check if the API service is healthy before making requests."""
    try:
        logger.debug("Checking API health...")
        response = http_session.get(f"{API_URL}/health", timeout=HEALTH_CHECK_TIMEOUT)
        if response.status_code == 200:
            logger.debug("API health check passed")
            return True
        else:
            logger.warning(f"API health check failed with status: {response.status_code}")
            return False
    except Exception as e:
        logger.warning(f"API health check failed: {e}")
        return False


def make_request_with_retry(url, params=None, max_retries=MAX_RETRIES):
    """Make HTTP request with retry logic, exponential backoff, and jitter."""
    last_exception = None

    # Perform health check for the first attempt
    if not check_api_health():
        logger.warning("API health check failed, but proceeding with request...")

    for attempt in range(max_retries):
        try:
            logger.debug(f"Request attempt {attempt + 1}/{max_retries} to {url}")
            
            # Use http_session for connection pooling
            response = http_session.get(
                url, 
                params=params, 
                timeout=(CONNECTION_TIMEOUT, REQUEST_TIMEOUT)
            )
            
            logger.debug(f"Request successful with status {response.status_code}")
            return response
            
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            last_exception = e
            if attempt < max_retries - 1:
                # Exponential backoff with jitter
                base_wait = RETRY_DELAY * (2 ** attempt)
                jitter = random.uniform(0.1, 0.5)  # Add jitter to prevent thundering herd
                wait_time = base_wait + jitter
                
                logger.warning(f"Request attempt {attempt + 1} failed: {e}. Retrying in {wait_time:.2f} seconds...")
                time.sleep(wait_time)
            else:
                logger.error(f"All {max_retries} request attempts failed. Last error: {e}")
                
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error during request: {e}")
            raise e
            
        except Exception as e:
            logger.error(f"Unexpected error during request: {e}")
            raise e

    # If we get here, all retries failed
    raise last_exception
@st.cache_data
def get_data(endpoint, params=None):
    """Enhanced get_data function with retry logic and better error handling."""
    try:
        logger.info(f"Fetching data from endpoint: {endpoint}")
        response = make_request_with_retry(f"{API_URL}/{endpoint}", params=params)

        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                logger.info(f"Successfully retrieved {len(data)} records from {endpoint}")
                return pd.DataFrame(data)
            else:
                logger.warning(f"No data returned from {endpoint}")
                return pd.DataFrame()
        elif response.status_code == 400:
            st.warning(f"Invalid request parameters: {response.text}")
            return pd.DataFrame()
        elif response.status_code == 503:
            st.warning("Database temporarily unavailable. Please try again later.")
            return pd.DataFrame()
        else:
            st.error(f"API error: {response.status_code} - {response.text}")
            return pd.DataFrame()
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
        logger.error(f"Connection/timeout error for {endpoint}: {e}")
        st.error(f"Connection error for {endpoint}. Please check your connection and try again.")
        return pd.DataFrame()
    except ValueError as e:
        logger.error(f"JSON parsing error for {endpoint}: {e}")
        st.error(f"Error parsing response data: {e}")
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Unexpected error for {endpoint}: {e}")
        st.error(f"Unexpected error: {e}")
        return pd.DataFrame()

@st.cache_data
def get_sectors():
    """Enhanced get_sectors function with retry logic and better error handling."""
    default_sectors = ["Technology", "Healthcare", "Financial Services", "Consumer Cyclical", "Communication Services"]
    
    try:
        logger.info("Fetching sectors from API")
        response = make_request_with_retry(f"{API_URL}/get_unique_sectors")
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                logger.info(f"Successfully retrieved {len(data)} sectors")
                return data
            else:
                logger.warning("Invalid sectors data format or empty list")
                st.warning("Invalid sectors data format. Using default list.")
                return default_sectors
        else:
            logger.warning(f"Failed to fetch sectors: {response.status_code}")
            st.warning(f"Failed to fetch sectors: {response.status_code}. Using default list.")
            return default_sectors
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
        logger.error(f"Connection/timeout error fetching sectors: {e}")
        st.warning("Connection error fetching sectors. Using default list.")
        return default_sectors
    except Exception as e:
        logger.error(f"Unexpected error fetching sectors: {e}")
        st.warning(f"Error fetching sectors: {e}. Using default list.")
        return default_sectors


def format_market_cap(x):
    if pd.isna(x):
        return x
    if x >= 1e9:
        return f"£{x/1e9:.1f}B"
    elif x >= 1e6:
        return f"£{x/1e6:.1f}M"
    else:
        return f"£{x:,.0f}"


def format_dataframe(df):
    if 'marketCap' in df.columns:
        df['marketCap'] = df['marketCap'].apply(format_market_cap)
    return df


# Ensure proper session handling using `get_db()`
session = next(get_db())
try:
    st.set_page_config(page_title="Equity Alpha Engine", layout="wide")
    st.title("📊 Equity Alpha Engine Dashboard")

    sectors = get_sectors()
    sector_options = ["All"] + sectors

    with st.sidebar.expander("🔍 Filter Options", expanded=True):
        with st.form("filter_form"):
            st.markdown("### Customize Your Search")

            col1, col2 = st.columns(2)
            with col1:
                min_mktcap = st.number_input("Min Market Cap (£)", min_value=0, value=0, placeholder="e.g., 1000000000")
            with col2:
                top_n = st.slider("Number of Top Stocks", min_value=5, max_value=50, value=10)

            col3, col4 = st.columns(2)
            with col3:
                company_filter = st.text_input("Company Name", placeholder="e.g., Apple Inc.")
            with col4:
                sector_filter = st.selectbox("Sector", sector_options)

            st.markdown("---")
            submitted = st.form_submit_button("🚀 Apply Filters", type="primary")

    if submitted:
        st.session_state["min_mktcap"] = min_mktcap
        st.session_state["top_n"] = top_n
        st.session_state["company_filter"] = company_filter
        st.session_state["sector_filter"] = sector_filter

    # Define filter values from session state
    min_mktcap_val = st.session_state.get("min_mktcap", 0)
    top_n_val = st.session_state.get("top_n", 10)
    company_filter_val = st.session_state.get("company_filter", "")
    sector_filter_val = st.session_state.get("sector_filter", "All")

    # Define Tabs
    TABS = [
        "Undervalued Stocks",
        "Overvalued Stocks",
        "High Quality Stocks",
        "High Earnings Yield",
        "Top Market Cap Stocks",
        "Low Beta Stocks",
        "High Dividend Yield",
        "High Momentum Stocks",
        "Low Volatility Stocks",
        "Short-Term Momentum",
        "High Dividend & Low Beta",
        "Top Factor Composite",
        "High Risk Stocks",
        "Top Combined Screener",
        "Macro Data Visualization",
    ]
    tabs = st.tabs(TABS)

    with tabs[0]:
        st.header("💰 Undervalued Stocks")
        with st.spinner("Loading undervalued stocks..."):
            params = {"min_mktcap": min_mktcap_val, "top_n": top_n_val}
            if company_filter_val:
                params["company"] = company_filter_val
            if sector_filter_val != "All":
                params["sector"] = sector_filter_val
            df_undervalued = get_data("get_undervalued_stocks", params=params)
            if not df_undervalued.empty:
                df_display = format_dataframe(df_undervalued.copy())
                st.dataframe(df_display)
                st.download_button(
                    label="Download as CSV",
                    data=df_undervalued.to_csv(index=False),
                    file_name="undervalued_stocks.csv",
                    mime="text/csv",
                )
            else:
                st.info("No undervalued stocks found with current filters.")

    with tabs[1]:
        st.header("📉 Overvalued Stocks")
        params = {"min_mktcap": min_mktcap_val, "top_n": top_n_val}
        if company_filter_val:
            params["company"] = company_filter_val
        if sector_filter_val != "All":
            params["sector"] = sector_filter_val
        df_overvalued = get_data("get_overvalued_stocks", params=params)
        df_display = format_dataframe(df_overvalued.copy())
        st.dataframe(df_display)
        if not df_overvalued.empty:
            st.download_button(
                label="Download as CSV",
                data=df_overvalued.to_csv(index=False),
                file_name="overvalued_stocks.csv",
                mime="text/csv",
            )

    with tabs[2]:
        st.header("🏅 High Quality Stocks")
        params = {"min_mktcap": min_mktcap_val, "top_n": top_n_val}
        if company_filter_val:
            params["company"] = company_filter_val
        if sector_filter_val != "All":
            params["sector"] = sector_filter_val
        df_quality = get_data("get_high_quality_stocks", params=params)
        df_display = format_dataframe(df_quality.copy())
        st.dataframe(df_display)
        if not df_quality.empty:
            st.download_button(
                label="Download as CSV",
                data=df_quality.to_csv(index=False),
                file_name="high_quality_stocks.csv",
                mime="text/csv",
            )

    with tabs[3]:
        st.header("💵 High Earnings Yield Stocks")
        params = {"min_mktcap": min_mktcap_val, "top_n": top_n_val}
        if company_filter_val:
            params["company"] = company_filter_val
        if sector_filter_val != "All":
            params["sector"] = sector_filter_val
        df_ey = get_data("get_high_earnings_yield_stocks", params=params)
        df_display = format_dataframe(df_ey.copy())
        if not df_display.empty:
            df_display = df_display.reset_index(drop=True)
            st.dataframe(df_display)
        if not df_ey.empty:
            st.download_button(
                label="Download as CSV",
                data=df_ey.to_csv(index=False),
                file_name="high_earnings_yield_stocks.csv",
                mime="text/csv",
            )

    with tabs[4]:
        st.header("🏦 Top Market Cap Stocks")
        params = {"min_mktcap": min_mktcap_val, "top_n": top_n_val}
        if company_filter_val:
            params["company"] = company_filter_val
        if sector_filter_val != "All":
            params["sector"] = sector_filter_val
        df_mktcap = get_data("get_top_market_cap_stocks", params=params)
        df_display = format_dataframe(df_mktcap.copy())
        st.dataframe(df_display)
        if not df_mktcap.empty:
            st.download_button(
                label="Download as CSV",
                data=df_mktcap.to_csv(index=False),
                file_name="top_market_cap_stocks.csv",
                mime="text/csv",
            )

    with tabs[5]:
        st.header("🛡️ Low Beta Stocks")
        params = {"min_mktcap": min_mktcap_val, "top_n": top_n_val}
        if company_filter_val:
            params["company"] = company_filter_val
        if sector_filter_val != "All":
            params["sector"] = sector_filter_val
        df_lowbeta = get_data("get_low_beta_stocks", params=params)
        df_display = format_dataframe(df_lowbeta.copy())
        st.dataframe(df_display)
        if not df_lowbeta.empty:
            st.download_button(
                label="Download as CSV",
                data=df_lowbeta.to_csv(index=False),
                file_name="low_beta_stocks.csv",
                mime="text/csv",
            )

    with tabs[6]:
        st.header("💸 High Dividend Yield Stocks")
        params = {"min_mktcap": min_mktcap_val, "top_n": top_n_val}
        if company_filter_val:
            params["company"] = company_filter_val
        if sector_filter_val != "All":
            params["sector"] = sector_filter_val
        df_div = get_data("get_high_dividend_yield_stocks", params=params)
        df_display = format_dataframe(df_div.copy())
        st.dataframe(df_display)
        if not df_div.empty:
            st.download_button(
                label="Download as CSV",
                data=df_div.to_csv(index=False),
                file_name="high_dividend_yield_stocks.csv",
                mime="text/csv",
            )

    with tabs[7]:
        st.header("🚀 High Momentum Stocks")
        params = {"min_mktcap": min_mktcap_val, "top_n": top_n_val}
        if company_filter_val:
            params["company"] = company_filter_val
        if sector_filter_val != "All":
            params["sector"] = sector_filter_val
        df_mom = get_data("get_high_momentum_stocks", params=params)
        df_display = format_dataframe(df_mom.copy())
        st.dataframe(df_display)
        if not df_mom.empty:
            st.download_button(
                label="Download as CSV",
                data=df_mom.to_csv(index=False),
                file_name="high_momentum_stocks.csv",
                mime="text/csv",
            )

    with tabs[8]:
        st.header("🛡️ Low Volatility Stocks")
        params = {"min_mktcap": min_mktcap_val, "top_n": top_n_val}
        if company_filter_val:
            params["company"] = company_filter_val
        if sector_filter_val != "All":
            params["sector"] = sector_filter_val
        df_lowvol = get_data("get_low_volatility_stocks", params=params)
        df_display = format_dataframe(df_lowvol.copy())
        st.dataframe(df_display)
        if not df_lowvol.empty:
            st.download_button(
                label="Download as CSV",
                data=df_lowvol.to_csv(index=False),
                file_name="low_volatility_stocks.csv",
                mime="text/csv",
            )

    with tabs[9]:
        st.header("⚡ Short-Term Momentum Stocks")
        params = {"min_mktcap": min_mktcap_val, "top_n": top_n_val}
        if company_filter_val:
            params["company"] = company_filter_val
        if sector_filter_val != "All":
            params["sector"] = sector_filter_val
        df_stmom = get_data("get_top_short_term_momentum_stocks", params=params)
        df_display = format_dataframe(df_stmom.copy())
        st.dataframe(df_display)
        if not df_stmom.empty:
            st.download_button(
                label="Download as CSV",
                data=df_stmom.to_csv(index=False),
                file_name="short_term_momentum_stocks.csv",
                mime="text/csv",
            )

    with tabs[10]:
        st.header("💰 High Dividend + Low Beta Stocks")
        params = {"min_mktcap": min_mktcap_val, "top_n": top_n_val}
        if company_filter_val:
            params["company"] = company_filter_val
        if sector_filter_val != "All":
            params["sector"] = sector_filter_val
        df_div_lowbeta = get_data("get_high_dividend_low_beta_stocks", params=params)
        df_display = format_dataframe(df_div_lowbeta.copy())
        st.dataframe(df_display)
        if not df_div_lowbeta.empty:
            st.download_button(
                label="Download as CSV",
                data=df_div_lowbeta.to_csv(index=False),
                file_name="high_dividend_low_beta_stocks.csv",
                mime="text/csv",
            )

    with tabs[11]:
        st.header("🏅 Top Factor Composite Scores")
        params = {"min_mktcap": min_mktcap_val, "top_n": top_n_val}
        if company_filter_val:
            params["company"] = company_filter_val
        if sector_filter_val != "All":
            params["sector"] = sector_filter_val
        df_factor = get_data("get_top_factor_composite_stocks", params=params)
        df_display = format_dataframe(df_factor.copy())
        st.dataframe(df_display)
        if not df_factor.empty:
            st.download_button(
                label="Download as CSV",
                data=df_factor.to_csv(index=False),
                file_name="top_factor_composite_stocks.csv",
                mime="text/csv",
            )

    with tabs[12]:
        st.header("🚩 High Risk Warning Stocks")
        params = {"min_mktcap": min_mktcap_val, "top_n": top_n_val}
        if company_filter_val:
            params["company"] = company_filter_val
        if sector_filter_val != "All":
            params["sector"] = sector_filter_val
        df_risk = get_data("get_high_risk_stocks", params=params)
        df_display = format_dataframe(df_risk.copy())
        st.dataframe(df_display)
        if not df_risk.empty:
            st.download_button(
                label="Download as CSV",
                data=df_risk.to_csv(index=False),
                file_name="high_risk_stocks.csv",
                mime="text/csv",
            )

    with tabs[13]:
        st.header(
            "🏆 Top Combined Screener (Undervalued + High Quality + High Momentum)")
        params = {"min_mktcap": min_mktcap_val, "top_n": top_n_val}
        if company_filter_val:
            params["company"] = company_filter_val
        if sector_filter_val != "All":
            params["sector"] = sector_filter_val
        df_combined = get_data("get_top_combined_screen_limited", params=params)
        if not df_combined.empty:
            df_display = format_dataframe(df_combined.copy())
            st.dataframe(df_display)
            st.download_button(
                label="Download Combined Screener as CSV",
                data=df_combined.to_csv(index=False),
                file_name="top_combined_screener.csv",
                mime="text/csv",
            )
        else:
            st.warning(
                "No combined results found based on current filter criteria.")

    with tabs[14]:
        st.header("📈 Macro Data Visualization")
        df_macro = get_data("get_macro_data")
        if not df_macro.empty:
            # Convert Date column to datetime for proper plotting
            df_macro['Date'] = pd.to_datetime(df_macro['Date'])

            # Create two columns for charts
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("GDP Growth (YoY %)")
                st.line_chart(df_macro.set_index('Date')['GDP_Growth_YoY'])

            with col2:
                st.subheader("Inflation Rate (YoY %)")
                st.line_chart(df_macro.set_index('Date')['Inflation_YoY'])

            # Display the data table
            st.subheader("Macro Data Table")
            st.dataframe(df_macro)

            # Download button for macro data
            st.download_button(
                label="Download Macro Data as CSV",
                data=df_macro.to_csv(index=False),
                file_name="macro_data.csv",
                mime="text/csv",
            )
        else:
            st.warning("No macro data available.")

    st.success("Dashboard Loaded Successfully!")

finally:
    session.close()
