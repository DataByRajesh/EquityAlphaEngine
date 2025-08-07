from typing import Optional

import pandas as pd
from sqlalchemy import create_engine, inspect, text

import config

class DBHelper:
    """Simple helper around a SQLAlchemy engine.

    Parameters
    ----------
    db_url: Optional[str]
        Database connection string.  When not provided the value from
        :mod:`config` (``config.DATABASE_URL``) is used.
    """

    def __init__(self, db_url: Optional[str] = None):
        self.database_url = db_url or config.DATABASE_URL
        self.engine = create_engine(self.database_url)

    def create_table(self, table_name, df):
        dtype_map = self.df_sql_dtypes(df)
        cols_sql = ',\n  '.join([f'"{col}" {dtype}' for col, dtype in dtype_map.items()])
        sql = text(f"CREATE TABLE IF NOT EXISTS {table_name} ({cols_sql})")
        with self.engine.begin() as conn:
            conn.execute(sql)

        # --- Add missing columns if table already exists ---
        inspector = inspect(self.engine)
        existing_cols = set(col['name'] for col in inspector.get_columns(table_name))
        for col, dtype in dtype_map.items():
            if col not in existing_cols:
                alter_sql = text(f'ALTER TABLE {table_name} ADD COLUMN "{col}" {dtype}')
                with self.engine.begin() as conn:
                    conn.execute(alter_sql)


    def insert_row(self, table_name, row_dict):
        cols = ", ".join(row_dict.keys())
        placeholders = ", ".join([f":{col}" for col in row_dict])
        sql = text(f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})")
        with self.engine.begin() as conn:
            conn.execute(sql, row_dict)

    def insert_dataframe(self, table_name, df):
        df.to_sql(table_name, self.engine, if_exists='replace', index=False)

    def close(self):
        self.engine.dispose()

    def df_sql_dtypes(self,df):
        """
        Create a dictionary mapping DataFrame column names to SQL types.
        Float/Int → 'FLOAT', everything else → 'TEXT'
        """
        type_map = {}
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                type_map[col] = 'FLOAT'
            else:
                type_map[col] = 'TEXT'
        return type_map

