#!/usr/bin/env python3
"""
Simple test script to verify the database connection fix works.
This test focuses specifically on the connect_timeout parameter issue.
"""

import os
import tempfile
from sqlalchemy import create_engine

# Mock the get_secret function to avoid Google Cloud dependencies
def mock_get_secret(key):
    """Mock function to simulate getting database URL from secrets."""
    if key == "DATABASE_URL":
        # Return a test database URL - we'll test both drivers
        return os.environ.get("TEST_DATABASE_URL", "sqlite:///test.db")
    return None

# Patch the get_secret function
import sys
sys.path.insert(0, '.')

# Create a mock utils module
class MockUtils:
    @staticmethod
    def get_secret(key):
        return mock_get_secret(key)

# Patch the import
sys.modules['data_pipeline.utils'] = MockUtils()

# Now import our fixed db_connection module
from data_pipeline.db_connection import _get_driver_specific_connect_args, initialize_engine

def test_driver_detection():
    """Test that driver detection works correctly."""
    print("🧪 Testing driver detection logic...")
    
    # Test psycopg2 URLs
    psycopg2_urls = [
        "postgresql://user:pass@host:5432/db",
        "postgresql+psycopg2://user:pass@host:5432/db"
    ]
    
    for url in psycopg2_urls:
        args = _get_driver_specific_connect_args(url)
        print(f"  URL: {url}")
        print(f"  Args: {args}")
        assert "connect_timeout" in args, f"psycopg2 should have connect_timeout: {args}"
        assert args["timeout"] == 60, f"Should have timeout=60: {args}"
        print("  ✅ psycopg2 detection works")
    
    # Test pg8000 URLs
    pg8000_urls = [
        "postgresql+pg8000://user:pass@host:5432/db"
    ]
    
    for url in pg8000_urls:
        args = _get_driver_specific_connect_args(url)
        print(f"  URL: {url}")
        print(f"  Args: {args}")
        assert "connect_timeout" not in args, f"pg8000 should NOT have connect_timeout: {args}"
        assert args["timeout"] == 60, f"Should have timeout=60: {args}"
        print("  ✅ pg8000 detection works")
    
    print("✅ Driver detection test passed!")

def test_sqlite_engine_creation():
    """Test that we can create an engine with SQLite (no connection args needed)."""
    print("\n🧪 Testing SQLite engine creation...")
    
    # Create a temporary SQLite database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_url = f"sqlite:///{tmp.name}"
    
    # Set the mock DATABASE_URL
    os.environ["TEST_DATABASE_URL"] = db_url
    
    try:
        # This should work without any connection timeout issues
        engine = initialize_engine()
        print(f"  ✅ Engine created successfully: {engine}")
        
        # Test a simple connection
        with engine.connect() as conn:
            result = conn.execute("SELECT 1 as test").fetchone()
            assert result[0] == 1, "Simple query should work"
            print("  ✅ Database connection test passed")
        
        engine.dispose()
        print("✅ SQLite engine test passed!")
        
    except Exception as e:
        print(f"  ❌ SQLite engine test failed: {e}")
        raise
    finally:
        # Clean up
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)

def test_postgresql_url_parsing():
    """Test PostgreSQL URL parsing without actually connecting."""
    print("\n🧪 Testing PostgreSQL URL parsing...")
    
    test_cases = [
        {
            "url": "postgresql://user:pass@localhost:5432/testdb",
            "expected_driver": "psycopg2",
            "should_have_connect_timeout": True
        },
        {
            "url": "postgresql+psycopg2://user:pass@localhost:5432/testdb", 
            "expected_driver": "psycopg2",
            "should_have_connect_timeout": True
        },
        {
            "url": "postgresql+pg8000://user:pass@localhost:5432/testdb",
            "expected_driver": "pg8000", 
            "should_have_connect_timeout": False
        }
    ]
    
    for case in test_cases:
        print(f"  Testing: {case['url']}")
        args = _get_driver_specific_connect_args(case['url'])
        
        if case['should_have_connect_timeout']:
            assert "connect_timeout" in args, f"Should have connect_timeout for {case['expected_driver']}"
            print(f"    ✅ {case['expected_driver']} has connect_timeout")
        else:
            assert "connect_timeout" not in args, f"Should NOT have connect_timeout for {case['expected_driver']}"
            print(f"    ✅ {case['expected_driver']} does not have connect_timeout")
        
        assert "timeout" in args, "All drivers should have timeout"
        print(f"    ✅ Has timeout parameter: {args['timeout']}")
    
    print("✅ PostgreSQL URL parsing test passed!")

if __name__ == "__main__":
    print("🚀 Testing Database Connection Fix")
    print("=" * 50)
    
    try:
        test_driver_detection()
        test_sqlite_engine_creation()
        test_postgresql_url_parsing()
        
        print("\n" + "=" * 50)
        print("🎉 All tests passed! The database connection fix is working correctly.")
        print("\nThe fix should resolve the original error:")
        print("  TypeError: connect() got an unexpected keyword argument 'connect_timeout'")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
