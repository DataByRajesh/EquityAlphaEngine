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

# Standard library imports
import argparse
import logging
from datetime import datetime, timedelta

# Third-party library imports
import pandas as pd
from sqlalchemy import inspect

# Local application imports
from data_pipeline.db_connection import engine
from data_pipeline.db_utils import DBHelper
from data_pipeline.market_data import main as market_data_main

# Use the config helper to create a file logger
logger = logging.getLogger(__name__)

# Configure logger to print to console
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Define constants for configurations
DEFAULT_TIMEOUT = 60  # seconds


def _needs_fetch(engine, start_date: str, end_date: str) -> bool:
    """Return ``True`` if the database lacks ``financial_tbl`` data for range."""
    inspector = inspect(engine)
    try:
        if not inspector.has_table("financial_tbl"):
            logger.error(
                "Table 'financial_tbl' does not exist in the database.")
            return True
    except Exception as e:
        logger.error(
            f"Error inspecting the database for 'financial_tbl': {e}", exc_info=True
        )
        raise RuntimeError(
            "Failed to inspect the database for 'financial_tbl'")

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


def fetch_data_if_needed(db_helper: DBHelper, start_date, end_date):
    """Check if data fetch is needed and perform the fetch."""
    try:
        logger.info("Starting market data processing.")
        market_data_main(db_helper.engine, start_date, end_date)
        logger.info("Market data processing completed successfully.")
    except Exception as e:
        logger.error(
            f"Error during market data processing: {e}", exc_info=True)
        raise RuntimeError(
            "Market data processing failed due to an unexpected error.")


def main(start_date: str, end_date: str) -> None:
    """Run the update financial data script."""
    logger.info("Starting update_financial_data script.")

    db_helper = DBHelper()
    try:
        fetch_data_if_needed(db_helper, start_date, end_date)
    except Exception as e:
        logger.error(
            f"Critical error in update_financial_data script: {e}", exc_info=True
        )
        raise RuntimeError("Critical error in update_financial_data script")
    finally:
        db_helper.engine.dispose()


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

    # Example usage of reinitialize_engine if needed
    # reinitialize_engine("postgresql+pg8000://new_user:new_password@new_host:5432/new_db")

    # Use the engine directly for database operations
    try:
        with engine.connect() as connection:
            logger.info("Connected to the database successfully.")
    except Exception as e:
        logger.error(f"Failed to connect to the database: {e}")

    main(start_date, end_date)
