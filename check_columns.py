from data_pipeline.db_connection import engine
from sqlalchemy import inspect

inspector = inspect(engine)
columns = inspector.get_columns('financial_tbl')
print("Columns in financial_tbl:")
for col in columns:
    print(f"  {col['name']}: {col['type']}")
