"""Compatibility layer exposing market data helpers.

This module re-exports the key functions from ``UK_data`` so that the rest
of the codebase – and the tests in this kata – can simply ``import
market_data``.  Historically the functionality lived in a module called
``market_data`` but it was renamed.  The tests still expect the old name, so
this thin wrapper restores the original interface without duplicating
implementation.
"""


import logging

try:
    from . import config
    from .UK_data import (
        load_cached_fundamentals,
        save_fundamentals_cache,
        fetch_historical_data,
        fetch_fundamental_data,
        combine_price_and_fundamentals,
    )
    from .financial_utils import round_financial_columns
except ImportError:  # pragma: no cover
    import config
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
    "fetch_fundamentals_threaded",
    "combine_price_and_fundamentals",
    "round_financial_columns",
]


def fetch_fundamentals_threaded(tickers: list[str], use_cache: bool = True) -> list[dict]:
    """Fetch fundamentals for multiple tickers concurrently.

    The heavy lifting is delegated to :func:`fetch_fundamental_data`, which now
    performs bulk asynchronous requests. This wrapper exists so tests can easily
    patch the underlying function without depending on its location.
    """
    return fetch_fundamental_data(tickers, use_cache=use_cache)

