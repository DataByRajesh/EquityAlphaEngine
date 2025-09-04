from google.cloud.sql.connector import Connector
import sqlalchemy
import os

# Initialize the Cloud SQL Connector
connector = Connector()

# Define the connection function
def get_connection():
    return connector.connect(
        "34.39.5.6",  # Public IP address
        "pg8000",
        user="postgres",  # Changed to default 'postgres' user
        password="Smart!98",
        db="equity_db",
        timeout=30  # Increased timeout to 30 seconds
    )

# Create a SQLAlchemy engine
try:
    pool = sqlalchemy.create_engine(
    "postgresql+pg8000://postgres:Smart!98@34.39.5.6:5432/equity_db",  # Changed to default 'postgres' user
    connect_args={"timeout": 30}  # Increased timeout to 30 seconds
)
    connection = pool.connect()
    print("Connection successful!")
    connection.close()
except Exception as e:
    print(f"Connection failed: {e}")

# Close the connector
connector.close()
