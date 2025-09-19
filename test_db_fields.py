#!/usr/bin/env python3
"""
Test script to check what fields are available in the database.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'data_pipeline'))

from data_pipeline.db_connection import engine
from sqlalchemy import text
import pandas as pd

def test_db_fields():
    """Check what fields are available and have data in the database."""
    print("Testing database fields availability...")

    try:
        with engine.connect() as conn:
            # Check latest data for a few tickers
            query = text("""
                SELECT
                    f."Ticker",
                    f."Date",
                    f."factor_composite",
                    f."norm_quality_score",
                    f."earnings_yield",
                    f."marketCap",
                    f."beta",
                    f."dividendYield",
                    f."return_12m",
                    f."vol_21d",
                    f."return_3m",
                    f."vol_252d"
                FROM financial_tbl f
                INNER JOIN (
                    SELECT "Ticker", MAX("Date") as max_date
                    FROM financial_tbl
                    GROUP BY "Ticker"
                ) m ON f."Ticker" = m."Ticker" AND f."Date" = m.max_date
                LIMIT 5
            """)

            df = pd.read_sql(query, conn)
            print(f"✅ Database connection successful")
            print(f"Sample data (first 5 rows):\n{df}")

            # Check null counts for each field
            print("\n📊 NULL Analysis:")
            for col in df.columns:
                if col != 'Ticker' and col != 'Date':
                    null_count = df[col].isnull().sum()
                    total_count = len(df)
                    print(f"{col}: {null_count}/{total_count} NULL values")

            # Test specific queries that are failing
            print("\n🔍 Testing problematic queries:")

            # Test high_quality_stocks query
            quality_query = text("""
                SELECT COUNT(*) as count
                FROM financial_tbl f
                INNER JOIN (
                    SELECT "Ticker", MAX("Date") as max_date
                    FROM financial_tbl
                    GROUP BY "Ticker"
                ) m ON f."Ticker" = m."Ticker" AND f."Date" = m.max_date
                WHERE f."norm_quality_score" IS NOT NULL
            """)

            quality_result = pd.read_sql(quality_query, conn)
            print(f"Records with norm_quality_score: {quality_result.iloc[0]['count']}")

            # Test earnings_yield query
            earnings_query = text("""
                SELECT COUNT(*) as count
                FROM financial_tbl f
                INNER JOIN (
                    SELECT "Ticker", MAX("Date") as max_date
                    FROM financial_tbl
                    GROUP BY "Ticker"
                ) m ON f."Ticker" = m."Ticker" AND f."Date" = m.max_date
                WHERE f."earnings_yield" IS NOT NULL
            """)

            earnings_result = pd.read_sql(earnings_query, conn)
            print(f"Records with earnings_yield: {earnings_result.iloc[0]['count']}")

            # Test marketCap query
            marketcap_query = text("""
                SELECT COUNT(*) as count
                FROM financial_tbl f
                INNER JOIN (
                    SELECT "Ticker", MAX("Date") as max_date
                    FROM financial_tbl
                    GROUP BY "Ticker"
                ) m ON f."Ticker" = m."Ticker" AND f."Date" = m.max_date
                WHERE f."marketCap" IS NOT NULL
            """)

            marketcap_result = pd.read_sql(marketcap_query, conn)
            print(f"Records with marketCap: {marketcap_result.iloc[0]['count']}")

            return True

    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

if __name__ == "__main__":
    test_db_fields()
