"""
CLI to populate or refresh the financial data table.

Deployment context:
All secrets and config (e.g., DATABASE_URL, API keys) are loaded from environment variables
as set by the GitHub Actions workflow or your cloud deployment environment.
No secrets are hardcoded or loaded from files; config.py centralizes all env var usage.

This script inspects the existing ``financial_tbl`` table in the configured
``DATABASE_URL``. If the requested date range is not present it will invoke the
full market data pipeline to fetch and store the data. Intended for use as a
scheduled job so that dashboards can simply read from an already populated
database.
"""

from __future__ import annotations

import argparse
import logging
from datetime import datetime, timedelta

import pandas as pd
from sqlalchemy import create_engine, inspect
from google.cloud.sql.connector import Connector
import pg8000

try:  # Prefer package-relative imports
    from . import config, market_data
except ImportError:  # pragma: no cover - fallback when run as script
    import config  # type: ignore
    import market_data  # type: ignore


logger = logging.getLogger(__name__)


def _needs_fetch(engine, start_date: str, end_date: str) -> bool:
    """Return ``True`` if the database lacks ``financial_tbl`` data for range."""
    inspector = inspect(engine)
    if not inspector.has_table("financial_tbl"):
        logger.warning("Table 'financial_tbl' does not exist in the database.")
        return True

    date_range = pd.read_sql(
        "SELECT MIN(Date) AS min_date, MAX(Date) AS max_date FROM financial_tbl",
        engine,
    )
    if date_range.empty:
        logger.warning("Table 'financial_tbl' exists but contains no data.")
        return True

    min_date = pd.to_datetime(date_range["min_date"].iloc[0])
    max_date = pd.to_datetime(date_range["max_date"].iloc[0])
    if pd.isna(min_date) or pd.isna(max_date):
        logger.warning("Table 'financial_tbl' contains invalid date range.")
        return True

    return not (
        min_date <= pd.to_datetime(
            start_date) and max_date >= pd.to_datetime(end_date)
    )


def main(start_date: str, end_date: str) -> None:
    """Run ``market_data.main`` if the database is missing requested data."""
    connector = Connector()
    try:
        def getconn():
            return connector.connect(
                config.DATABASE_URL,  # Replace with your Cloud SQL instance connection name
                "pg8000",
                user=config.DB_USER,
                password=config.DB_PASSWORD,
                db=config.DB_NAME,
            )

        engine = create_engine("postgresql+pg8000://", creator=getconn)
        if _needs_fetch(engine, start_date, end_date):
            market_data.main(config.FTSE_100_TICKERS, start_date, end_date)
        else:
            logger.info(
                "financial_tbl already contains requested data; skipping fetch."
            )
    finally:
        connector.close()
        engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Populate or refresh the financial_tbl with UK market data",
    )
    parser.add_argument(
        "--start_date",
        type=str,
        help="Start date for historical data (YYYY-MM-DD). If omitted, uses --years.",
    )
    parser.add_argument(
        "--end_date",
        type=str,
        help="End date for historical data (YYYY-MM-DD). Defaults to today.",
    )
    parser.add_argument(
        "--years",
        type=int,
        default=10,
        help="Number of years back to fetch when --start_date is not provided (default: 10).",
    )

    args = parser.parse_args()
    end_date = args.end_date or datetime.today().strftime("%Y-%m-%d")
    if args.start_date:
        start_date = args.start_date
    else:
        years = args.years if (args.years and args.years > 0) else 10
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        start_dt = end_dt - timedelta(days=years * 365)
        start_date = start_dt.strftime("%Y-%m-%d")

    main(start_date, end_date)
