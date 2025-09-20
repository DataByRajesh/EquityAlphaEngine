#!/usr/bin/env python3
"""
Check data for INF.L ticker specifically.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'data_pipeline'))

from data_pipeline.db_connection import engine
from sqlalchemy import text
import pandas as pd

def check_inf_data():
    """Check data for INF.L ticker."""
    print("Checking data for INF.L ticker...")

    try:
        with engine.connect() as conn:
            # Check the specific ticker that was returned
            query = text("""
                SELECT 
                    f."Ticker",
                    f."Date",
                    f."Open",
                    f."High",
                    f."Low",
                    f."close_price",
                    f."factor_composite"
                FROM financial_tbl f
                WHERE f."Ticker" = 'INF.L'
                ORDER BY f."Date" DESC
                LIMIT 5
            """)
            df = pd.read_sql(query, conn)
            print('Recent data for INF.L:')
            print(df)
            
            # Check if there's any ticker with non-null OHLCV data
            print("\nChecking for any ticker with non-null OHLCV data:")
            query2 = text("""
                SELECT 
                    f."Ticker",
                    f."Date",
                    f."Open",
                    f."High",
                    f."Low",
                    f."close_price"
                FROM financial_tbl f
                WHERE f."Open" IS NOT NULL 
                AND f."High" IS NOT NULL 
                AND f."Low" IS NOT NULL 
                AND f."close_price" IS NOT NULL
                ORDER BY f."Date" DESC
                LIMIT 5
            """)
            df2 = pd.read_sql(query2, conn)
            print('Tickers with complete OHLCV data:')
            print(df2)

    except Exception as e:
        print(f"❌ Check failed: {e}")
        return False

if __name__ == "__main__":
    check_inf_data()
