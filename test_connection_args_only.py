#!/usr/bin/env python3
"""
Focused test for the database connection argument fix.
"""

import sys

from data_pipeline.db_connection import _get_driver_specific_connect_args

sys.path.insert(0, ".")


# Mock the get_secret function
class MockUtils:
    @staticmethod
    def get_secret(key):
        return "sqlite:///test.db"


sys.modules["data_pipeline.utils"] = MockUtils()


def test_connection_args():
    """Test the core fix: driver-specific connection arguments."""
    print("🧪 Testing Database Connection Arguments Fix")
    print("=" * 50)

    test_cases = [
        {
            "url": "postgresql://user:pass@localhost:5432/db",
            "description": "Default PostgreSQL (psycopg2)",
            "should_have_connect_timeout": True,
        },
        {
            "url": "postgresql+psycopg2://user:pass@localhost:5432/db",
            "description": "Explicit psycopg2",
            "should_have_connect_timeout": True,
        },
        {
            "url": "postgresql+pg8000://user:pass@localhost:5432/db",
            "description": "pg8000 driver (the problematic one)",
            "should_have_connect_timeout": False,
        },
    ]

    all_passed = True

    for i, case in enumerate(test_cases, 1):
        print(f"\n{i}. Testing {case['description']}")
        print(f"   URL: {case['url']}")

        try:
            args = _get_driver_specific_connect_args(case["url"])
            print(f"   Generated args: {args}")

            # Check timeout is always present
            if "timeout" not in args:
                print(f"   ❌ FAIL: Missing 'timeout' parameter")
                all_passed = False
                continue

            # Check connect_timeout based on driver
            has_connect_timeout = "connect_timeout" in args
            should_have = case["should_have_connect_timeout"]

            if has_connect_timeout == should_have:
                status = "✅ PASS"
                if should_have:
                    print(
                        f"   {status}: Correctly includes 'connect_timeout' for psycopg2"
                    )
                else:
                    print(
                        f"   {status}: Correctly excludes 'connect_timeout' for pg8000"
                    )
            else:
                status = "❌ FAIL"
                if should_have:
                    print(
                        f"   {status}: Should have 'connect_timeout' but doesn't")
                else:
                    print(
                        f"   {status}: Should NOT have 'connect_timeout' but does")
                all_passed = False

        except Exception as e:
            print(f"   ❌ FAIL: Exception occurred: {e}")
            all_passed = False

    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 SUCCESS: All connection argument tests passed!")
        print("\nThe fix should resolve the original error:")
        print(
            "   TypeError: connect() got an unexpected keyword argument 'connect_timeout'"
        )
        print("\nThis error occurred because:")
        print("   - pg8000 driver doesn't support 'connect_timeout' parameter")
        print("   - The code was passing it to all PostgreSQL drivers")
        print("   - Now the code detects the driver and uses appropriate parameters")
        return True
    else:
        print("❌ FAILURE: Some tests failed")
        return False


if __name__ == "__main__":
    success = test_connection_args()
    exit(0 if success else 1)
