# Standard library imports
from io import StringIO

# Third-party imports
import pandas as pd

# Local imports
try:
    from . import config
except ImportError:
    import data_pipeline.config as config

try:
    from .update_financial_data import get_secret
except ImportError:
    from data_pipeline.update_financial_data import get_secret

# Updated import for market_data to use fallback mechanism
try:
    from . import market_data
except ImportError:
    import data_pipeline.market_data as market_data

# Refactored to use the centralized engine from db_connection.py
from data_pipeline.db_connection import engine

# Use the config helper to create a file logger
logger = config.get_file_logger(__name__)

DB_PATH = get_secret("DATABASE_URL")


# Lazy import for DBHelper to resolve circular dependency
# Replace the direct import with a function-level import
def get_db_helper():
    from data_pipeline.db_utils import DBHelper

    return DBHelper


def main() -> None:
    """Load stock data from the DB and log summary information."""
    try:
        df = pd.read_sql("SELECT * FROM stock_data", engine)

        buffer = StringIO()
        df.info(buf=buffer)
        logger.info(buffer.getvalue())

        logger.info("describe\n%s", df.describe())
        logger.info("Missing data count\n%s", df.isnull().sum())
        logger.info(
            "duplicates data count %d",
            df.duplicated(subset=["Date", "Ticker"]).sum(),
        )
        logger.info("data coverage per ticker\n%s",
                    df["Ticker"].value_counts())
        logger.info(
            "Selected columns description\n%s",
            df[["Close", "Volume", "marketCap"]].describe(),
        )
    except Exception as e:
        logger.error(f"Error during database operation: {e}", exc_info=True)
        raise RuntimeError("Database operation failed")


if __name__ == "__main__":
    main()
