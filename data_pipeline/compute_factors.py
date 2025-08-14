import numpy as np
import pandas as pd
import ta


def compute_factors(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute technical, value, quality and liquidity factors for a price
    and fundamentals :class:`~pandas.DataFrame`.

    Parameters
    ----------
    df : pd.DataFrame
        Input data containing at least ``Date``, ``Ticker``, ``Close`` and
        ``Volume`` columns, plus fundamental fields such as ``trailingPE``,
        ``priceToBook``, ``returnOnEquity``, ``profitMargins`` and
        ``marketCap``. Optional columns like ``dividendYield`` and
        ``priceToSalesTrailing12Months`` are used when available.

    Returns
    -------
    pd.DataFrame
        The original DataFrame with additional columns for momentum,
        volatility, moving averages, technical indicators (RSI, MACD,
        Bollinger Bands), value ratios, quality metrics, size/liquidity
        measures and a composite factor.
    """
    # --- Momentum ---
    for period, label in zip([21, 63, 126, 252], ['1m', '3m', '6m', '12m']):
        df[f'return_{label}'] = (
            df.groupby('Ticker')['Close'].pct_change(periods=period)
        )

    # 12-1m momentum
    df['momentum_12_1'] = (
        df.groupby('Ticker')['Close'].pct_change(periods=252) -
        df.groupby('Ticker')['Close'].pct_change(periods=21)
    )

    # --- Volatility ---
    for window in [21, 63, 252]:
        df[f'vol_{window}d'] = (
            df.groupby('Ticker')['Close'].transform(lambda x: x.pct_change().rolling(window).std())
        )

    # --- Moving Averages ---
    for window in [20, 50, 200]:
        df[f'ma_{window}'] = (
            df.groupby('Ticker')['Close'].transform(lambda x: ta.trend.sma_indicator(x, window))
        )

    # --- Technicals via ta ---
    df['RSI_14'] = (
        df.groupby('Ticker')['Close'].transform(lambda x: ta.momentum.rsi(x, window=14))
    )

    # MACD and MACD histogram
    df['MACD'] = df.groupby('Ticker')['Close'].transform(lambda x: ta.trend.macd(x, window_slow=26, window_fast=12))
    df['MACDh'] = df.groupby('Ticker')['Close'].transform(lambda x: ta.trend.macd_diff(x, window_slow=26, window_fast=12, window_sign=9))

    # Bollinger Bands (upper and lower)
    def bbands_func(x):
        bb = ta.volatility.BollingerBands(x, window=20, window_dev=2)
        return pd.DataFrame({'BBU_20': bb.bollinger_hband(), 'BBL_20': bb.bollinger_lband()}, index=x.index)

    bb_df = df.groupby('Ticker')['Close'].apply(bbands_func).reset_index(level=0, drop=True)
    df[['BBU_20', 'BBL_20']] = bb_df

    # --- Value factors ---
    if 'trailingPE' in df.columns:
        df['earnings_yield'] = 1 / df['trailingPE'].replace(0, np.nan)
    else:
        df['earnings_yield'] = np.nan

    df['book_to_price'] = 1 / df['priceToBook'].replace(0, np.nan)
    df['dividendYield'] = df.get('dividendYield', np.nan)
    df['price_to_sales'] = df.get('priceToSalesTrailing12Months', np.nan)

    # Ensure finite values for subsequent calculations
    df.replace([np.inf, -np.inf], np.nan, inplace=True)

    # --- Quality factors ---
    df['quality_score'] = df[['returnOnEquity', 'profitMargins']].mean(axis=1)
    df['norm_quality_score'] = df.groupby('Date')['quality_score'].transform(lambda x: (x - x.mean()) / x.std())

    # --- Size / Liquidity ---
    df['log_marketCap'] = np.log(df['marketCap'])
    df['avg_volume_21d'] = df.groupby('Ticker')['Volume'].transform(lambda x: x.rolling(21).mean())    
    # Calculate raw Amihud
    df['amihud_raw'] = (df['Close'].pct_change().abs() / (df['Volume'] * df['Close']))
    # 21-day rolling mean by ticker (final Amihud)
    df['amihud_illiquidity'] = df.groupby('Ticker')['amihud_raw'].transform(lambda x: x.rolling(21).mean())
    # Optionally: drop the intermediate column
    df.drop(columns=['amihud_raw'], inplace=True)

    '''df['amihud_illiquidity'] = (
        df.groupby('Ticker').apply(
            lambda g: (g['Close'].pct_change().abs() / (g['Volume'] * g['Close'])).rolling(21).mean()
        ).reset_index(level=0, drop=True)
    )'''


    # --- Composite factor ---
    factor_cols = ['return_12m', 'earnings_yield', 'norm_quality_score']
    for col in factor_cols:
        df[f'z_{col}'] = df.groupby('Date')[col].transform(lambda x: (x - x.mean()) / x.std())

    df['factor_composite'] = df[[f'z_{col}' for col in factor_cols if f'z_{col}' in df.columns]].mean(axis=1)

    return df
