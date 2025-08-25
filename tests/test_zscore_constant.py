import unittest
import pandas as pd
import numpy as np

from data_pipeline.compute_factors import compute_factors


class TestZScoreConstant(unittest.TestCase):
    def test_constant_values_return_zero(self):
        df = pd.DataFrame({
            'Date': ['2024-01-01', '2024-01-01'],
            'Ticker': ['AAA', 'BBB'],
            'Close': [100, 100],
            'Volume': [1000, 1000],
            'trailingPE': [10, 10],
            'priceToBook': [2, 2],
            'returnOnEquity': [0.1, 0.1],
            'profitMargins': [0.2, 0.2],
            'marketCap': [1e6, 1e6],
        })

        result = compute_factors(df)

        self.assertTrue(np.all(result['norm_quality_score'].fillna(0) == 0))
        self.assertTrue(np.all(result['z_earnings_yield'].fillna(0) == 0))


if __name__ == '__main__':  # pragma: no cover
    unittest.main()
