import time
from typing import Dict, Optional, Sequence

import pandas as pd
from sqlalchemy import (BigInteger, Boolean, Column, Date, DateTime, Float,
                        Index, Integer, MetaData, String, Table, Text,
                        create_engine, inspect, text)
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

# Updated local imports to use fallback mechanism
try:
    from . import config
except ImportError:
    import data_pipeline.config as config

# Config-driven logger
logger = config.get_file_logger(__name__)

# --- Helpers ---
_SQL_TEXT = Text  # For generic text columns
_SQL_FLOAT = Float  # For float columns
_SQL_INT = Integer  # For integer columns
_SQL_BIGINT = BigInteger  # For big integer columns
_SQL_BOOL = Boolean  # For boolean columns
_SQL_STR = String  # For string columns
_SQL_DATE = Date  # For date columns
_SQL_DT = DateTime  # For datetime columns


def _sa_type_for_series(s: pd.Series, col_name: str = None):
    """
    Infer the appropriate SQLAlchemy type for a pandas Series.
    Used for automatic schema inference when creating tables.
    """
    # Special case for Date column
    if col_name == "Date":
        logger.debug("Inferring DATE type for Date column")
        return _SQL_DATE
    # Boolean columns
    if pd.api.types.is_bool_dtype(s):
        logger.debug("Inferring BOOL type for column")
        return _SQL_BOOL
    # Integer columns (choose BIGINT if max value exceeds 2**31-1)
    if pd.api.types.is_integer_dtype(s):
        max_val = s.max(skipna=True)
        logger.debug(
            "Inferring INT/BIGINT type for column, max value: %s", max_val)
        return _SQL_BIGINT if max_val and max_val > 2**31 - 1 else _SQL_INT
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
    return _SQL_TEXT


def _records(df: pd.DataFrame):
    """
    Convert DataFrame to list of dicts, replacing NaN with None for DB NULL.
    """
    logger.debug(
        "Converting DataFrame to records for DB insert, shape: %s", df.shape)
    return df.where(pd.notna(df), None).to_dict(orient="records")


def _chunked_insert(conn, stmt, df: pd.DataFrame, chunksize: int = 900) -> None:
    """
    Helper to insert DataFrame in chunks using the given statement.
    Includes retry logic for database lock errors and performance tracking.
    """
    max_retries = 5  # Increased retries for better reliability
    retry_delay = 0.5  # Reduced initial delay for faster retries

    total_chunks = (len(df) + chunksize - 1) // chunksize
    logger.info(
        "Processing %d chunks of size %d (%d total rows)",
        total_chunks,
        chunksize,
        len(df),
    )

    chunk_start_time = time.time()
    for chunk_idx, (_, chunk) in enumerate(df.groupby(df.index // chunksize)):
        chunk_time = time.time()
        data = _records(chunk)
        logger.debug(
            "Processing chunk %d/%d with %d records",
            chunk_idx + 1,
            total_chunks,
            len(data),
        )

        for attempt in range(max_retries):
            try:
                conn.execute(stmt, data)
                chunk_elapsed = time.time() - chunk_time
                logger.info(
                    "Chunk %d/%d inserted in %.2f seconds (%.1f rows/sec)",
                    chunk_idx + 1,
                    total_chunks,
                    chunk_elapsed,
                    len(data) / chunk_elapsed if chunk_elapsed > 0 else 0,
                )
                # Log progress every 5 chunks or for the last chunk
                if chunk_idx % 5 == 0 or chunk_idx == total_chunks - 1:
                    elapsed = time.time() - chunk_start_time
                    rows_processed = (chunk_idx + 1) * chunksize
                    rate = rows_processed / elapsed if elapsed > 0 else 0
                    logger.info(
                        "Inserted chunk %d/%d (%d/%d rows, %.1f rows/sec)",
                        chunk_idx + 1,
                        total_chunks,
                        min(rows_processed, len(df)),
                        len(df),
                        rate,
                    )
                break  # Success, exit retry loop
            except OperationalError as e:
                if "database is locked" in str(e).lower() and attempt < max_retries - 1:
                    logger.warning(
                        "Database locked, retrying insert in %s seconds (attempt %d/%d): %s",
                        retry_delay,
                        attempt + 1,
                        max_retries,
                        e,
                    )
                    time.sleep(retry_delay)
                    # Capped exponential backoff
                    retry_delay = min(retry_delay * 1.5, 5.0)
                else:
                    logger.error(
                        "Failed to insert chunk into '%s' after %d attempts: %s",
                        getattr(stmt, "table", None) or getattr(
                            stmt, "name", None),
                        max_retries,
                        e,
                        exc_info=True,
                    )
                    raise
            except Exception as e:
                logger.error(
                    "Failed to insert chunk into '%s': %s",
                    getattr(stmt, "table", None) or getattr(
                        stmt, "name", None),
                    e,
                    exc_info=True,
                )
                raise


# --- Main DBHelper ---


class DBHelper:
    """
    Helper for GCP Cloud SQL (PostgreSQL) operations.
    Only PostgreSQL is supported.
    """

    _population_running = False  # Class variable to prevent multiple population triggers

    def __init__(self, db_url: Optional[str] = None, engine=None):
        if engine:
            # Use provided engine
            self.database_url = "using_provided_engine"
            self.engine = engine
            self._own_engine = False  # We don't own the provided engine
            session_factory = sessionmaker(
                autocommit=False, autoflush=False, bind=self.engine)
        elif db_url:
            # Create dedicated engine for custom URL (used by API endpoints and
            # tests)
            self.database_url = db_url
            self.engine = create_engine(db_url, pool_pre_ping=True)
            self._own_engine = True  # Track that we own this engine
            session_factory = sessionmaker(
                autocommit=False, autoflush=False, bind=self.engine)
        else:
            # Use global engine (used by data pipeline)
            from data_pipeline.db_connection import SessionLocal, engine

            self.database_url = "using_global_engine"
            self.engine = engine
            self._own_engine = False  # We don't own the global engine
            session_factory = SessionLocal

        self.inspector = inspect(self.engine)
        self.session = session_factory()
        logger.info("DBHelper initialized with database URL: %s",
                    self.database_url)

    def create_table(
        self,
        table_name: str,
        df: pd.DataFrame,
        primary_keys: Optional[Sequence[str]] = None,
        unique_cols: Optional[Sequence[str]] = None,
        auto_populate: bool = True,
    ) -> None:
        """
        Create table if missing; add missing columns if present.
        If table is created or empty, optionally trigger data population.
        """
        table_created = False
        table_empty = False

        try:
            # Use session for ORM-based operations
            with self.session.begin():
                logger.info("Creating table '%s' if not exists.", table_name)
                if self.inspector.has_table(table_name):
                    # Check if table is empty
                    try:
                        count_result = pd.read_sql(
                            f"SELECT COUNT(*) as count FROM {table_name}", self.engine)
                        row_count = count_result["count"].iloc[0]
                        if row_count == 0:
                            table_empty = True
                            logger.info(
                                "Table '%s' exists but is empty (%d rows).",
                                table_name,
                                row_count,
                            )
                    except Exception as e:
                        logger.warning(
                            "Could not check if table '%s' is empty: %s", table_name, e)

                    # add only missing columns
                    existing = {c["name"]
                                for c in self.inspector.get_columns(table_name)}
                    for col in df.columns:
                        if col in existing:
                            continue
                        col_type = _sa_type_for_series(df[col], col)
                        logger.info(
                            "Adding missing column '%s' to table '%s'", col, table_name)
                        try:
                            alter_stmt = text(f"ALTER TABLE \"{table_name}\" ADD COLUMN \"{col}\" {str(col_type).upper()}")
                            self.session.execute(alter_stmt)
                        except Exception as e:
                            logger.error(
                                "Failed to add column '%s' to table '%s': %s",
                                col,
                                table_name,
                                e,
                                exc_info=True,
                            )
                    # ensure UNIQUE index for upsert if requested
                    if unique_cols:
                        self._ensure_unique_index(
                            self.session, table_name, tuple(unique_cols))
                else:
                    # create new table
                    table_created = True
                    cols = []
                    for col in df.columns:
                        cols.append(
                            Column(
                                col,
                                _sa_type_for_series(df[col], col),
                                primary_key=(
                                    primary_keys and col in primary_keys),
                            )
                        )
                    table = Table(table_name, MetaData(), *cols)
                    MetaData().create_all(self.engine, tables=[table])
                    logger.info("Table '%s' created.", table_name)

                    # add unique index if needed (for upsert)
                    if unique_cols:
                        self._ensure_unique_index(
                            self.session, table_name, tuple(unique_cols))
        except Exception as e:
            logger.error("Failed to create table '%s': %s",
                         table_name, e, exc_info=True)
            self.session.rollback()
        finally:
            self.session.close()

        # Trigger data population if table was created or is empty
        if auto_populate and (table_created or table_empty) and table_name == "financial_tbl":
            logger.info(
                "Table '%s' is %s. Triggering data population...",
                table_name,
                "newly created" if table_created else "empty",
            )
            self._trigger_data_population()

    def _trigger_data_population(self):
        """Trigger the data population pipeline for financial data using default 10 years."""
        if DBHelper._population_running:
            logger.info(
                "Data population already running, skipping duplicate trigger.")
            return

        DBHelper._population_running = True
        try:
            from datetime import datetime, timedelta

            from data_pipeline.market_data import main as market_data_main

            # Use same default as update_financial_data.py: 10 years
            end_date = datetime.today()
            # 10 years of data (default)
            start_date = end_date - timedelta(days=10 * 365)

            logger.info(
                "Starting automatic data population from %s to %s (10 years default)",
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d"),
            )

            # Call the market data pipeline
            market_data_main(
                self.engine,
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d"),
            )

            logger.info("Automatic data population completed successfully.")

        except Exception as e:
            logger.error(
                "Failed to trigger automatic data population: %s", e, exc_info=True)
            # Don't raise - this is a convenience feature, not critical
        finally:
            DBHelper._population_running = False

    def _ensure_unique_index(self, conn, table_name: str, cols: tuple[str, ...]):
        """
        Ensure a unique index exists for the given columns.
        """
        idx_name = f"uq_{table_name}_{'_'.join(cols)}"
        existing = {i["name"] for i in self.inspector.get_indexes(table_name)}
        if idx_name not in existing:
            tbl = Table(table_name, MetaData(), autoload_with=self.engine)
            Index(idx_name, *[tbl.c[c]
                  for c in cols], unique=True).create(conn)
            logger.info("Created unique index '%s' on table '%s'",
                        idx_name, table_name)

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
                logger.error("Failed to insert row into '%s': %s",
                             table_name, e, exc_info=True)

    def insert_dataframe(
        self,
        table_name: str,
        df: pd.DataFrame,
        unique_cols: Optional[Sequence[str]] = None,
        chunksize: int = 900,  # Reduced to 900 to stay within pg8000 parameter limits
    ) -> None:
        """
        Insert a DataFrame into a table, using upsert if unique_cols are provided.
        Only PostgreSQL (GCP Cloud SQL) is supported.
        Optimized for large datasets with larger chunks and better connection handling.
        """
        if df.empty:
            logger.info(
                "DataFrame is empty; nothing to insert into '%s'.", table_name)
            return

        start_time = time.time()
        logger.info(
            "Starting bulk insert of %d rows into '%s' with chunksize %d",
            len(df),
            table_name,
            chunksize,
        )

        # Convert Date column to date if it's datetime
        if 'Date' in df.columns and pd.api.types.is_datetime64_any_dtype(df['Date']):
            df = df.copy()
            df['Date'] = df['Date'].dt.date

        tbl = Table(table_name, MetaData(), autoload_with=self.engine)

        if unique_cols:
            logger.info(
                "Upserting DataFrame into '%s' (%d rows) with unique columns: %s",
                table_name,
                len(df),
                unique_cols,
            )

            # Properly quote column names
            def quote_ident(col: str) -> str:
                if getattr(self.engine.dialect, "name", "") == "mysql":
                    return f"`{col}`"
                return f'"{col}"'

            quoted_columns = [quote_ident(col) for col in df.columns]
            quoted_unique_cols = [quote_ident(col) for col in unique_cols]
            non_unique_cols = [
                col for col in df.columns if col not in unique_cols]

            dialect_name = getattr(self.engine, "dialect", None)
            dialect_name = getattr(dialect_name, "name", "")

            # Helper to render SQL literals safely for basic types
            def _sql_literal(val):
                import pandas as _pd
                import datetime

                if val is None or (_pd.isna(val) if hasattr(_pd, "isna") else False):
                    return "NULL"
                if isinstance(val, str):
                    return "'" + val.replace("'", "''") + "'"
                if isinstance(val, datetime.date) and not isinstance(val, datetime.datetime):
                    return "'" + val.strftime('%Y-%m-%d') + "'"
                if isinstance(val, (_pd.Timestamp, _pd.Timedelta, datetime.datetime)) or hasattr(val, 'strftime'):
                    return "'" + val.strftime('%Y-%m-%d %H:%M:%S') + "'"
                return str(val)

            rows_sql = []
            for _, row in df.iterrows():
                values = [_sql_literal(row[col]) for col in df.columns]
                rows_sql.append("(" + ", ".join(values) + ")")

            if dialect_name == "sqlite":
                # SQLite: INSERT OR REPLACE with VALUES
                upsert_query = f"""
                INSERT OR REPLACE INTO {table_name} ({', '.join(quoted_columns)})
                VALUES {', '.join(rows_sql)}
                """
            elif dialect_name == "mysql":
                # MySQL: ON DUPLICATE KEY UPDATE
                update_clause = ", ".join(
                    [f"{quote_ident(col)} = VALUES({quote_ident(col)})" for col in non_unique_cols]
                )
                upsert_query = f"""
                INSERT INTO {table_name} ({', '.join(quoted_columns)})
                VALUES {', '.join(rows_sql)}
                ON DUPLICATE KEY UPDATE {update_clause}
                """
            elif dialect_name == "postgresql":
                # PostgreSQL: ON CONFLICT DO UPDATE
                update_clause = ", ".join(
                    [f"{quote_ident(col)} = EXCLUDED.{quote_ident(col)}" for col in non_unique_cols]
                )
                cols_alias = ", ".join([quote_ident(col)
                                       for col in df.columns])
                upsert_query = f"""
                INSERT INTO {table_name} ({', '.join(quoted_columns)})
                VALUES {', '.join(rows_sql)}
                ON CONFLICT ({', '.join(quoted_unique_cols)}) DO UPDATE SET {update_clause}
                """
            else:
                # Fallback: create temp table, then upsert if supported by DB, else replace
                temp_table_name = f"temp_{table_name}_{int(time.time())}"
                logger.info("Creating temp table '%s' for upsert",
                            temp_table_name)
                temp_columns = []
                for col in tbl.columns:
                    temp_columns.append(
                        Column(col.name, col.type, nullable=col.nullable))
                temp_tbl = Table(temp_table_name, MetaData(), *temp_columns)
                temp_tbl.create(self.engine, checkfirst=True)

                df.to_sql(
                    temp_table_name,
                    con=self.engine,
                    if_exists="append",
                    index=False,
                    chunksize=chunksize,
                    method="multi",
                )

                upsert_query = f"""
                INSERT INTO {table_name} ({', '.join(quoted_columns)})
                SELECT {', '.join(quoted_columns)} FROM {temp_table_name}
                """

            logger.info("Upsert query: %s", upsert_query.strip())
            with self.engine.begin() as conn:
                logger.info("Executing upsert query...")
                conn.execute(text(upsert_query))
            logger.info("Upsert completed into '%s'", table_name)
        else:
            logger.info("Appending DataFrame to '%s' (%d rows)",
                        table_name, len(df))
            # Use pandas to_sql for faster non-upsert inserts
            logger.info(
                "Starting pandas to_sql insert into '%s' with %d rows, chunksize %d",
                table_name,
                len(df),
                chunksize,
            )
            non_upsert_start = time.time()
            df.to_sql(
                table_name,
                con=self.engine,
                if_exists="append",
                index=False,
                chunksize=chunksize,
                method="multi",
            )
            non_upsert_elapsed = time.time() - non_upsert_start
            logger.info(
                "Non-upsert insert into '%s' completed in %.2f seconds (%.1f rows/sec)",
                table_name,
                non_upsert_elapsed,
                len(df) / non_upsert_elapsed if non_upsert_elapsed > 0 else 0,
            )

        end_time = time.time()
        logger.info(
            "Bulk insert completed in %.2f seconds (%.1f rows/sec)",
            end_time - start_time,
            len(df) / (end_time - start_time),
        )

    def close(self) -> None:
        """
        Dispose the session and optionally the engine if we own it.
        """
        logger.info("Closing database session.")
        if hasattr(self, "session") and self.session:
            self.session.close()

        # Only dispose engine if we created it (custom URL case)
        if hasattr(self, "_own_engine") and self._own_engine and hasattr(self, "engine"):
            logger.info("Disposing custom database engine.")
            self.engine.dispose()

    def get_secret_lazy():
        from data_pipeline.update_financial_data import get_secret

        return get_secret


# Updated import for market_data to use fallback mechanism
try:
    pass
except ImportError:
    pass
