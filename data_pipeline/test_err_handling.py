import unittest
from data_pipeline import market_data
import numpy as np
import pandas as pd

class TestErrorHandling(unittest.TestCase):
    def test_missing_fields(self):
        # Simulate missing fields
        price_df = pd.DataFrame({
            'Date': ['2023-07-01'],
            'Ticker': ['ERR.L'],
            'Close': [100]
        })
        fundamentals = [{'Ticker': 'ERR.L'}]  # minimal
        combined = market_data.combine_price_and_fundamentals(price_df, fundamentals)
        rounded = market_data.round_financial_columns(combined)
        self.assertIn('returnOnEquity', rounded.columns)
        # Should not crash even with missing fields

    def test_bad_data(self):
        # Simulate NaNs and zeros
        price_df = pd.DataFrame({
            'Date': ['2023-07-01'],
            'Ticker': ['BAD.L'],
            'Open': [np.nan],
            'Close': [0],
            'Volume': [0]
        })
        fundamentals = [{'Ticker': 'BAD.L', 'returnOnEquity': np.nan}]
        combined = market_data.combine_price_and_fundamentals(price_df, fundamentals)
        rounded = market_data.round_financial_columns(combined)
        self.assertTrue(pd.isna(rounded['Open'].iloc[0]) or rounded['Open'].iloc[0] == 0)

if __name__ == '__main__':
    unittest.main()
