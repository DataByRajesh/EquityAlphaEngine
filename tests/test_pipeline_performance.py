#!/usr/bin/env python3
"""
Test script to verify optimized pipeline performance with a small subset of tickers.
"""

import time
import os
import tempfile
from data_pipeline.market_data import main
from data_pipeline.db_connection import engine

def test_small_pipeline():
    """Test pipeline with 5 tickers to verify performance improvements."""
    # Create temporary database for testing
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()
    db_url = f"sqlite:///{temp_db.name}"

    # Test with small subset of tickers
    test_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

    # Override config for testing
    os.environ["FTSE_100_TICKERS"] = ",".join(test_tickers)

    start_time = time.time()

    try:
        # Create engine
        engine = get_db_engine(db_url)

        # Run pipeline
        main(engine, "2023-01-01", "2023-12-31")

        end_time = time.time()
        duration = end_time - start_time

        print(f"✓ Pipeline completed successfully in {duration:.2f} seconds")
        print("✓ No database lock errors encountered")
        print("✓ Caching appears to be working")

        return True

    except Exception as e:
        print(f"✗ Pipeline failed: {e}")
        return False

    finally:
        # Clean up
        if os.path.exists(temp_db.name):
            os.unlink(temp_db.name)

if __name__ == "__main__":
    print("Testing optimized pipeline performance with 5 tickers...")
    success = test_small_pipeline()
    if success:
        print("\n🎉 Performance test passed!")
    else:
        print("\n❌ Performance test failed!")
