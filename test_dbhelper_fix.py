#!/usr/bin/env python3
"""
Test script to verify DBHelper fixes work correctly.
Tests the critical database connection and session flow fixes.
"""

import os
import sys
import tempfile

import pandas as pd

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_dbhelper_with_custom_url():
    """Test DBHelper with custom SQLite URL (simulates API endpoint usage)"""
    print("🧪 Testing DBHelper with custom SQLite URL...")

    try:
        # Create temporary SQLite database
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_url = f"sqlite:///{tmp.name}"

        # Import and test DBHelper
        from data_pipeline.db_utils import DBHelper

        # Test instantiation
        db = DBHelper(db_url)
        print(f"✅ DBHelper instantiated successfully with custom URL")

        # Test that engine property exists and works
        assert hasattr(db, "engine"), "Missing self.engine property"
        assert hasattr(db, "inspector"), "Missing self.inspector property"
        print(f"✅ Engine and inspector properties exist")

        # Test basic database operations
        test_df = pd.DataFrame(
            {"id": [1, 2], "name": ["test1", "test2"], "value": [10.5, 20.7]}
        )

        # Test table creation
        db.create_table("test_table", test_df)
        print(f"✅ Table creation successful")

        # Test data insertion
        db.insert_dataframe("test_table", test_df)
        print(f"✅ Data insertion successful")

        # Test data retrieval
        result_df = pd.read_sql("SELECT * FROM test_table", db.engine)
        assert len(result_df) == 2, f"Expected 2 rows, got {len(result_df)}"
        print(f"✅ Data retrieval successful: {len(result_df)} rows")

        # Test cleanup
        db.close()
        print(f"✅ Database cleanup successful")

        # Cleanup temp file
        os.unlink(tmp.name)

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_dbhelper_without_url():
    """Test DBHelper without URL (simulates data pipeline usage)"""
    print("\n🧪 Testing DBHelper without URL (global engine)...")

    try:
        from data_pipeline.db_utils import DBHelper

        # Test instantiation without URL
        db = DBHelper()
        print(f"✅ DBHelper instantiated successfully without URL")

        # Test that engine property exists
        assert hasattr(db, "engine"), "Missing self.engine property"
        assert hasattr(db, "inspector"), "Missing self.inspector property"
        print(f"✅ Engine and inspector properties exist")

        # Test that it uses global engine
        from data_pipeline.db_connection import engine as global_engine

        assert db.engine is global_engine, "Should use global engine"
        print(f"✅ Uses global engine correctly")

        # Test cleanup
        db.close()
        print(f"✅ Database cleanup successful")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_streamlit_import():
    """Test that streamlit import fix works"""
    print("\n🧪 Testing Streamlit import fix...")

    try:
        # Test the import that was failing
        from data_pipeline.db_connection import get_db

        print(f"✅ Import successful: data_pipeline.db_connection.get_db")

        # Test that it returns a generator
        db_gen = get_db()
        assert hasattr(db_gen, "__next__"), "get_db should return a generator"
        print(f"✅ get_db returns generator as expected")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_market_data_import():
    """Test that market data import fix works"""
    print("\n🧪 Testing Market Data import fix...")

    try:
        # Test the import that was failing
        from data_pipeline.db_utils import DBHelper

        print(f"✅ Import successful: data_pipeline.db_utils.DBHelper")

        # Test instantiation (the pattern used in market_data.py)
        db_helper = DBHelper()  # Uses global engine
        print(f"✅ DBHelper instantiation successful")

        # Test cleanup
        db_helper.close()
        print(f"✅ Cleanup successful")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("🚀 Starting Database Connection Fix Verification Tests\n")

    tests = [
        ("DBHelper with Custom URL", test_dbhelper_with_custom_url),
        ("DBHelper without URL", test_dbhelper_without_url),
        ("Streamlit Import Fix", test_streamlit_import),
        ("Market Data Import Fix", test_market_data_import),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"{'='*60}")
        print(f"Running: {test_name}")
        print(f"{'='*60}")

        success = test_func()
        results.append((test_name, success))

        if success:
            print(f"✅ {test_name}: PASSED")
        else:
            print(f"❌ {test_name}: FAILED")

    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}")

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name}: {status}")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Database connection fixes are working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please review the errors above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
