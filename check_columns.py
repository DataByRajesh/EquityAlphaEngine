#!/usr/bin/env python3
"""
Check what columns exist in the financial_tbl table.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'data_pipeline'))

from data_pipeline.db_connection import engine
from sqlalchemy import text
import pandas as pd

def check_columns():
    """Check what columns exist in financial_tbl."""
    print("Checking database columns...")

    try:
        with engine.connect() as conn:
            # Get column names from financial_tbl
            query = text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'financial_tbl' 
                ORDER BY ordinal_position
            """)
            columns_df = pd.read_sql(query, conn)
            print('Columns in financial_tbl:')
            for _, row in columns_df.iterrows():
                print(f'  {row["column_name"]}: {row["data_type"]}')
            
            # Check if OHLCV columns exist
            ohlcv_cols = ['Open', 'High', 'Low', 'close_price', 'Close']
            print(f'\nOHLCV Column Status:')
            for col in ohlcv_cols:
                exists = col in columns_df['column_name'].values
                print(f'  {col}: {"EXISTS" if exists else "MISSING"}')
                
            # Check for sample data in OHLCV columns that exist
            print(f'\nSample OHLCV Data:')
            for col in ohlcv_cols:
                if col in columns_df['column_name'].values:
                    sample_query = text(f'SELECT "{col}" FROM financial_tbl WHERE "{col}" IS NOT NULL LIMIT 5')
                    try:
                        sample_df = pd.read_sql(sample_query, conn)
                        if not sample_df.empty:
                            print(f'  {col}: {sample_df.iloc[0, 0]} (sample value)')
                        else:
                            print(f'  {col}: NO NON-NULL VALUES')
                    except Exception as e:
                        print(f'  {col}: ERROR - {e}')

    except Exception as e:
        print(f"❌ Database check failed: {e}")
        return False

if __name__ == "__main__":
    check_columns()
