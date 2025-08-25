import unittest
import pandas as pd
import numpy as np
from data_pipeline.compute_factors import compute_factors
from data_pipeline import market_data
from data_pipeline.db_utils import DBHelper


def test_compute_factors_docstring():
    """Ensure ``compute_factors`` exposes helpful documentation."""
    doc = compute_factors.__doc__
    assert doc is not None
    assert 'Ticker' in doc and 'momentum' in doc

class TestFullPipeline(unittest.TestCase):
    def setUp(self):
        # Prepare synthetic dataset
        self.price_df = pd.DataFrame({
            'Date': pd.to_datetime(['2023-07-01', '2023-07-02']),
            'Ticker': ['ADV.L', 'ADV.L'],
            'Open': [100, 101],
            'High': [110, 111],
            'Low': [90, 91],
            'Close': [105, 106],
            'Volume': [1000, 1100]
        })
        self.fundamentals = [{
            'Ticker': 'ADV.L',
            'returnOnEquity': 0.2,
            'profitMargins': 0.15,
            'priceToBook': 1.8,
            'trailingPE': 12.0,
            'marketCap': 2000000,
            # Add all required fields for compute_factors
            'grossMargins': 0.3, 'operatingMargins': 0.2, 'forwardPE': 11.5,
            'priceToSalesTrailing12Months': 2.0, 'debtToEquity': 0.4, 'currentRatio': 1.2,
            'quickRatio': 1.1, 'dividendYield': 0.03, 'beta': 1.05, 'averageVolume': 1000
        }] * 2

    def test_pipeline_to_db(self):
        # Merge, round, factor
        combined = market_data.combine_price_and_fundamentals(self.price_df, self.fundamentals)
        rounded = market_data.round_financial_columns(combined)
        rounded['Date'] = rounded['Date'].astype(str)
        factors = compute_factors(rounded)
        # Save to temp DB
        dbfile = "test_pipeline.db"
        db_url = f"sqlite:///{dbfile}"
        helper = DBHelper(db_url)
        helper.create_table("factors", factors)
        helper.insert_dataframe("factors", factors)
        readback = pd.read_sql("SELECT * FROM factors", helper.engine)
        self.assertEqual(len(readback), len(factors))
        helper.close()
        import os
        os.remove(dbfile)

    def test_factor_composite_and_ranking(self):
        # Should rank and score correctly
        combined = market_data.combine_price_and_fundamentals(self.price_df, self.fundamentals)
        rounded = market_data.round_financial_columns(combined)
        rounded['Date'] = rounded['Date'].astype(str)
        factors = compute_factors(rounded)
        self.assertIn('factor_composite', factors.columns)
        # Check values are finite or nan (no strings or infs)
        self.assertTrue(np.all(np.isfinite(factors['factor_composite']) | np.isnan(factors['factor_composite'])))

if __name__ == '__main__':
    unittest.main()
