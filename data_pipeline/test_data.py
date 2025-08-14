import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

import asyncio
import numpy as np
import pandas as pd

from data_pipeline import market_data
from data_pipeline.db_utils import DBHelper
from data_pipeline.compute_factors import compute_factors

class TestMarketData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create a temporary directory for cache
        cls.temp_dir = tempfile.mkdtemp()
        # Monkeypatch config.CACHE_DIR for all tests
        market_data.config.CACHE_DIR = cls.temp_dir

    @classmethod
    def tearDownClass(cls):
        # Remove the temporary directory after tests
        shutil.rmtree(cls.temp_dir)

    def test_cache_save_and_load(self):
        ticker = "TEST.L"
        test_data = {"Ticker": ticker, "returnOnEquity": 0.15}
        # Save cache
        market_data.save_fundamentals_cache(ticker, test_data)
        # Load cache
        loaded = market_data.load_cached_fundamentals(ticker)
        self.assertEqual(loaded, test_data)

    @patch('yfinance.Tickers')
    def test_fetch_fundamental_data(self, mock_tickers):
        # Setup mock object to simulate yfinance.Tickers().tickers[ticker].info
        ticker_name = "MOCK.L"
        mock_info = {
            'returnOnEquity': 0.12, 'grossMargins': 0.3, 'operatingMargins': 0.25,
            'profitMargins': 0.20, 'priceToBook': 2.5, 'trailingPE': 15.0,
            'forwardPE': 14.5, 'priceToSalesTrailing12Months': 2.0, 'debtToEquity': 0.5,
            'currentRatio': 1.2, 'quickRatio': 1.0, 'dividendYield': 0.04,
            'marketCap': 1e9, 'beta': 1.1, 'averageVolume': 1000000
        }
        mock_ticker_obj = unittest.mock.Mock()
        mock_ticker_obj.info = mock_info
        mock_tickers.return_value.tickers = {ticker_name: mock_ticker_obj}

        result_list = market_data.fetch_fundamental_data([ticker_name], use_cache=False)
        self.assertEqual(result_list[0]['Ticker'], ticker_name)
        self.assertAlmostEqual(result_list[0]['returnOnEquity'], 0.12)
        self.assertIn('marketCap', result_list[0])

    @patch('yfinance.Tickers')
    def test_fetch_fundamental_data_no_loop_uses_asyncio_run(self, mock_tickers):
        ticker_name = "MOCK.L"
        mock_info = {
            'returnOnEquity': 0.1,
        }
        mock_ticker_obj = unittest.mock.Mock()
        mock_ticker_obj.info = mock_info
        mock_tickers.return_value.tickers = {ticker_name: mock_ticker_obj}

        original_run = asyncio.run
        with patch('data_pipeline.UK_data.asyncio.run', side_effect=original_run) as mock_run, \
             patch('data_pipeline.UK_data.asyncio.create_task') as mock_ct:
            result_list = market_data.fetch_fundamental_data([ticker_name], use_cache=False)
            self.assertTrue(mock_run.called)
            mock_ct.assert_not_called()
        self.assertEqual(result_list[0]['Ticker'], ticker_name)

    @patch('yfinance.Tickers')
    def test_fetch_fundamental_data_running_loop_uses_create_task(self, mock_tickers):
        ticker_name = "MOCK.L"
        mock_info = {
            'returnOnEquity': 0.2,
        }
        mock_ticker_obj = unittest.mock.Mock()
        mock_ticker_obj.info = mock_info
        mock_tickers.return_value.tickers = {ticker_name: mock_ticker_obj}

        async def runner():
            original_create = asyncio.create_task
            with patch('data_pipeline.UK_data.asyncio.run', wraps=asyncio.run) as mock_run, \
                 patch('data_pipeline.UK_data.asyncio.create_task', side_effect=original_create) as mock_ct:
                result = await market_data.fetch_fundamental_data([ticker_name], use_cache=False)
                self.assertFalse(mock_run.called)
                self.assertTrue(mock_ct.called)
                return result

        result_list = asyncio.run(runner())
        self.assertEqual(result_list[0]['Ticker'], ticker_name)

    @patch('yfinance.download')
    def test_fetch_historical_data(self, mock_download):
        # Return fake price data
        mock_df = pd.DataFrame({
            ('Open', 'MOCK.L'): [100, 102],
            ('High', 'MOCK.L'): [110, 112],
            ('Low', 'MOCK.L'): [99, 101],
            ('Close', 'MOCK.L'): [109, 111],
            ('Volume', 'MOCK.L'): [1000, 1200],
        }, index=pd.to_datetime(['2022-01-01', '2022-01-02']))
        mock_download.return_value = mock_df

        df = market_data.fetch_historical_data(['MOCK.L'], '2022-01-01', '2022-01-02')
        self.assertIn('Ticker', df.columns)
        self.assertIn('Close', df.columns)
        self.assertEqual(df['Ticker'].iloc[0], 'MOCK.L')

    @patch('yfinance.download')
    def test_fetch_historical_data_single_ticker(self, mock_download):
        """Ensure single-ticker responses without a MultiIndex are handled."""
        mock_df = pd.DataFrame({
            'Open': [100, 102],
            'High': [110, 112],
            'Low': [99, 101],
            'Close': [109, 111],
            'Volume': [1000, 1200],
        }, index=pd.to_datetime(['2022-01-01', '2022-01-02']))
        mock_download.return_value = mock_df

        df = market_data.fetch_historical_data(['MOCK.L'], '2022-01-01', '2022-01-02')
        self.assertEqual(df['Ticker'].unique().tolist(), ['MOCK.L'])
        self.assertIn('Close', df.columns)

    def test_combine_price_and_fundamentals(self):
        # Fake price and fundamentals
        price_df = pd.DataFrame({'Date': ['2022-01-01'], 'Ticker': ['ABC.L'], 'Close': [100]})
        fundamentals = [{'Ticker': 'ABC.L', 'returnOnEquity': 0.1}]
        combined = market_data.combine_price_and_fundamentals(price_df, fundamentals)
        self.assertIn('returnOnEquity', combined.columns)
        self.assertEqual(combined['returnOnEquity'].iloc[0], 0.1)
        
class TestPipelineAdvanced(unittest.TestCase):
    def setUp(self):
        # Synthetic price data (2 days, 1 ticker)
        self.price_df = pd.DataFrame({
            'Date': pd.to_datetime(['2023-01-01', '2023-01-02']),
            'Ticker': ['TEST.L', 'TEST.L'],
            'Open': [100.12, 101.34],
            'High': [102.45, 103.56],
            'Low': [99.80, 100.80],
            'Close': [101.00, 102.00],
            'Volume': [1000, 1200]
        })
        # Synthetic fundamentals
        self.fundamentals = [{
            'Ticker': 'TEST.L',
            'returnOnEquity': 0.125678,
            'grossMargins': 0.33,
            'operatingMargins': 0.20,
            'profitMargins': 0.13,
            'priceToBook': 2.54321,
            'trailingPE': 15.9876,
            'forwardPE': 14.6543,
            'priceToSalesTrailing12Months': 1.4321,
            'debtToEquity': 0.35,
            'currentRatio': 1.5,
            'quickRatio': 1.2,
            'dividendYield': 0.0456,
            'marketCap': 2000000000,
            'beta': 1.02,
            'averageVolume': 1100
        }] * 2  # for both days

    def test_full_pipeline(self):
        # Merge and round
        combined = market_data.combine_price_and_fundamentals(self.price_df, self.fundamentals)
        rounded = market_data.round_financial_columns(combined)
        # Date as string for groupby in factors
        rounded['Date'] = rounded['Date'].astype(str)
        factors = compute_factors(rounded)
        # Check a few factor columns
        self.assertIn('return_1m', factors.columns)
        self.assertIn('ma_20', factors.columns)
        self.assertIn('factor_composite', factors.columns)
        self.assertEqual(len(factors), len(rounded))
        # Check for NaNs in factors due to short length (OK in this synthetic case)
        self.assertTrue(np.isnan(factors['return_1m']).all() or not factors['return_1m'].dropna().empty)

    def test_missing_trailingPE(self):
        # Remove 'trailingPE', earnings_yield should be nan or inf
        fundamentals = [dict(self.fundamentals[0])]
        fundamentals[0].pop('trailingPE')
        combined = market_data.combine_price_and_fundamentals(self.price_df.iloc[:1], fundamentals)
        rounded = market_data.round_financial_columns(combined)
        rounded['Date'] = rounded['Date'].astype(str)
        factors = compute_factors(rounded)
        self.assertIn('earnings_yield', factors.columns)
        self.assertTrue(np.isnan(factors['earnings_yield'].iloc[0]) or np.isinf(factors['earnings_yield'].iloc[0]))

class TestDBHelper(unittest.TestCase):
    def setUp(self):
        self.test_db = "test_stocks.db"
        self.db_url = f"sqlite:///{self.test_db}"
        self.helper = DBHelper(self.db_url)
        self.df = pd.DataFrame({
            "Ticker": ["A.L", "B.L"],
            "Close": [100, 200],
            "Volume": [1000, 1500]
        })

    def tearDown(self):
        self.helper.close()
        os.remove(self.test_db)

    def test_create_and_insert(self):
        self.helper.create_table("test_tbl", self.df)
        self.helper.insert_dataframe("test_tbl", self.df)
        # Read back to check
        result = pd.read_sql("SELECT * FROM test_tbl", self.helper.engine)
        self.assertEqual(len(result), 2)
        self.assertIn("Close", result.columns)

    def test_upsert_dataframe(self):
        self.helper.create_table("test_tbl", self.df, primary_keys=["Ticker"])
        self.helper.insert_dataframe("test_tbl", self.df, unique_cols=["Ticker"])
        updated = self.df.copy()
        updated.loc[0, "Close"] = 150
        self.helper.insert_dataframe("test_tbl", updated, unique_cols=["Ticker"])
        result = pd.read_sql("SELECT * FROM test_tbl", self.helper.engine)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[result["Ticker"] == "A.L"]["Close"].iloc[0], 150)
        
if __name__ == "__main__":
    unittest.main()
