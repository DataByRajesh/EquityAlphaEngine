import unittest
from unittest.mock import patch

from data_pipeline import market_data


class TestFundamentalFetch(unittest.TestCase):
    @patch("data_pipeline.market_data.fetch_fundamental_data")
    def test_multi_ticker_fetch(self, mock_fetch):
        mock_fetch.return_value = [
            {"Ticker": "A.L", "returnOnEquity": 0.1},
            {"Ticker": "B.L", "returnOnEquity": 0.2},
            {"Ticker": "C.L", "returnOnEquity": 0.3},
        ]
        tickers = ["A.L", "B.L", "C.L"]
        out = market_data.fetch_fundamental_data(tickers, use_cache=False)
        self.assertEqual(len(out), 3)
        tickers_seen = {d["Ticker"] for d in out}
        self.assertEqual(tickers_seen, {"A.L", "B.L", "C.L"})
        return_on_equity = {d["Ticker"]: d["returnOnEquity"] for d in out}
        self.assertAlmostEqual(return_on_equity["A.L"], 0.1)
        self.assertAlmostEqual(return_on_equity["B.L"], 0.2)
        self.assertAlmostEqual(return_on_equity["C.L"], 0.3)
        mock_fetch.assert_called_once_with(tickers, use_cache=False)


if __name__ == "__main__":
    unittest.main()
