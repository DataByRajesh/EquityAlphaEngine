import os

import pandas as pd
import requests
import streamlit as st

from data_pipeline.db_connection import get_db

API_URL = os.getenv(
    "API_URL", "https://equity-api-248891289968.europe-west2.run.app")


def get_data(endpoint, params=None):
    response = requests.get(f"{API_URL}/{endpoint}", params=params)
    if response.status_code == 200:
        return pd.DataFrame(response.json())
    else:
        st.error(f"API error: {response.status_code}")
        return pd.DataFrame()


def get_sectors():
    response = requests.get(f"{API_URL}/get_unique_sectors")
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Failed to fetch sectors: {response.status_code}")
        return []


def format_market_cap(x):
    if pd.isna(x):
        return x
    if x >= 1e9:
        return f"${x/1e9:.1f}B"
    elif x >= 1e6:
        return f"${x/1e6:.1f}M"
    else:
        return f"${x:,.0f}"


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
        params = {"min_mktcap": min_mktcap, "top_n": top_n}
        if company_filter:
            params["company"] = company_filter
        if sector_filter != "All":
            params["sector"] = sector_filter
        df_undervalued = get_data("get_undervalued_stocks", params=params)
        df_display = format_dataframe(df_undervalued.copy())
        st.dataframe(df_display)
        if not df_undervalued.empty:
            st.download_button(
                label="Download as CSV",
                data=df_undervalued.to_csv(index=False),
                file_name="undervalued_stocks.csv",
                mime="text/csv",
            )

    with tabs[1]:
        st.header("📉 Overvalued Stocks")
        params = {"min_mktcap": min_mktcap, "top_n": top_n}
        if company_filter:
            params["company"] = company_filter
        if sector_filter != "All":
            params["sector"] = sector_filter
        df_overvalued = get_data("get_overvalued_stocks", params=params)
        st.dataframe(df_overvalued)
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
        if sector_filter:
            params["sector"] = sector_filter
        df_quality = get_data("get_high_quality_stocks", params=params)
        st.dataframe(df_quality)
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
        if sector_filter:
            params["sector"] = sector_filter
        df_ey = get_data("get_high_earnings_yield_stocks", params=params)
        st.dataframe(df_ey)
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
        if sector_filter:
            params["sector"] = sector_filter
        df_mktcap = get_data("get_top_market_cap_stocks", params=params)
        st.dataframe(df_mktcap)
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
        if sector_filter:
            params["sector"] = sector_filter
        df_lowbeta = get_data("get_low_beta_stocks", params=params)
        st.dataframe(df_lowbeta)
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
        if sector_filter:
            params["sector"] = sector_filter
        df_div = get_data("get_high_dividend_yield_stocks", params=params)
        st.dataframe(df_div)
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
        if sector_filter:
            params["sector"] = sector_filter
        df_mom = get_data("get_high_momentum_stocks", params=params)
        st.dataframe(df_mom)
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
        if sector_filter:
            params["sector"] = sector_filter
        df_lowvol = get_data("get_low_volatility_stocks", params=params)
        st.dataframe(df_lowvol)
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
        if sector_filter:
            params["sector"] = sector_filter
        df_stmom = get_data("get_top_short_term_momentum_stocks", params=params)
        st.dataframe(df_stmom)
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
        if sector_filter:
            params["sector"] = sector_filter
        df_div_lowbeta = get_data("get_high_dividend_low_beta_stocks", params=params)
        st.dataframe(df_div_lowbeta)
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
        if sector_filter:
            params["sector"] = sector_filter
        df_factor = get_data("get_top_factor_composite_stocks", params=params)
        st.dataframe(df_factor)
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
        if sector_filter:
            params["sector"] = sector_filter
        df_risk = get_data("get_high_risk_stocks", params=params)
        st.dataframe(df_risk)
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
        if sector_filter:
            params["sector"] = sector_filter
        df_combined = get_data("get_top_combined_screen_limited", params=params)
        if not df_combined.empty:
            st.dataframe(df_combined)
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
