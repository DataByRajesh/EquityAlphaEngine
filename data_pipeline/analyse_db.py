import pandas as pd
from sqlalchemy import create_engine

import config
import logging


DB_PATH = config.DATABASE_URL


def main() -> None:
    """Analyse the stock database and print basic statistics."""
    engine = create_engine(DB_PATH)
    try:
        # Load a sample of the data
        df = pd.read_sql("SELECT * FROM stock_data", engine)

        # General stats
        print(df.info())
        print(f"describe {df.describe()}")

        # Check for missing data
        print(f" Missing data count {df.isnull().sum()}")

        # Check for duplicates
        print(
            f"duplicates data count {df.duplicated(subset=['Date', 'Ticker']).sum()}"
        )

        # Check data coverage per ticker
        print(f"data coverage per ticker {df['Ticker'].value_counts()}")

        # Spot-check for outliers
        print(df[["Close", "Volume", "marketCap"]].describe(), end="\n\n")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
