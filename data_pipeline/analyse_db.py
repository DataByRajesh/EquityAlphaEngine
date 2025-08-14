import io
import logging
import pandas as pd
from sqlalchemy import create_engine

import config


DB_PATH = config.DATABASE_URL

logger = logging.getLogger(__name__)

def main() -> None:
    """Analyse the stock database and print basic statistics."""
    engine = create_engine(DB_PATH)
    try:
        # Load a sample of the data
        df = pd.read_sql("SELECT * FROM stock_data", engine)

        # General stats
        buf = io.StringIO()
        df.info(buf=buf)
        logger.info(buf.getvalue())
        logger.info("describe %s", df.describe())

        # Check for missing data
        logger.info(" Missing data count %s", df.isnull().sum())

        # Check for duplicates
        logger.info(
            "duplicates data count %s",
            df.duplicated(subset=["Date", "Ticker"]).sum(),
        )

        # Check data coverage per ticker
        logger.info("data coverage per ticker %s", df["Ticker"].value_counts())

        # Spot-check for outliers
        logger.info("\n%s\n", df[["Close", "Volume", "marketCap"]].describe())
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
