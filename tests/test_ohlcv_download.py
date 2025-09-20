#!/usr/bin/env python3
"""
Test script to cross-check OHLCV download functionality.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'data_pipeline'))

from data_pipeline.market_data import fetch_historical_data
from data_pipeline.config import configure_logging

# Configure logging
configure_logging()

def test_ohlcv_download():
    """Test OHLCV download for a few tickers."""
    print("Testing OHLCV download...")

    # Test with a few FTSE 100 tickers
    test_tickers = ["III.L", "ADM.L", "AAF.L"]  # First 3 from config
    start_date = "2023-01-01"
    end_date = "2023-01-10"

    print(f"Downloading data for {test_tickers} from {start_date} to {end_date}")

    df = fetch_historical_data(test_tickers, start_date, end_date)

    if df.empty:
        print("❌ No data downloaded!")
        return False

    print(f"✅ Downloaded {len(df)} rows")
    print(f"Columns: {list(df.columns)}")
    print(f"Sample data:\n{df.head()}")

    # Check for OHLCV completeness
    required_ohlcv = ['Open', 'High', 'Low', 'close_price']
    complete_rows = df[required_ohlcv].notna().all(axis=1).sum()
    total_rows = len(df)

    print(f"OHLCV completeness: {complete_rows}/{total_rows} rows have complete OHLCV data")

    if complete_rows == 0:
        print("❌ All OHLCV data is NULL!")
        return False
    elif complete_rows < total_rows:
        print("⚠️  Some OHLCV data is missing")
    else:
        print("✅ All OHLCV data is complete")

    return True

if __name__ == "__main__":
    success = test_ohlcv_download()
    sys.exit(0 if success else 1)
