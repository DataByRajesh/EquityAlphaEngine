import numpy as np
import pandas as pd
import ta

# Updated local imports to use fallback mechanism
try:
    from . import config
except ImportError:
    import data_pipeline.config as config

# Config-driven logger
logger = config.get_file_logger(__name__)


def _safe_zscore(x: pd.Series, fill_value: float = 0.0) -> pd.Series:
    """
    Cross-sectional z-score; safe for zero/NaN std.
    Logs entry, exit, and edge cases.
    """
    logger.debug("_safe_zscore called for series of length %d", len(x))
    std = x.std()
    if pd.isna(std) or std == 0:
        logger.debug(
            "Standard deviation is zero or NaN; returning fill_value %s", fill_value
        )
        return pd.Series(fill_value, index=x.index)
    result = (x - x.mean()) / std
    logger.debug("_safe_zscore completed for series of length %d", len(x))
    return result


def compute_factors(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute technical, value, quality, liquidity, and a composite factor.

    Requires columns:
      Date, Ticker, close_price, Volume
    Uses when available:
      trailingPE, priceToBook, returnOnEquity, profitMargins,
      marketCap, dividendYield, priceToSalesTrailing12Months
    """

    logger.info("compute_factors called for DataFrame with %d rows", len(df))
    try:
        df = df.sort_values(["Ticker", "Date"]).copy()
    except Exception as e:
        logger.error("Failed to sort DataFrame: %s", e, exc_info=True)
        raise
    logger.debug("DataFrame sorted by Ticker and Date")

    # ---------- Momentum ----------
    logger.debug("Starting momentum calculations")
    for period, label in zip([21, 63, 126, 252], ["1m", "3m", "6m", "12m"]):
        try:
            df[f"return_{label}"] = df.groupby("Ticker", group_keys=False)[
                "close_price"
            ].pct_change(periods=period, fill_method=None)
        except Exception as e:
            logger.warning(
                f"Failed to compute return_{label}: %s", e, exc_info=True)
    # 12-1 momentum
    try:
        g = df.groupby("Ticker", group_keys=False)["close_price"]
        df["momentum_12_1"] = g.pct_change(252, fill_method=None) - g.pct_change(
            21, fill_method=None
        )
    except Exception as e:
        logger.warning("Failed to compute momentum_12_1: %s", e, exc_info=True)

    # ---------- Volatility ----------
    logger.debug("Starting volatility calculations")
    for window in [21, 63, 252]:
        try:
            df[f"vol_{window}d"] = df.groupby("Ticker", group_keys=False)[
                "close_price"
            ].transform(
                lambda x: x.pct_change(fill_method=None)
                .rolling(window, min_periods=max(2, window // 3))
                .std()
            )
        except Exception as e:
            logger.warning(
                f"Failed to compute vol_{window}d: %s", e, exc_info=True)

    # ---------- Moving Averages ----------
    logger.debug("Starting moving averages calculations")
    for window in [20, 50, 200]:
        try:
            df[f"ma_{window}"] = df.groupby("Ticker", group_keys=False)[
                "close_price"
            ].transform(lambda x: ta.trend.sma_indicator(x, window=window))
        except Exception as e:
            logger.warning(
                f"Failed to compute ma_{window}: %s", e, exc_info=True)

    # ---------- RSI ----------
    logger.debug("Starting RSI calculation")
    try:
        df["RSI_14"] = df.groupby("Ticker", group_keys=False)["close_price"].transform(
            lambda x: ta.momentum.rsi(x, window=14)
        )
    except Exception as e:
        logger.warning("Failed to compute RSI_14: %s", e, exc_info=True)

    # ---------- MACD (robust to ta version) ----------
    logger.debug("Starting MACD calculation")

    def _macd(series: pd.Series) -> pd.DataFrame:
        """
        Compute MACD and MACD histogram for a price series.
        Logs entry and errors.
        """
        logger.debug("_macd called for series of length %d", len(series))
        try:
            m = ta.trend.MACD(series, window_slow=26,
                              window_fast=12, window_sign=9)
            return pd.DataFrame(
                {"MACD": m.macd(), "MACDh": m.macd_diff()}, index=series.index
            )
        except Exception as e:
            logger.warning("MACD calculation failed: %s", e, exc_info=True)
            return pd.DataFrame({"MACD": np.nan, "MACDh": np.nan}, index=series.index)

    try:
        macd_df = (
            df.groupby("Ticker", group_keys=False)["close_price"]
            .apply(_macd)
            .reset_index(level=0, drop=True)
        )
        df[["MACD", "MACDh"]] = macd_df
    except Exception as e:
        logger.warning("Failed to compute MACD/MACDh: %s", e, exc_info=True)

    # ---------- Bollinger Bands ----------
    logger.debug("Starting Bollinger Bands calculation")

    def _bb(series: pd.Series) -> pd.DataFrame:
        """
        Compute Bollinger Bands for a price series.
        Logs entry and errors.
        """
        logger.debug("_bb called for series of length %d", len(series))
        try:
            bb = ta.volatility.BollingerBands(series, window=20, window_dev=2)
            return pd.DataFrame(
                {"BBU_20": bb.bollinger_hband(), "BBL_20": bb.bollinger_lband()},
                index=series.index,
            )
        except Exception as e:
            logger.warning(
                "Bollinger Bands calculation failed: %s", e, exc_info=True)
            return pd.DataFrame(
                {"BBU_20": np.nan, "BBL_20": np.nan}, index=series.index
            )

    try:
        bb_df = (
            df.groupby("Ticker", group_keys=False)["close_price"]
            .apply(_bb)
            .reset_index(level=0, drop=True)
        )
        df[["BBU_20", "BBL_20"]] = bb_df
    except Exception as e:
        logger.warning("Failed to compute Bollinger Bands: %s",
                       e, exc_info=True)

    # ---------- Value ----------
    logger.debug("Starting value factor calculations")
    # Earnings yield (handle zero/NaN/neg PE safely)
    if "trailingPE" in df.columns:
        pe = pd.to_numeric(df["trailingPE"], errors="coerce")
        df["earnings_yield"] = 1.0 / pe.replace(0, np.nan)
    else:
        logger.warning(
            "Column 'trailingPE' missing; earnings_yield set to NaN.")
        df["earnings_yield"] = np.nan

    pb = pd.to_numeric(df.get("priceToBook", np.nan), errors="coerce")
    if "priceToBook" not in df.columns:
        logger.warning(
            "Column 'priceToBook' missing; book_to_price set to NaN.")
    df["book_to_price"] = 1.0 / pb.replace(0, np.nan)
    if "dividendYield" not in df.columns:
        logger.warning(
            "Column 'dividendYield' missing; dividendYield set to NaN.")
    df["dividendYield"] = pd.to_numeric(
        df.get("dividendYield", np.nan), errors="coerce"
    )
    if "priceToSalesTrailing12Months" not in df.columns:
        logger.warning(
            "Column 'priceToSalesTrailing12Months' missing; price_to_sales set to NaN."
        )
    df["price_to_sales"] = pd.to_numeric(
        df.get("priceToSalesTrailing12Months", np.nan), errors="coerce"
    )

    # ---------- Quality ----------
    logger.debug("Starting quality factor calculations")
    if "returnOnEquity" not in df.columns:
        logger.warning(
            "Column 'returnOnEquity' missing; quality_score may be inaccurate."
        )
    if "profitMargins" not in df.columns:
        logger.warning(
            "Column 'profitMargins' missing; quality_score may be inaccurate."
        )
    df["quality_score"] = (
        pd.to_numeric(df.get("returnOnEquity", np.nan), errors="coerce")
        + pd.to_numeric(df.get("profitMargins", np.nan), errors="coerce")
    ) / 2.0
    df["norm_quality_score"] = df.groupby("Date", group_keys=False)[
        "quality_score"
    ].transform(_safe_zscore)

    # ---------- Size / Liquidity ----------
    logger.debug("Starting size/liquidity calculations")
    mc = pd.to_numeric(df.get("marketCap", np.nan), errors="coerce")
    if "marketCap" not in df.columns:
        logger.warning("Column 'marketCap' missing; log_marketCap set to NaN.")
    df["log_marketCap"] = np.where(mc > 0, np.log(mc), np.nan)

    if "Volume" not in df.columns:
        logger.warning("Column 'Volume' missing; avg_volume_21d set to NaN.")
        df["avg_volume_21d"] = np.nan
    else:
        df["avg_volume_21d"] = df.groupby("Ticker", group_keys=False)[
            "Volume"
        ].transform(lambda x: x.rolling(21, min_periods=5).mean())

    # ---------- Amihud illiquidity ----------
    logger.debug("Starting Amihud illiquidity calculation")

    def _amihud(grp: pd.DataFrame) -> pd.Series:
        """
        Compute Amihud illiquidity for a ticker group.
        Logs entry and errors.
        """
        logger.debug("_amihud called for group of length %d", len(grp))
        try:
            ret = grp["close_price"].pct_change(fill_method=None).abs()
            vol = grp["Volume"].replace(0, np.nan)
            amt = vol * grp["close_price"]
            raw = ret / amt
            return raw.rolling(21, min_periods=5).mean()
        except Exception as e:
            logger.warning("Amihud calculation failed: %s", e, exc_info=True)
            return pd.Series(np.nan, index=grp.index)

    try:
        df["amihud_illiquidity"] = (
            df.groupby("Ticker", group_keys=False)[["close_price", "Volume"]]
            .apply(_amihud)
            .reset_index(level=0, drop=True)
        )
    except Exception as e:
        logger.warning(
            "Failed to compute amihud_illiquidity: %s", e, exc_info=True)

    # ---------- Clean infinities early ----------
    logger.debug("Cleaning infinities and NaNs")
    df.replace([np.inf, -np.inf], np.nan, inplace=True)

    # ---------- Composite factor ----------
    logger.debug("Starting composite factor calculation")
    factor_cols = ["return_12m", "earnings_yield", "norm_quality_score"]

    for col in factor_cols:
        if col in df.columns:
            try:
                df[f"z_{col}"] = df.groupby("Date", group_keys=False)[col].transform(
                    _safe_zscore
                )
            except Exception as e:
                logger.warning(
                    f"Failed to z-score {col}: %s", e, exc_info=True)

    z_cols = [f"z_{c}" for c in factor_cols if f"z_{c}" in df.columns]
    try:
        df["factor_composite"] = df[z_cols].mean(axis=1) if z_cols else np.nan
    except Exception as e:
        logger.warning("Failed to compute factor_composite: %s",
                       e, exc_info=True)

    logger.info("Factor computation complete for %d rows.", len(df))
    return df
