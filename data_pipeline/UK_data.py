# data_pipeline/UK_data.py
# This module is responsible for fetching and processing market data for the data pipeline.

# import necessary libraries
import asyncio  # For asynchronous operations
import logging
import os  # For file and directory operations
from typing import Optional  # For type hinting

# Third-party imports
import numpy as np  # For numerical operations
import pandas as pd  # For data manipulation
import yfinance as yf  # For fetching financial data


# Local imports

try:  # Prefer package-relative imports
    from .compute_factors import compute_factors  # Function to compute financial factors
    from .db_utils import DBHelper  # Importing the DBHelper class for database operations
    from .gmail_utils import get_gmail_service, create_message, send_message  # For Gmail API operations
    from . import config  # Importing configuration file
    from .financial_utils import round_financial_columns  # For financial rounding utilities
except ImportError:  # Fallback for running as a script without package context
    from compute_factors import compute_factors  # type: ignore  # pragma: no cover
    from db_utils import DBHelper  # type: ignore  # pragma: no cover
    from gmail_utils import get_gmail_service, create_message, send_message  # type: ignore  # pragma: no cover
    import config  # type: ignore  # pragma: no cover
    from financial_utils import round_financial_columns  # type: ignore  # pragma: no cover

# Module-level logger
logger = logging.getLogger(__name__)

# Ensure cache directory exists or create it
os.makedirs(config.CACHE_DIR, exist_ok=True)
# Ensure data directory exists or create it
os.makedirs(config.DATA_DIR, exist_ok=True)


# --- Caching functions ---

# The public functions ``load_cached_fundamentals`` and
# ``save_fundamentals_cache`` proxy to ``cache_utils`` so that the rest of this
# module does not need to know which backend is in use.  Any failures from the
# remote cache are logged and ignored so pipeline execution can continue.


try:
    from .cache_utils import (
        load_cached_fundamentals as _load_cached_fundamentals,
        save_fundamentals_cache as _save_fundamentals_cache,
    )
except ImportError:  # pragma: no cover - fallback for script execution
    from cache_utils import (  # type: ignore
        load_cached_fundamentals as _load_cached_fundamentals,
        save_fundamentals_cache as _save_fundamentals_cache,
    )

def load_cached_fundamentals(
    ticker: str,
    expiry_minutes: int = config.CACHE_EXPIRY_MINUTES,
) -> Optional[dict]:
    try:
        return _load_cached_fundamentals(ticker, expiry_minutes=expiry_minutes)
    except Exception as e:  # pragma: no cover - best effort logging
        logger.warning(f"Failed to load cache for {ticker}: {e}")
        return None


def save_fundamentals_cache(ticker: str, data: dict) -> None:
    try:
        _save_fundamentals_cache(ticker, data)
    except Exception as e:  # pragma: no cover - best effort logging
        logger.warning(f"Failed to save cache for {ticker}: {e}")

def fetch_historical_data(
    tickers: list[str], start_date: str, end_date: str
) -> pd.DataFrame:
    """
    Downloads historical price data for tickers, cleans and rounds it.
    Returns a DataFrame or empty DataFrame on failure.
    """
    logger.info(f"Downloading historical price data for {len(tickers)} tickers from {start_date} to {end_date}...")
    if not tickers:
        logger.error("No tickers provided.")
        return pd.DataFrame()
    try:
        data = yf.download(tickers, start=start_date, end=end_date, progress=False)
        data = data.stack(level=1).reset_index()
        data.rename(columns={'level_1': 'Ticker'}, inplace=True)
        if 'Volume' in data.columns:
            data['Volume'] = data['Volume'].fillna(0).astype(int)
        logger.info("Historical data fetched successfully.")
        return data
    except Exception as e:
        logger.error(f"Error downloading historical data: {e}")
        return pd.DataFrame()

async def _fetch_single_info(ticker_obj: yf.Ticker, ticker: str, retries: int, backoff_factor: int, request_timeout: int) -> tuple[str, dict]:
    """Asynchronously fetch ``info`` for a single ticker with retries.

    This helper runs the blocking ``ticker_obj.info`` call in a thread and
    retries with exponential backoff, using ``asyncio.sleep`` to avoid blocking
    the event loop. Returns a ``(ticker, info_dict)`` tuple where ``info_dict``
    is empty on failure.
    """
    delay = config.INITIAL_DELAY
    for attempt in range(retries):
        try:
            info = await asyncio.wait_for(asyncio.to_thread(lambda: ticker_obj.info), timeout=request_timeout)
            return ticker, info
        except Exception as exc:  # pragma: no cover - network errors are non-deterministic
            logger.warning(f"Attempt {attempt+1} failed for {ticker}: {exc}")
            if attempt < retries - 1:
                await asyncio.sleep(delay)
                delay *= backoff_factor
    return ticker, {}


def fetch_fundamental_data(
    ticker_symbols: list[str],
    retries: int = config.MAX_RETRIES,
    backoff_factor: int = config.BACKOFF_FACTOR,
    use_cache: bool = True,
    cache_expiry_minutes: int = config.CACHE_EXPIRY_MINUTES,
    request_timeout: int = 10,
) -> list[dict]:
    """Fetch fundamental data for multiple tickers concurrently.

    The function first serves data from the cache when available. Remaining
    tickers are fetched concurrently using ``yf.Tickers`` and non-blocking
    retry logic.  If an event loop is already running (e.g. inside a notebook
    or other async-aware environment) the existing loop is reused via
    :func:`asyncio.get_event_loop` and ``run_until_complete``.  Should the async
    execution fail for any reason, the function falls back to sequential
    fetching to ensure callers receive best-effort data.  Returns a list of
    dictionaries with key ratios.
    """

    results: list[dict] = []
    remaining: list[str] = []
    if use_cache:
        for symbol in ticker_symbols:
            cached = load_cached_fundamentals(symbol, expiry_minutes=cache_expiry_minutes)
            if cached is not None:
                logger.info(f"Loaded cached fundamentals for {symbol}")
                results.append(cached)
            else:
                remaining.append(symbol)
    else:
        remaining = list(ticker_symbols)

    if remaining:
        tickers_obj = yf.Tickers(" ".join(remaining))

        async def _fetch_all() -> list[tuple[str, dict]]:
            tasks = [
                _fetch_single_info(tickers_obj.tickers[t], t, retries, backoff_factor, request_timeout)
                for t in remaining
            ]
            return await asyncio.gather(*tasks)

        fetched: list[tuple[str, dict]] = []
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                fetched = loop.run_until_complete(_fetch_all())
            else:
                fetched = loop.run_until_complete(_fetch_all())
        except RuntimeError:
            fetched = asyncio.run(_fetch_all())
        except Exception as e:
            logger.error(
                f"Asynchronous fetch failed, falling back to sequential execution: {e}",
                exc_info=True,
            )
            for t in remaining:
                try:
                    info = tickers_obj.tickers[t].info
                except Exception as exc:  # pragma: no cover - best effort fallback
                    logger.error(f"Synchronous fetch failed for {t}: {exc}")
                    info = {}
                fetched.append((t, info))

        for symbol, info in fetched:
            if not info:
                logger.error(f"Failed to fetch fundamentals for {symbol} after {retries} attempts")
                continue
            key_ratios = {
                'Ticker': symbol,
                'CompanyName': info.get('longName'),
                'returnOnEquity': info.get('returnOnEquity'),
                'grossMargins': info.get('grossMargins'),
                'operatingMargins': info.get('operatingMargins'),
                'profitMargins': info.get('profitMargins'),
                'priceToBook': info.get('priceToBook'),
                'trailingPE': info.get('trailingPE'),
                'forwardPE': info.get('forwardPE'),
                'priceToSalesTrailing12Months': info.get('priceToSalesTrailing12Months'),
                'debtToEquity': info.get('debtToEquity'),
                'currentRatio': info.get('currentRatio'),
                'quickRatio': info.get('quickRatio'),
                'dividendYield': info.get('dividendYield'),
                'marketCap': info.get('marketCap'),
                'beta': info.get('beta'),
                'averageVolume': info.get('averageVolume'),
            }
            results.append(key_ratios)
            if use_cache:
                save_fundamentals_cache(symbol, key_ratios)

    return results

def fetch_fundamentals_threaded(
    tickers: list[str], use_cache: bool = True
) -> list[dict]:
    """Backward compatible wrapper for ``fetch_fundamental_data``.

    Historically, fundamentals were fetched in separate threads per ticker. The
    new implementation already performs concurrent requests, so this wrapper
    simply delegates to :func:`fetch_fundamental_data`.
    """
    return fetch_fundamental_data(tickers, use_cache=use_cache)

def combine_price_and_fundamentals(price_df: pd.DataFrame, fundamentals_list: list[dict]) -> pd.DataFrame:
    """
    Merges price data DataFrame with a list of fundamental dicts (as DataFrame).
    Returns a combined DataFrame.
    """
    fundamentals_df = pd.DataFrame(fundamentals_list)

    # Ensure expected fundamental columns exist even if missing from the raw
    # data.  This prevents downstream operations from failing when a field is
    # absent in the source response.
    required_cols = [
        'returnOnEquity', 'grossMargins', 'operatingMargins', 'profitMargins',
        'priceToBook', 'trailingPE', 'forwardPE',
        'priceToSalesTrailing12Months', 'debtToEquity', 'currentRatio',
        'quickRatio', 'dividendYield', 'marketCap', 'beta', 'averageVolume',
    ]
    for col in required_cols:
        if col not in fundamentals_df.columns:
            fundamentals_df[col] = np.nan

    combined_df = pd.merge(price_df, fundamentals_df, on='Ticker', how='left')
    return combined_df

def main(tickers, start_date, end_date, use_cache=True):

    hist_df = fetch_historical_data(tickers, start_date, end_date)
    if hist_df.empty:
        logger.error("No historical data fetched. Exiting.")
        return

    fundamentals_list = fetch_fundamental_data(tickers, use_cache=use_cache)
    if not fundamentals_list:
        logger.error("No fundamentals data fetched. Exiting.")
        return
    
    price_fundamentals_df = combine_price_and_fundamentals(hist_df, fundamentals_list)
    
    
    # Compute factors
    logger.info("Computing factors...")
    financial_df = compute_factors(price_fundamentals_df)

    if financial_df is None or financial_df.empty:
        logger.error("Failed to compute financial factors. Exiting.")
        return
    financial_df = round_financial_columns(financial_df)
    
    # Save computed factors to DB
    if financial_df is not None:
        financial_tbl = "financial_tbl"
        Dbhelper = DBHelper(config.DATABASE_URL)  # Create a new DBHelper instance
        Dbhelper.create_table(
            financial_tbl,
            financial_df,
            primary_keys=["Date", "Ticker"],
        )  # Create table if not exists
        Dbhelper.insert_dataframe(
            financial_tbl,
            financial_df,
            unique_cols=["Date", "Ticker"],
        )  # Upsert computed factors
        Dbhelper.close()

        # Prepare and send email notification
        try:
            gmail_service = get_gmail_service()  # Initialize Gmail API service once
        except FileNotFoundError as e:
            logger.error(e)
            gmail_service = None

        if gmail_service is None:
            logger.error("Failed to initialize Gmail service. Email notification will not be sent.")
            return
    
        sender = "raj.analystdata@gmail.com"
        recipient = "raj.analystdata@gmail.com"
        subject = "Data Fetch Success"
        body = "Financial data computed and saved to DB."

        msg = create_message(sender, recipient, subject, body)
        send_message(gmail_service, "me", msg)
        logger.info("Email notification sent successfully.")
        logger.info("Financial data computed and saved to DB.")
    else:
        logger.error("Failed to compute and not saved to DB. Exiting.")

if __name__ == "__main__":
    import argparse
    from datetime import datetime, timedelta

    # CLI
    parser = argparse.ArgumentParser(
        description="Fetch historical and fundamental data for FTSE 100 stocks."
    )
    parser.add_argument(
        "--start_date",
        type=str,
        help="Start date for historical data (YYYY-MM-DD). If provided, takes precedence over --years.",
    )
    parser.add_argument(
        "--end_date",
        type=str,
        help="End date for historical data (YYYY-MM-DD). Defaults to today if omitted.",
    )
    parser.add_argument(
        "--years",
        type=int,
        default=10,
        help="Number of years back to fetch when --start_date is not provided (default: 10).",
    )

    args = parser.parse_args()

    # Resolve dates
    end_date = args.end_date or datetime.today().strftime("%Y-%m-%d")

    if args.start_date:
        start_date = args.start_date
    else:
        years = args.years if (args.years and args.years > 0) else 10
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        start_dt = end_dt - timedelta(days=years * 365)
        start_date = start_dt.strftime("%Y-%m-%d")

    # Basic validation
    if datetime.strptime(start_date, "%Y-%m-%d") > datetime.strptime(end_date, "%Y-%m-%d"):
        raise SystemExit(f"start_date ({start_date}) cannot be after end_date ({end_date}).")

    main(config.FTSE_100_TICKERS, start_date, end_date)

