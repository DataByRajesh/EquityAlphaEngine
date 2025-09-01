import logging
import os

import pandas as pd
import quandl

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

DEFAULT_API_KEY = os.environ.get("QUANDL_API_KEY")


class FiveYearMacroDataLoader:
    def __init__(
        self,
        api_key: str | None = None,
        start_date: str = "2020-01-01",
        end_date: str = "2025-12-31",  # cover full years
    ):
        self.api_key = api_key or DEFAULT_API_KEY
        if not self.api_key:
            raise ValueError("QUANDL_API_KEY is not configured. Set env or pass api_key.")
        quandl.ApiConfig.api_key = self.api_key
        self.start_date = start_date
        self.end_date = end_date

    def fetch_gdp_growth(self) -> pd.DataFrame | None:
        """IMF WEO Real GDP growth, YoY % (annual)."""
        try:
            df = quandl.get(
                "ODA/GBR_NGDP_RPCH",
                start_date=self.start_date,
                end_date=self.end_date,
            ).reset_index().rename(columns={"Value": "GDP_Growth_YoY", "Date": "Date"})
            # Normalize to Jan 1 of the year for stable merge keys
            df["Date"] = pd.to_datetime(df["Date"]).dt.to_period("Y").dt.to_timestamp()
            return df[["Date", "GDP_Growth_YoY"]].sort_values("Date")
        except Exception as e:
            logger.error("Error fetching GDP Growth Data: %s", e)
            return None

    def fetch_inflation_rate(self) -> pd.DataFrame:
        """Placeholder inflation series (annual, constant 2.5%)."""
        dates = pd.date_range(start=self.start_date, end=self.end_date, freq="Y")
        df = pd.DataFrame({
            "Date": dates.to_period("Y").to_timestamp(),  # normalize to year start
            "Inflation_YoY": [2.5] * len(dates),
        })
        return df

    def get_combined_macro_data(self) -> pd.DataFrame | None:
        gdp = self.fetch_gdp_growth()
        infl = self.fetch_inflation_rate()
        if gdp is None or gdp.empty:
            return None
        out = gdp.merge(infl, on="Date", how="outer").sort_values("Date").reset_index(drop=True)
        return out


if __name__ == "__main__":

    def store_macro_data_to_db(macro_df: pd.DataFrame):
        """Store macroeconomic data in the DB using DBHelper (expects DATABASE_URL)."""
        try:
            macro_df = macro_df.copy()
            macro_df["Date"] = pd.to_datetime(macro_df["Date"])
            from data_pipeline.db_utils import DBHelper
            db = DBHelper()
            db.create_table("macro_data", macro_df, primary_keys=["Date"])
            db.insert_dataframe("macro_data", macro_df, unique_cols=["Date"])
            db.close()
            logger.info("✅ Macro data stored in 'macro_data'.")
        except Exception as e:
            logger.error("❌ Failed to store macro data in DB: %s", e)

    loader = FiveYearMacroDataLoader()
    macro = loader.get_combined_macro_data()
    if macro is not None:
        logger.info("✅ Combined UK Macro Data (tail):\n%s", macro.tail())
        macro.to_csv("UK_5Year_Macro_Data.csv", index=False)
        store_macro_data_to_db(macro)
    else:
        logger.error("❌ Failed to fetch macro data.")
    """
    if __name__ == "__main__":
        # Main block bypassed for now
        # def store_macro_data_to_db(macro_df: pd.DataFrame):
        #     """
        #     Store macroeconomic data in the DB using DBHelper (expects DATABASE_URL).
        #     """
        #     try:
        #         macro_df = macro_df.copy()
        #         macro_df["Date"] = pd.to_datetime(macro_df["Date"])
        #         from data_pipeline.db_utils import DBHelper
        #         db = DBHelper()
        #         db.create_table("macro_data", macro_df, primary_keys=["Date"])
        #         db.insert_dataframe("macro_data", macro_df, unique_cols=["Date"])
        #         db.close()
        #         logger.info("✅ Macro data stored in 'macro_data'.")
        #     except Exception as e:
        #         logger.error("❌ Failed to store macro data in DB: %s", e)
        # loader = FiveYearMacroDataLoader()
        # macro = loader.get_combined_macro_data()
        # if macro is not None:
        #     logger.info("✅ Combined UK Macro Data (tail):\n%s", macro.tail())
        #     macro.to_csv("UK_5Year_Macro_Data.csv", index=False)
        #     store_macro_data_to_db(macro)
        # else:
        #     logger.error("❌ Failed to fetch macro data.")
    """
