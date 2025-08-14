import io
import logging
import pandas as pd
from sqlalchemy import create_engine

import config


logger = logging.getLogger(__name__)

DB_PATH = config.DATABASE_URL

logger = logging.getLogger(__name__)

def main() -> None:
    """Load stock data from the DB and log summary information."""
    engine = create_engine(DB_PATH)
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
        logger.info("data coverage per ticker\n%s", df["Ticker"].value_counts())
        logger.info(
            "Selected columns description\n%s",
            df[["Close", "Volume", "marketCap"]].describe(),
        )

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()

