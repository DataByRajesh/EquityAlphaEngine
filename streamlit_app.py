
import streamlit as st
import pandas as pd
import requests
import os

API_URL = os.getenv("API_URL", "http://localhost:8000")

def get_data(endpoint, params=None):
    response = requests.get(f"{API_URL}/{endpoint}", params=params)
    if response.status_code == 200:
        return pd.DataFrame(response.json())
    else:
        st.error(f"API error: {response.status_code}")
        return pd.DataFrame()

st.set_page_config(page_title="Equity Alpha Engine", layout="wide")
st.title("📊 Equity Alpha Engine Dashboard")

st.sidebar.header("Filter Options")
min_mktcap = st.sidebar.number_input("Min Market Cap", min_value=0)
top_n = st.sidebar.slider("Number of Top Stocks", min_value=5, max_value=50, value=10)

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
    "Top Combined Screener"
]
tabs = st.tabs(TABS)

with tabs[0]:
    st.header("💰 Undervalued Stocks")
    df_undervalued = get_data("get_undervalued_stocks", params={"min_mktcap": min_mktcap, "top_n": top_n})
    st.dataframe(df_undervalued)

with tabs[1]:
    st.header("📉 Overvalued Stocks")
    df_overvalued = get_data("get_overvalued_stocks", params={"min_mktcap": min_mktcap, "top_n": top_n})
    st.dataframe(df_overvalued)

with tabs[2]:
    st.header("🏅 High Quality Stocks")
    df_quality = get_data("get_high_quality_stocks", params={"min_mktcap": min_mktcap, "top_n": top_n})
    st.dataframe(df_quality)

with tabs[3]:
    st.header("💵 High Earnings Yield Stocks")
    df_ey = get_data("get_high_earnings_yield_stocks", params={"min_mktcap": min_mktcap, "top_n": top_n})
    st.dataframe(df_ey)

with tabs[4]:
    st.header("🏦 Top Market Cap Stocks")
    df_mktcap = get_data("get_top_market_cap_stocks", params={"min_mktcap": min_mktcap, "top_n": top_n})
    st.dataframe(df_mktcap)

with tabs[5]:
    st.header("🛡️ Low Beta Stocks")
    df_lowbeta = get_data("get_low_beta_stocks", params={"min_mktcap": min_mktcap, "top_n": top_n})
    st.dataframe(df_lowbeta)

with tabs[6]:
    st.header("💸 High Dividend Yield Stocks")
    df_div = get_data("get_high_dividend_yield_stocks", params={"min_mktcap": min_mktcap, "top_n": top_n})
    st.dataframe(df_div)

with tabs[7]:
    st.header("🚀 High Momentum Stocks")
    df_mom = get_data("get_high_momentum_stocks", params={"min_mktcap": min_mktcap, "top_n": top_n})
    st.dataframe(df_mom)

with tabs[8]:
    st.header("🛡️ Low Volatility Stocks")
    df_lowvol = get_data("get_low_volatility_stocks", params={"min_mktcap": min_mktcap, "top_n": top_n})
    st.dataframe(df_lowvol)

with tabs[9]:
    st.header("⚡ Short-Term Momentum Stocks")
    df_stmom = get_data("get_top_short_term_momentum_stocks", params={"min_mktcap": min_mktcap, "top_n": top_n})
    st.dataframe(df_stmom)

with tabs[10]:
    st.header("💰 High Dividend + Low Beta Stocks")
    df_div_lowbeta = get_data("get_high_dividend_low_beta_stocks", params={"min_mktcap": min_mktcap, "top_n": top_n})
    st.dataframe(df_div_lowbeta)

with tabs[11]:
    st.header("🏅 Top Factor Composite Scores")
    df_factor = get_data("get_top_factor_composite_stocks", params={"min_mktcap": min_mktcap, "top_n": top_n})
    st.dataframe(df_factor)

with tabs[12]:
    st.header("🚩 High Risk Warning Stocks")
    df_risk = get_data("get_high_risk_stocks", params={"min_mktcap": min_mktcap, "top_n": top_n})
    st.dataframe(df_risk)

with tabs[13]:
    st.header("🏆 Top Combined Screener (Undervalued + High Quality + High Momentum)")
    df_combined = get_data("get_top_combined_screen_limited", params={"min_mktcap": min_mktcap, "top_n": top_n})
    if not df_combined.empty:
        st.dataframe(df_combined)
        st.download_button(
            label="Download Combined Screener as CSV",
            data=df_combined.to_csv(index=False),
            file_name='top_combined_screener.csv',
            mime='text/csv',
        )
    else:
        st.warning("No combined results found based on current filter criteria.")

st.success("Dashboard Loaded Successfully!")

st.info("Uses InvestWiseUK analytics engine pipeline. Replace with your real factor output for production if demoing.")
