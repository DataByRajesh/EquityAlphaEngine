import logging
import os

import quandl
import pandas as pd

DEFAULT_API_KEY = os.environ.get("QUANDL_API_KEY")


logger = logging.getLogger(__name__)

class FiveYearMacroDataLoader:
    def __init__(self, api_key: str | None = None,
                 start_date: str = "2020-01-01",
                 end_date: str = "2025-01-01"):
        self.api_key = api_key or DEFAULT_API_KEY
        if self.api_key is None:
            raise ValueError(
                "QUANDL_API_KEY is not configured. Set the env var or pass api_key."

            )
        quandl.ApiConfig.api_key = self.api_key
        self.start_date = start_date
        self.end_date = end_date

    def fetch_gdp_growth(self):
        """
        Fetch 5-Year UK GDP Growth (YoY %) from IMF via Quandl
        """
        try:
            data = quandl.get("ODA/GBR_NGDP_RPCH", start_date=self.start_date, end_date=self.end_date)
            data.reset_index(inplace=True)
            data.rename(columns={"Value": "GDP_Growth_YoY"}, inplace=True)
            return data
        except Exception as e:
            logger.error("Error fetching GDP Growth Data: %s", e)
            return None

    def fetch_inflation_rate(self):
        """
        Placeholder for Inflation Data.
        Replace this with a real data fetch once available.
        """
        dates = pd.date_range(start=self.start_date, end=self.end_date, freq='Q')
        inflation_data = pd.DataFrame({
            'Date': dates,
            'Inflation_YoY': [2.5 for _ in range(len(dates))]  # Placeholder: 2.5%
        })
        return inflation_data

    def get_combined_macro_data(self):
        gdp_data = self.fetch_gdp_growth()
        inflation_data = self.fetch_inflation_rate()
        if gdp_data is not None:
            combined_data = pd.merge(gdp_data, inflation_data, on='Date', how='outer').sort_values('Date')
            return combined_data
        else:
            return None

if __name__ == "__main__":
    loader = FiveYearMacroDataLoader()

    macro_data = loader.get_combined_macro_data()
    if macro_data is not None:
        logger.info("✅ Combined 5-Year UK Macro Data:")
        logger.info("\n%s", macro_data)
        # Optionally save to CSV
        macro_data.to_csv("UK_5Year_Macro_Data.csv", index=False)
    else:
        logger.error("❌ Failed to fetch macro data.")
