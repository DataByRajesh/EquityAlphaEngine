import logging
import os

import pandas as pd
import requests

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
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
            raise ValueError(
                "QUANDL_API_KEY is not configured. Set env or pass api_key.")
        quandl.ApiConfig.api_key = self.api_key
        self.start_date = start_date
        self.end_date = end_date

    def fetch_gdp_growth(self) -> pd.DataFrame | None:
        """IMF WEO Real GDP growth, YoY % (annual)."""
        try:
            df = (
                quandl.get(
                    "ODA/GBR_NGDP_RPCH",
                    start_date=self.start_date,
                    end_date=self.end_date,
                )
                .reset_index()
                .rename(columns={"Value": "GDP_Growth_YoY", "Date": "Date"})
            )
            # Normalize to Jan 1 of the year for stable merge keys
            df["Date"] = pd.to_datetime(
                df["Date"]).dt.to_period("Y").dt.to_timestamp()
            return df[["Date", "GDP_Growth_YoY"]].sort_values("Date")
        except Exception as e:
            logger.error("Error fetching GDP Growth Data: %s", e)
            # Fallback to mock data
            logger.info("Using mock GDP growth data as fallback.")
            dates = pd.date_range(start=self.start_date, end=self.end_date, freq="YE")
            df = pd.DataFrame(
                {
                    "Date": dates.to_period("Y").to_timestamp(),
                    "GDP_Growth_YoY": [2.0] * len(dates),  # Mock constant growth
                }
            )
            return df

    def fetch_inflation_rate(self) -> pd.DataFrame:
        """Placeholder inflation series (annual, constant 2.5%)."""
        dates = pd.date_range(start=self.start_date,
                              end=self.end_date, freq="YE")
        df = pd.DataFrame(
            {
                # normalize to year start
                "Date": dates.to_period("Y").to_timestamp(),
                "Inflation_YoY": [2.5] * len(dates),
            }
        )
        return df

    def get_combined_macro_data(self) -> pd.DataFrame | None:
        gdp = self.fetch_gdp_growth()
        infl = self.fetch_inflation_rate()
        if gdp is None or gdp.empty:
            return None
        out = gdp.merge(infl, on="Date", how="outer").sort_values(
            "Date").reset_index(drop=True)
        return out
