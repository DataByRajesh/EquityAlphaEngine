"""
Test database connection using environment variables.

This script tests the database connection using DATABASE_URL from environment variables.
It avoids hardcoded credentials and IPs for security and flexibility.
"""

import sqlalchemy

from data_pipeline.db_connection import engine


def test_connection():
    """Test database connection using the configured engine."""
    try:
        with engine.connect() as connection:
            result = connection.execute(sqlalchemy.text("SELECT 1"))
            print("Connection successful! Test query executed.")
            return True
    except Exception as e:
        print(f"Connection failed: {e}")
        return False


if __name__ == "__main__":
    success = test_connection()
    if not success:
        exit(1)
