from data_pipeline.db_connection import engine
from sqlalchemy import text

def check_factor_composite_column():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'financial_tbl'
                AND column_name = 'factor_composite';
            """)).fetchall()

            if result:
                print("✅ factor_composite column EXISTS in financial_tbl")
                return True
            else:
                print("❌ factor_composite column DOES NOT exist in financial_tbl")
                return False
    except Exception as e:
        print(f"Error checking database schema: {e}")
        return False

def check_recent_data():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) as total_rows,
                       COUNT(CASE WHEN "factor_composite" IS NOT NULL THEN 1 END) as factor_composite_count
                FROM financial_tbl
                LIMIT 1000;
            """)).fetchone()

            print(f"Total rows in sample: {result[0]}")
            print(f"Rows with factor_composite: {result[1]}")
    except Exception as e:
        print(f"Error checking data: {e}")

if __name__ == "__main__":
    print("Checking database schema...")
    column_exists = check_factor_composite_column()
    if column_exists:
        check_recent_data()
