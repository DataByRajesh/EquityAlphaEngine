import sqlite3
import pandas as pd
import numpy as np

class DBHelper:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)
        self.cur = self.conn.cursor()

    def create_table(self, table_name,df):
        dtype_map = self.df_sql_dtypes(df)
        cols_sql = ',\n  '.join([f'"{col}" {dtype}' for col, dtype in dtype_map.items()])    
        sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({cols_sql})"
        self.cur.execute(sql)
        self.conn.commit()

        # --- Add missing columns if table already exists ---
        self.cur.execute(f"PRAGMA table_info({table_name})")
        existing_cols = set(row[1] for row in self.cur.fetchall())
        for col, dtype in dtype_map.items():
            if col not in existing_cols:
                alter_sql = f'ALTER TABLE {table_name} ADD COLUMN "{col}" {dtype}'
                self.cur.execute(alter_sql)
                self.conn.commit()


    def insert_row(self, table_name, row_dict):
        # row_dict = {"col1": val1, "col2": val2, ...}
        cols = ", ".join(row_dict.keys())
        placeholders = ", ".join(["?"] * len(row_dict))
        values = tuple(row_dict.values())
        sql = f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})"
        self.cur.execute(sql, values)
        self.conn.commit()

    def insert_dataframe(self, table_name, df):
        df.to_sql(table_name, self.conn, if_exists='replace', index=False)

    def close(self):
        self.conn.close()

    def df_sql_dtypes(self,df):
        """
        Create a dictionary mapping DataFrame column names to SQLite types.
        Float/Int → 'REAL', everything else → 'TEXT'
        """
        type_map = {}
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                type_map[col] = 'REAL'
            else:
                type_map[col] = 'TEXT'
        return type_map

