from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

import pandas as pd


def financial_round(value, places):
    """
    Rounds a value to the specified number of decimal places using decimal.Decimal for accuracy.
    If value cannot be converted, returns NaN.
    """
    try:
        if pd.isna(value):
            return float("nan")
        return float(
            Decimal(str(value)).quantize(
                Decimal(f'1.{"0" * places}'), rounding=ROUND_HALF_UP
            )
        )
    except (InvalidOperation, TypeError, ValueError):
        return float("nan")


def round_financial_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Round financial and factor columns to fixed decimal places.

    Built-in :meth:`pandas.DataFrame.round` is used wherever possible for
    performance and simplicity. ``financial_round`` is reserved only for
    columns that contain non-numeric data and therefore require the more
    robust decimal based rounding.
    """

    column_decimals = {
        # Raw financials
        "Open": 2,
        "High": 2,
        "Low": 2,
        "close_price": 2,
        "returnOnEquity": 4,
        "grossMargins": 4,
        "operatingMargins": 4,
        "profitMargins": 4,
        "priceToBook": 4,
        "trailingPE": 4,
        "forwardPE": 4,
        "priceToSalesTrailing12Months": 4,
        "debtToEquity": 3,
        "currentRatio": 3,
        "quickRatio": 3,
        "dividendYield": 5,
        "marketCap": 0,
        "beta": 3,
        "averageVolume": 0,
        # Factors (expand as you add)
        "return_1m": 4,
        "return_3m": 4,
        "return_6m": 4,
        "return_12m": 4,
        "momentum_12_1": 4,
        "vol_21d": 5,
        "vol_63d": 5,
        "vol_252d": 5,
        "ma_20": 3,
        "ma_50": 3,
        "ma_200": 3,
        "RSI_14": 2,
        "MACD": 3,
        "MACDh": 3,
        "BBU_20": 2,
        "BBL_20": 2,
        "earnings_yield": 5,
        "book_to_price": 5,
        "quality_score": 4,
        "norm_quality_score": 4,
        "log_marketCap": 3,
        "avg_volume_21d": 0,
        "amihud_illiquidity": 7,
        "price_to_sales": 4,
        "factor_composite": 4,
        "z_return_12m": 4,
        "z_earnings_yield": 4,
        "z_norm_quality_score": 4,
        # Add any other computed columns here
    }
    df_copy = df.copy()

    numeric_cols: dict[str, int] = {}
    object_cols: list[tuple[str, int]] = []

    for col, dec in column_decimals.items():
        if col not in df_copy.columns:
            continue
        if pd.api.types.is_numeric_dtype(df_copy[col]):
            numeric_cols[col] = dec
        else:
            object_cols.append((col, dec))

    if numeric_cols:
        df_copy = df_copy.round(numeric_cols)

    for col, dec in object_cols:
        df_copy[col] = df_copy[col].apply(lambda x: financial_round(x, dec))

    return df_copy
