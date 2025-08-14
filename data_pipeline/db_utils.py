from typing import Optional, Sequence

import pandas as pd
from sqlalchemy import (
    Column,
    Float,
    MetaData,
    Table,
    Text as SAText,
    create_engine,
    inspect,
    text,
)
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from . import config


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
        self.preparer = self.engine.dialect.identifier_preparer

    def _quote_identifier(self, identifier: str) -> str:
        """Safely quote an identifier (e.g., table/column name)."""
        return self.preparer.quote(identifier)

    def create_table(
        self,
        table_name: str,
        df: pd.DataFrame,
        primary_keys: Optional[Sequence[str]] = None,
    ) -> None:
        dtype_map = self.df_sql_dtypes(df)
        metadata = MetaData()
        columns = []
        for col, dtype in dtype_map.items():
            sql_type = Float if dtype == 'FLOAT' else SAText
            is_pk = primary_keys and col in primary_keys
            columns.append(Column(col, sql_type, primary_key=bool(is_pk)))
        table = Table(table_name, metadata, *columns)
        metadata.create_all(self.engine, tables=[table])

        # --- Add missing columns if table already exists ---
        inspector = inspect(self.engine)
        existing_cols = set(col['name'] for col in inspector.get_columns(table_name))
        for col, dtype in dtype_map.items():
            if col not in existing_cols:
                alter_sql = text(
                    f'ALTER TABLE {self._quote_identifier(table_name)} '
                    f'ADD COLUMN {self._quote_identifier(col)} {dtype}'
                )
                with self.engine.begin() as conn:
                    conn.execute(alter_sql)

    def insert_row(self, table_name, row_dict):
        metadata = MetaData()
        table = Table(table_name, metadata, autoload_with=self.engine)
        with self.engine.begin() as conn:
            conn.execute(table.insert(), row_dict)

    def insert_dataframe(
        self,
        table_name: str,
        df: pd.DataFrame,
        unique_cols: Optional[Sequence[str]] = None,
    ) -> None:
        if df.empty:
            return

        if unique_cols:
            metadata = MetaData()
            table = Table(table_name, metadata, autoload_with=self.engine)
            insert_stmt = sqlite_insert(table)
            update_cols = {
                c.name: insert_stmt.excluded[c.name]
                for c in table.columns
                if c.name not in unique_cols
            }
            upsert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=list(unique_cols), set_=update_cols
            )
            with self.engine.begin() as conn:
                conn.execute(upsert_stmt, df.to_dict(orient="records"))
        else:
            df.to_sql(table_name, self.engine, if_exists="append", index=False)

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

