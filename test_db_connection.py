from sqlalchemy import create_engine

DATABASE_URL = "postgresql://db_admin:Smart!98@34.39.5.6:5432/equity_db"

try:
    engine = create_engine(DATABASE_URL)
    connection = engine.connect()
    print("Connection successful!")
    connection.close()
except Exception as e:
    print(f"Connection failed: {e}")
