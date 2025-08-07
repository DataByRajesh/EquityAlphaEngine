"""Compatibility layer exposing market data helpers.

This module re-exports the key functions from ``UK_data`` so that the rest
of the codebase – and the tests in this kata – can simply ``import
market_data``.  Historically the functionality lived in a module called
``market_data`` but it was renamed.  The tests still expect the old name, so
this thin wrapper restores the original interface without duplicating
implementation.
"""

import config
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from UK_data import (
    load_cached_fundamentals,
    save_fundamentals_cache,
    fetch_historical_data,
    fetch_fundamental_data,
    combine_price_and_fundamentals,
)
from financial_utils import round_financial_columns

__all__ = [
    "load_cached_fundamentals",
    "save_fundamentals_cache",
    "fetch_historical_data",
    "fetch_fundamental_data",
    "combine_price_and_fundamentals",
    "round_financial_columns",
]


def fetch_fundamentals_threaded(tickers: list[str], use_cache: bool = True) -> list[dict]:
    """Fetch fundamentals for multiple tickers concurrently.

    This re-implementation ensures that ``fetch_fundamental_data`` is looked up
    from this module so tests can patch it easily.
    """
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=config.MAX_THREADS) as executor:
        futures = {
            executor.submit(fetch_fundamental_data, ticker, use_cache=use_cache): ticker
            for ticker in tickers
        }
        for future in tqdm(as_completed(futures), total=len(futures), desc="Fetching Fundamentals"):
            ticker = futures[future]
            try:
                res = future.result()
                if res:
                    results.append(res)
                else:
                    logging.warning(f"No data returned for {ticker}")
            except Exception as exc:
                logging.error(f"Error fetching data for {ticker}: {exc}")
    return results

__all__.insert(4, "fetch_fundamentals_threaded")
