import numpy as np
import pandas as pd

from data_pipeline.compute_factors import compute_factors


def test_zero_volume_results_in_nan_amihud():
    dates = pd.date_range("2023-01-01", periods=25, freq="D")
    df = pd.DataFrame(
        {
            "Date": dates.astype(str),
            "Ticker": ["TEST.L"] * 25,
            "Close": np.linspace(100, 124, 25),
            "Volume": [100] * 24 + [0],
            "returnOnEquity": [0.1] * 25,
            "profitMargins": [0.1] * 25,
            "priceToBook": [1.0] * 25,
            "trailingPE": [10.0] * 25,
            "marketCap": [1e6] * 25,
        }
    )

    factors = compute_factors(df.copy())
    # Last row has zero volume -> NaN
    assert np.isnan(factors.iloc[-1]["amihud_illiquidity"])
    # Previous row has non-zero volume and enough history -> finite
    assert np.isfinite(factors.iloc[-2]["amihud_illiquidity"])
