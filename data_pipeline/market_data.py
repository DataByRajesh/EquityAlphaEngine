"""Fetch and process UK market data.

This module provides helpers for downloading historical prices,
retrieving fundamental data and combining the results for further
processing in the equity pipeline.
"""

# import necessary libraries
import asyncio  # For asynchronous operations
import logging
import os  # For file and directory operations
from typing import Optional, Union  # For type hinting

# Third-party imports
import numpy as np  # For numerical operations
import pandas as pd  # For data manipulation
import yfinance as yf  # For fetching financial data

# Local imports
try:
    from data_pipeline.db_connection import engine, reinitialize_engine
    from data_pipeline.utils import get_secret

    from . import config  # Importing configuration file
    from .compute_factors import \
        compute_factors  # Function to compute financial factors
    from .financial_utils import \
        round_financial_columns  # For financial rounding utilities
    from .gmail_utils import create_message  # For Gmail API operations
    from .gmail_utils import get_gmail_service, send_message
    from .Macro_data import FiveYearMacroDataLoader  # Macro data loader
except ImportError:
    import data_pipeline.config as config
    from data_pipeline.compute_factors import compute_factors
    from data_pipeline.db_connection import engine, reinitialize_engine
    from data_pipeline.financial_utils import round_financial_columns
    from data_pipeline.gmail_utils import (create_message, get_gmail_service,
                                           send_message)
    from data_pipeline.Macro_data import FiveYearMacroDataLoader
    from data_pipeline.utils import get_secret

# Updated import for market_data to use fallback mechanism
try:
    from . import market_data
except ImportError:
    import data_pipeline.market_data as market_data

# Set up logging for debugging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Module-level logger
# logger = logging.getLogger(__name__)


def ensure_directories(dirs=None):
    """
    Ensure required directories exist for pipeline operation.
    Logs creation for traceability.
    """
    if dirs is None:
        dirs = [config.CACHE_DIR, config.DATA_DIR]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
        logger.info(f"Ensured directory exists: {d}")


# --- Caching functions ---

# The public functions ``load_cached_fundamentals`` and
# ``save_fundamentals_cache`` proxy to ``cache_utils`` so that the rest of this
# module does not need to know which backend is in use.  Any failures from the
# remote cache are logged and ignored so pipeline execution can continue.


try:
    from .cache_utils import \
        load_cached_fundamentals as _load_cached_fundamentals
    from .cache_utils import \
        save_fundamentals_cache as _save_fundamentals_cache
except ImportError:  # pragma: no cover - fallback for script execution
    from cache_utils import \
        load_cached_fundamentals as _load_cached_fundamentals  # type: ignore
    from cache_utils import save_fundamentals_cache as _save_fundamentals_cache


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


def fetch_macro_data(start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """Fetch macroeconomic indicators for the given date range.

    Returns a DataFrame or ``None`` if the loader fails or returns no data.
    """
    try:
        loader = FiveYearMacroDataLoader(
            start_date=start_date, end_date=end_date)
        macro_df = loader.get_combined_macro_data()
        if macro_df is None or macro_df.empty:
            logger.error("No macroeconomic data fetched.")
            return None
        logger.info("Macroeconomic data fetched successfully.")
        return macro_df
    except Exception as exc:  # pragma: no cover - best effort logging
        logger.error(f"Error fetching macroeconomic data: {exc}")
        return None


def fetch_historical_data(
    tickers: list[str], start_date: str, end_date: str
) -> pd.DataFrame:
    """
    Downloads historical price data for tickers, cleans and rounds it.
    Returns a DataFrame or empty DataFrame on failure.
    Includes retry logic and timeout for robustness.
    Disables yfinance caching to prevent database lock issues.
    """
    logger.debug(
        f"Fetching historical data for tickers: {tickers}, start_date: {start_date}, end_date: {end_date}"
    )
    logger.info(
        f"Downloading historical price data for {len(tickers)} tickers from {start_date} to {end_date}..."
    )
    if not tickers:
        logger.error("No tickers provided.")
        return pd.DataFrame()

    max_retries = 5  # Increased retries for better reliability
    timeout = 300  # 5 minutes timeout per attempt
    base_delay = 2  # Base delay for exponential backoff

    for attempt in range(max_retries):
        try:
            logger.info(
                f"Attempt {attempt + 1}/{max_retries} to download data...")

            # Configure yfinance to prevent database lock issues
            if config.YF_DISABLE_CACHE:
                # Create a unique cache directory for this process to avoid conflicts
                import uuid

                unique_cache_dir = os.path.join(
                    config.YF_CACHE_DIR, str(uuid.uuid4()))
                os.makedirs(unique_cache_dir, exist_ok=True)
                # Set timezone cache to unique directory to avoid conflicts
                yf.set_tz_cache_location(unique_cache_dir)
                # Note: yfinance doesn't have a direct way to disable all caching,
                # but we can minimize it by using unique directories

            # Explicitly set auto_adjust=False to ensure we get Adj Close column
            data = yf.download(
                tickers,
                start=start_date,
                end=end_date,
                progress=False,
                auto_adjust=False,
                timeout=timeout,
            )

            # yfinance returns a ``MultiIndex`` when multiple tickers are provided.
            # If only a single ticker is returned, the columns are a simple
            # ``Index`` which cannot be stacked. Detect this scenario and insert the
            # ticker symbol manually without calling ``stack``.
            if isinstance(data.columns, pd.MultiIndex):
                data = data.stack(level=1, future_stack=True).reset_index()
                data.rename(
                    columns={"level_0": "Date", "level_1": "Ticker"}, inplace=True
                )
            else:
                data = data.reset_index().rename(columns={"index": "Date"})
                # In single-ticker responses the symbol isn't part of the columns,
                # so assume the first requested ticker corresponds to the data
                # returned.
                data["Ticker"] = tickers[0]

            if "Volume" in data.columns:
                data["Volume"] = data["Volume"].fillna(0).astype(int)

            # Ensure Adj Close column exists - if not, use Close as fallback
            if "Adj Close" not in data.columns and "Close" in data.columns:
                data["Adj Close"] = data["Close"]
                logger.warning(
                    "Adj Close column missing, using Close as fallback")

            required_cols = {
                "Date",
                "Open",
                "High",
                "Low",
                "Close",
                "Adj Close",
                "Volume",
                "Ticker",
            }
            missing_cols = required_cols - set(data.columns)
            if missing_cols:
                logger.error(
                    f"Historical data missing required columns: {missing_cols}"
                )
                return pd.DataFrame()
            logger.info("Historical data fetched successfully.")
            logger.debug("Historical data fetch completed.")
            return data
        except Exception as e:
            error_msg = str(e).lower()
            if "database is locked" in error_msg:
                logger.warning(
                    f"Database lock detected on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    # Longer delay for database lock issues
                    delay = base_delay * (2**attempt) + 1
                    logger.info(
                        f"Waiting {delay} seconds before retry due to database lock..."
                    )
                    import time

                    time.sleep(delay)
                    continue
                else:
                    logger.error(
                        "All attempts failed due to persistent database lock. This may indicate concurrent yfinance usage."
                    )
            elif "timeout" in error_msg or "connection" in error_msg:
                logger.warning(f"Network issue on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)
                    logger.info(
                        f"Waiting {delay} seconds before retry due to network issue..."
                    )
                    import time

                    time.sleep(delay)
                    continue
            else:
                logger.warning(
                    f"Unexpected error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)
                    logger.info(f"Waiting {delay} seconds before retry...")
                    import time

                    time.sleep(delay)
                    continue

            # If we reach here, all retries are exhausted
            logger.error(
                f"All {max_retries} attempts failed. Returning empty DataFrame."
            )
            return pd.DataFrame()


async def _fetch_single_info(
    ticker_obj: yf.Ticker,
    ticker: str,
    retries: int,
    backoff_factor: int,
    request_timeout: int,
) -> tuple[str, dict]:
    """Asynchronously fetch ``info`` for a single ticker with retries.

    This helper runs the blocking ``ticker_obj.info`` call in a thread and
    retries with exponential backoff, using ``asyncio.sleep`` to avoid blocking
    the event loop. Returns a ``(ticker, info_dict)`` tuple where ``info_dict``
    is empty on failure. Includes special handling for database lock issues.
    """
    delay = config.INITIAL_DELAY
    for attempt in range(retries):
        try:
            info = await asyncio.wait_for(
                asyncio.to_thread(lambda: ticker_obj.info), timeout=request_timeout
            )
            return ticker, info
        except (
            Exception
        ) as exc:  # pragma: no cover - network errors are non-deterministic
            error_msg = str(exc).lower()
            if "database is locked" in error_msg:
                logger.warning(
                    f"Database lock detected for {ticker} on attempt {attempt+1}: {exc}"
                )
                if attempt < retries - 1:
                    # Longer delay for database lock issues
                    delay = max(
                        delay * backoff_factor, 3.0
                    )  # Minimum 3 seconds for DB locks
                    logger.info(
                        f"Waiting {delay} seconds before retry for {ticker} due to database lock..."
                    )
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(
                        f"All attempts failed for {ticker} due to persistent database lock"
                    )
            elif "timeout" in error_msg or "connection" in error_msg:
                logger.warning(
                    f"Network issue for {ticker} on attempt {attempt+1}: {exc}"
                )
                if attempt < retries - 1:
                    await asyncio.sleep(delay)
                    delay *= backoff_factor
                    continue
            else:
                logger.warning(
                    f"Attempt {attempt+1} failed for {ticker}: {exc}")
                if attempt < retries - 1:
                    await asyncio.sleep(delay)
                    delay *= backoff_factor
                    continue

            # If we reach here, all retries are exhausted
            return ticker, {}
    return ticker, {}


def fetch_fundamental_data(
    ticker_symbols: list[str],
    retries: int = config.MAX_RETRIES,
    backoff_factor: int = config.BACKOFF_FACTOR,
    use_cache: bool = True,
    cache_expiry_minutes: int = config.CACHE_EXPIRY_MINUTES,
    request_timeout: int = 10,
) -> Union[list[dict], "asyncio.Task[list[dict]]"]:
    """Fetch fundamental data for multiple tickers concurrently.

    The function first serves data from the cache when available. Remaining
    tickers are fetched concurrently using ``yf.Tickers`` and non-blocking
    retry logic.  If called without a running event loop, ``asyncio.run`` is
    used to drive the asynchronous execution.  When a loop is already running
    (e.g. inside a notebook) the coroutine is scheduled on that loop via
    :func:`asyncio.create_task` and the caller must ``await`` the returned task.
    Should the async execution fail for any reason, the function falls back to
    sequential fetching to ensure callers receive best-effort data.  Returns a
    list of dictionaries with key ratios or an awaitable resolving to such a
    list when a loop is running.
    """

    results: list[dict] = []
    remaining: list[str] = []
    if use_cache:
        for symbol in ticker_symbols:
            cached = load_cached_fundamentals(
                symbol, expiry_minutes=cache_expiry_minutes
            )
            if cached is not None:
                logger.info(f"Loaded cached fundamentals for {symbol}")
                results.append(cached)
            else:
                remaining.append(symbol)
    else:
        remaining = list(ticker_symbols)

    if not remaining:
        return results

    async def _fetch_all() -> list[dict]:
        """Fetch fundamentals for the remaining tickers asynchronously."""
        tickers_obj = yf.Tickers(" ".join(remaining))
        tasks = [
            _fetch_single_info(
                tickers_obj.tickers[t], t, retries, backoff_factor, request_timeout
            )
            for t in remaining
        ]

        fetched: list[tuple[str, dict]] = []
        try:
            fetched = await asyncio.gather(*tasks)
        except Exception as e:  # pragma: no cover - best effort logging
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
                logger.error(
                    f"Failed to fetch fundamentals for {symbol} after {retries} attempts"
                )
                continue
            key_ratios = {
                "Ticker": symbol,
                "CompanyName": info.get("longName"),
                "returnOnEquity": info.get("returnOnEquity"),
                "grossMargins": info.get("grossMargins"),
                "operatingMargins": info.get("operatingMargins"),
                "profitMargins": info.get("profitMargins"),
                "priceToBook": info.get("priceToBook"),
                "trailingPE": info.get("trailingPE"),
                "forwardPE": info.get("forwardPE"),
                "priceToSalesTrailing12Months": info.get(
                    "priceToSalesTrailing12Months"
                ),
                "debtToEquity": info.get("debtToEquity"),
                "currentRatio": info.get("currentRatio"),
                "quickRatio": info.get("quickRatio"),
                "dividendYield": info.get("dividendYield"),
                "marketCap": info.get("marketCap"),
                "beta": info.get("beta"),
                "averageVolume": info.get("averageVolume"),
            }
            results.append(key_ratios)
            if use_cache:
                save_fundamentals_cache(symbol, key_ratios)

        logger.debug("Fundamental data fetch completed.")
        return results

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_fetch_all())
    else:
        return asyncio.create_task(_fetch_all())


def combine_price_and_fundamentals(
    price_df: pd.DataFrame, fundamentals_list: list[dict]
) -> pd.DataFrame:
    """
    Merges price data DataFrame with a list of fundamental dicts (as DataFrame).
    Returns a combined DataFrame.
    """
    logger.debug("Combining price data and fundamental data.")
    fundamentals_df = pd.DataFrame(fundamentals_list)

    # Ensure expected fundamental columns exist even if missing from the raw
    # data.  This prevents downstream operations from failing when a field is
    # absent in the source response.
    required_cols = [
        "returnOnEquity",
        "grossMargins",
        "operatingMargins",
        "profitMargins",
        "priceToBook",
        "trailingPE",
        "forwardPE",
        "priceToSalesTrailing12Months",
        "debtToEquity",
        "currentRatio",
        "quickRatio",
        "dividendYield",
        "marketCap",
        "beta",
        "averageVolume",
    ]
    for col in required_cols:
        if col not in fundamentals_df.columns:
            fundamentals_df[col] = np.nan

    combined_df = pd.merge(price_df, fundamentals_df, on="Ticker", how="left")
    logger.debug("Combination of price and fundamental data completed.")
    return combined_df


def main(engine, start_date, end_date):
    """Process market data using the provided database engine."""
    import signal
    import time

    # Set overall timeout (30 minutes)
    timeout_seconds = 30 * 60

    def timeout_handler(signum, frame):
        logger.error("Pipeline timed out after %d seconds", timeout_seconds)
        raise TimeoutError("Pipeline execution exceeded timeout")

    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout_seconds)

    try:
        start_time = time.time()
        logger.info("Starting market data pipeline at %s",
                    time.ctime(start_time))

        # Ensure cache and data directories exist at module import
        ensure_directories()

        logger.info("Fetching market data...")
        tickers = config.FTSE_100_TICKERS

        # Example usage of the engine
        try:
            with engine.connect() as connection:
                logger.info("Connected to the database successfully.")
        except Exception as e:
            logger.error(f"Failed to connect to the database: {e}")

        hist_df = fetch_historical_data(tickers, start_date, end_date)
        if hist_df.empty:
            logger.warning("No historical data fetched.")
            return

        fundamentals_list = fetch_fundamental_data(tickers, use_cache=True)
        if not fundamentals_list:
            logger.error("No fundamentals data fetched. Exiting.")
            return

        price_fundamentals_df = combine_price_and_fundamentals(
            hist_df, fundamentals_list
        )

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
            from data_pipeline.db_utils import DBHelper

            db_helper = DBHelper(engine=engine)  # Use provided engine
            try:
                db_helper.create_table(
                    financial_tbl, financial_df, primary_keys=[
                        "Date", "Ticker"]
                )
                db_helper.insert_dataframe(
                    financial_tbl, financial_df, unique_cols=["Date", "Ticker"]
                )

                macro_df = fetch_macro_data(start_date, end_date)
                if macro_df is not None:
                    macro_tbl = "macro_data_tbl"
                    db_helper.create_table(
                        macro_tbl, macro_df, primary_keys=["Date"])
                    db_helper.insert_dataframe(
                        macro_tbl, macro_df, unique_cols=["Date"]
                    )
            finally:
                db_helper.close()

            # Prepare and send email notification
            try:
                gmail_service = get_gmail_service()
            except FileNotFoundError as e:
                logger.error(e)
                gmail_service = None

            if gmail_service is None:
                logger.error(
                    "Failed to initialize Gmail service. Email notification will not be sent."
                )
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
        logger.info("Market data processing completed.")

        end_time = time.time()
        elapsed = end_time - start_time
        logger.info("Pipeline completed successfully in %.2f seconds", elapsed)
    except TimeoutError:
        logger.error("Pipeline timed out")
        raise
    except Exception as e:
        logger.error("Pipeline failed with error: %s", e, exc_info=True)
        raise
    finally:
        signal.alarm(0)  # Cancel the alarm
