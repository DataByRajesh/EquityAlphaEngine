#!/usr/bin/env python3
"""
Test raw yfinance download to see what columns are returned.
"""

import yfinance as yf
import pandas as pd

def test_yfinance_raw():
    """Test raw yfinance download to see what columns are returned."""
    print("Testing raw yfinance download...")

    ticker = "III.L"
    start_date = "2023-01-01"
    end_date = "2023-01-10"

    print(f"Downloading raw data for {ticker} from {start_date} to {end_date}")

    try:
        data = yf.download(ticker, start=start_date, end=end_date, progress=False, auto_adjust=False)
        print(f"✅ Raw data downloaded successfully")
        print(f"Shape: {data.shape}")
        print(f"Columns: {list(data.columns)}")
        print(f"Index type: {type(data.index)}")
        print(f"Sample data:\n{data.head()}")

        # Check if it's MultiIndex
        if isinstance(data.columns, pd.MultiIndex):
            print("MultiIndex columns detected")
            print(f"Column levels: {data.columns.levels}")
        else:
            print("Regular columns")

        return True
    except Exception as e:
        print(f"❌ Raw download failed: {e}")
        return False

if __name__ == "__main__":
    test_yfinance_raw()
