import os
import time
import logging
import urllib.parse

import pandas as pd
import requests
import streamlit as st
from data_pipeline.db_connection import get_db
from data_pipeline.utils import get_secret

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API URL configuration from environment variable or default

API_URL = os.getenv("API_URL", "https://equity-api-248891289968.europe-west2.run.app")

# Connection configuration
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
CONNECTION_TIMEOUT = 500  # seconds
REQUEST_TIMEOUT = 500  # seconds

def make_request_with_retry(url, params=None, max_retries=MAX_RETRIES):
    """Make HTTP request with retry logic and exponential backoff."""
    last_exception = None

    for attempt in range(max_retries):
        try:
            logger.debug(f"Request attempt {attempt + 1}/{max_retries} to {url}")
            response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
            logger.debug(f"Request successful with status {response.status_code}")
            return response
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            last_exception = e
            if attempt < max_retries - 1:
                wait_time = RETRY_DELAY * (2 ** attempt)  # Exponential backoff
                logger.warning(f"Request attempt {attempt + 1} failed: {e}. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error(f"All {max_retries} request attempts failed. Last error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during request: {e}")
            raise e

    # If we get here, all retries failed
    raise last_exception

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

    st.sidebar.header("Filter Options")
    min_mktcap = st.sidebar.number_input("Min Market Cap", min_value=0)
    top_n = st.sidebar.slider("Number of Top Stocks",
                              min_value=5, max_value=50, value=10)
    company_filter = st.sidebar.text_input("Company Name", "")
    sectors = get_sectors()
    sector_options = ["All"] + sectors
    sector_filter = st.sidebar.selectbox("Sector", sector_options)

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
            params = {"min_mktcap": min_mktcap, "top_n": top_n}
            if company_filter:
                params["company"] = company_filter
            if sector_filter != "All":
                params["sector"] = sector_filter
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
        params = {"min_mktcap": min_mktcap, "top_n": top_n}
        if company_filter:
            params["company"] = company_filter
        if sector_filter != "All":
            params["sector"] = sector_filter
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
        params = {"min_mktcap": min_mktcap, "top_n": top_n}
        if company_filter:
            params["company"] = company_filter
        if sector_filter != "All":
            params["sector"] = sector_filter
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
        params = {"min_mktcap": min_mktcap, "top_n": top_n}
        if company_filter:
            params["company"] = company_filter
        if sector_filter != "All":
            params["sector"] = sector_filter
        df_ey = get_data("get_high_earnings_yield_stocks", params=params)
        df_display = format_dataframe(df_ey.copy())
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
        params = {"min_mktcap": min_mktcap, "top_n": top_n}
        if company_filter:
            params["company"] = company_filter
        if sector_filter != "All":
            params["sector"] = sector_filter
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
        params = {"min_mktcap": min_mktcap, "top_n": top_n}
        if company_filter:
            params["company"] = company_filter
        if sector_filter != "All":
            params["sector"] = sector_filter
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
        params = {"min_mktcap": min_mktcap, "top_n": top_n}
        if company_filter:
            params["company"] = company_filter
        if sector_filter != "All":
            params["sector"] = sector_filter
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
        params = {"min_mktcap": min_mktcap, "top_n": top_n}
        if company_filter:
            params["company"] = company_filter
        if sector_filter != "All":
            params["sector"] = sector_filter
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
        params = {"min_mktcap": min_mktcap, "top_n": top_n}
        if company_filter:
            params["company"] = company_filter
        if sector_filter != "All":
            params["sector"] = sector_filter
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
        params = {"min_mktcap": min_mktcap, "top_n": top_n}
        if company_filter:
            params["company"] = company_filter
        if sector_filter != "All":
            params["sector"] = sector_filter
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
        params = {"min_mktcap": min_mktcap, "top_n": top_n}
        if company_filter:
            params["company"] = company_filter
        if sector_filter != "All":
            params["sector"] = sector_filter
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
        params = {"min_mktcap": min_mktcap, "top_n": top_n}
        if company_filter:
            params["company"] = company_filter
        if sector_filter != "All":
            params["sector"] = sector_filter
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
        params = {"min_mktcap": min_mktcap, "top_n": top_n}
        if company_filter:
            params["company"] = company_filter
        if sector_filter != "All":
            params["sector"] = sector_filter
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
        params = {"min_mktcap": min_mktcap, "top_n": top_n}
        if company_filter:
            params["company"] = company_filter
        if sector_filter != "All":
            params["sector"] = sector_filter
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
