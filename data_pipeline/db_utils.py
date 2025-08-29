
from typing import Optional, Sequence, Dict

import pandas as pd
from sqlalchemy import (
    Column, Float, Integer, BigInteger, Boolean, Text, String, Date, DateTime,
    MetaData, Table, create_engine, inspect, Index
)
from sqlalchemy.dialects.postgresql import insert as pg_insert

from . import config

# Config-driven logger
logger = config.get_file_logger(__name__)

# --- Helpers ---
_SQL_TEXT = Text         # For generic text columns
_SQL_FLOAT = Float       # For float columns
_SQL_INT = Integer       # For integer columns
_SQL_BIGINT = BigInteger # For big integer columns
_SQL_BOOL = Boolean      # For boolean columns
_SQL_STR = String        # For string columns
_SQL_DATE = Date         # For date columns
_SQL_DT = DateTime       # For datetime columns

def _sa_type_for_series(s: pd.Series):
    """
    Infer the appropriate SQLAlchemy type for a pandas Series.
    Used for automatic schema inference when creating tables.
    """
    # Boolean columns
    if pd.api.types.is_bool_dtype(s):
        logger.debug("Inferring BOOL type for column")
        return _SQL_BOOL
    # Integer columns (choose BIGINT if max value exceeds 2**31-1)
    if pd.api.types.is_integer_dtype(s):
        max_val = s.max(skipna=True)
        logger.debug("Inferring INT/BIGINT type for column, max value: %s", max_val)
        return _SQL_BIGINT if max_val and max_val > 2**31-1 else _SQL_INT
    # Float columns
    if pd.api.types.is_float_dtype(s):
        logger.debug("Inferring FLOAT type for column")
        return _SQL_FLOAT
    # Datetime columns
    if pd.api.types.is_datetime64_any_dtype(s) or pd.api.types.is_datetime64_ns_dtype(s):
        logger.debug("Inferring DATETIME type for column")
        return _SQL_DT
    # String columns
    if pd.api.types.is_string_dtype(s):
        logger.debug("Inferring STRING type for column")
        return _SQL_STR
    # Fallback: treat as generic text
    logger.debug("Inferring TEXT type for column")
    return (_SQL_TEXT)

def _records(df: pd.DataFrame):
    """
    Convert DataFrame to list of dicts, replacing NaN with None for DB NULL.
    """
    logger.debug("Converting DataFrame to records for DB insert, shape: %s", df.shape)
    return df.where(pd.notna(df), None).to_dict(orient="records")

def _chunked_insert(conn, stmt, df: pd.DataFrame, chunksize: int = 5000) -> None:
    """
    Helper to insert DataFrame in chunks using the given statement.
    """
    for _, chunk in df.groupby(df.index // chunksize):
        data = _records(chunk)
        try:
            conn.execute(stmt, data)
        except Exception as e:
            logger.error("Failed to insert chunk into '%s': %s", getattr(stmt, 'table', None) or getattr(stmt, 'name', None), e, exc_info=True)

# --- Main DBHelper ---
class DBHelper:
    """
    Helper for GCP Cloud SQL (PostgreSQL) operations.
    Only PostgreSQL is supported.
    """
    def __init__(self, db_url: Optional[str] = None):
        self.database_url = db_url or config.DATABASE_URL
        self.engine = create_engine(self.database_url, future=True)
        self.inspector = inspect(self.engine)
        logger.info("DBHelper initialized with database URL: %s", self.database_url)

    def create_table(
        self,
        table_name: str,
        df: pd.DataFrame,
        primary_keys: Optional[Sequence[str]] = None,
        unique_cols: Optional[Sequence[str]] = None,
    ) -> None:
        """
        Create table if missing; add missing columns if present.
        """
        logger.info("Creating table '%s' with columns: %s", table_name, list(df.columns))
        md = MetaData()
        if self.inspector.has_table(table_name):
            # add only missing columns
            existing = {c['name'] for c in self.inspector.get_columns(table_name)}
            with self.engine.begin() as conn:
                for col in df.columns:
                    if col in existing:
                        continue
                    col_type = _sa_type_for_series(df[col])
                    logger.info("Adding missing column '%s' to table '%s'", col, table_name)
                    try:
                        conn.execute(
                            Table(table_name, md, autoload_with=self.engine)
                            .append_column(Column(col, col_type))
                            .to_metadata(md)
                        )
                    except Exception as e:
                        logger.error("Failed to add column '%s' to table '%s': %s", col, table_name, e, exc_info=True)
                # ensure UNIQUE index for upsert if requested
                if unique_cols:
                    self._ensure_unique_index(conn, table_name, tuple(unique_cols))
            return

        # create new table
        cols = []
        for col in df.columns:
            cols.append(Column(col, _sa_type_for_series(df[col]),
                               primary_key=(primary_keys and col in primary_keys)))
        table = Table(table_name, md, *cols)
        md.create_all(self.engine, tables=[table])
        logger.info("Table '%s' created.", table_name)

        # add unique index if needed (for upsert)
        if unique_cols:
            with self.engine.begin() as conn:
                self._ensure_unique_index(conn, table_name, tuple(unique_cols))

    def _ensure_unique_index(self, conn, table_name: str, cols: tuple[str, ...]):
        """
        Ensure a unique index exists for the given columns.
        """
        idx_name = f"uq_{table_name}_{'_'.join(cols)}"
        existing = {i['name'] for i in self.inspector.get_indexes(table_name)}
        if idx_name not in existing:
            tbl = Table(table_name, MetaData(), autoload_with=self.engine)
            Index(idx_name, *[tbl.c[c] for c in cols], unique=True).create(conn)
            logger.info("Created unique index '%s' on table '%s'", idx_name, table_name)

    def insert_row(self, table_name: str, row_dict: Dict) -> None:
        """
        Insert a single row into a table.
        """
        logger.debug("Inserting row into '%s': %s", table_name, row_dict)
        tbl = Table(table_name, MetaData(), autoload_with=self.engine)
        with self.engine.begin() as conn:
            try:
                conn.execute(tbl.insert(), [row_dict])
            except Exception as e:
                logger.error("Failed to insert row into '%s': %s", table_name, e, exc_info=True)

    def insert_dataframe(
        self,
        table_name: str,
        df: pd.DataFrame,
        unique_cols: Optional[Sequence[str]] = None,
        chunksize: int = 5000,
    ) -> None:
        """
        Insert a DataFrame into a table, using upsert if unique_cols are provided.
        Only PostgreSQL (GCP Cloud SQL) is supported.
        """
        if df.empty:
            logger.info("DataFrame is empty; nothing to insert into '%s'.", table_name)
            return
        tbl = Table(table_name, MetaData(), autoload_with=self.engine)

        if unique_cols:
            logger.info("Upserting DataFrame into '%s' (%d rows) with unique columns: %s", table_name, len(df), unique_cols)
            insert_stmt = pg_insert(tbl)
            up_cols = {c.name: insert_stmt.excluded[c.name] for c in tbl.columns if c.name not in unique_cols}
            stmt = insert_stmt.on_conflict_do_update(index_elements=list(unique_cols), set_=up_cols)
            with self.engine.begin() as conn:
                _chunked_insert(conn, stmt, df, chunksize)
        else:
            logger.info("Appending DataFrame to '%s' (%d rows)", table_name, len(df))
            with self.engine.begin() as conn:
                _chunked_insert(conn, tbl.insert(), df, chunksize)

    def close(self) -> None:
        """
        Dispose the SQLAlchemy engine.
        """
        logger.info("Disposing database engine.")
        self.engine.dispose()

