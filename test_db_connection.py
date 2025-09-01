from google.cloud.sql.connector import Connector
import sqlalchemy
import os

# Initialize the Cloud SQL Connector
connector = Connector()

# Define the connection function
def get_connection():
    return connector.connect(
        "equity-alpha-engine-alerts:europe-west2:equity-db",  # Instance connection name
        "pg8000",
        user="db_admin",
        password="Smart!98",
        db="equity_db"
    )

# Create a SQLAlchemy engine
try:
    pool = sqlalchemy.create_engine(
        "postgresql+pg8000://",
        creator=get_connection,
    )
    connection = pool.connect()
    print("Connection successful!")
    connection.close()
except Exception as e:
    print(f"Connection failed: {e}")

# Close the connector
connector.close()
