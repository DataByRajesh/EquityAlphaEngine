import pandas as pd

from data_pipeline import market_data


def test_main_stores_macro_data(monkeypatch):
    calls = []

    class DummyDB:
        def __init__(self, url):
            pass

        def create_table(self, name, df, primary_keys):
            calls.append(("create", name, list(df.columns), primary_keys))

        def insert_dataframe(self, name, df, unique_cols):
            calls.append(("insert", name, len(df), unique_cols))

        def close(self):
            calls.append(("close",))

    monkeypatch.setattr(market_data, "DBHelper", DummyDB)
    monkeypatch.setattr(
        market_data,
        "fetch_historical_data",
        lambda tickers, start, end: pd.DataFrame(
            {
                "Date": [pd.Timestamp("2020-01-01")],
                "Open": [1],
                "High": [1],
                "Low": [1],
                "Close": [1],
                "Adj Close": [1],
                "Volume": [1],
                "Ticker": ["A"],
            }
        ),
    )
    monkeypatch.setattr(
        market_data,
        "fetch_fundamental_data",
        lambda tickers, use_cache=True: [{"Ticker": "A"}],
    )
    monkeypatch.setattr(
        market_data,
        "compute_factors",
        lambda df: pd.DataFrame(
            {"Date": [pd.Timestamp("2020-01-01")], "Ticker": ["A"]}
        ),
    )
    monkeypatch.setattr(market_data, "round_financial_columns", lambda df: df)
    monkeypatch.setattr(
        market_data,
        "fetch_macro_data",
        lambda start, end: pd.DataFrame(
            {
                "Date": [pd.Timestamp("2020-01-01")],
                "GDP_Growth_YoY": [1.0],
                "Inflation_YoY": [2.0],
            }
        ),
    )
    monkeypatch.setattr(market_data, "get_gmail_service", lambda: object())
    monkeypatch.setattr(market_data, "create_message",
                        lambda *args, **kwargs: None)
    monkeypatch.setattr(market_data, "send_message",
                        lambda *args, **kwargs: None)

    market_data.main(["A"], "2020-01-01", "2020-12-31")

    created_tables = [c[1] for c in calls if c[0] == "create"]
    assert "macro_data_tbl" in created_tables
