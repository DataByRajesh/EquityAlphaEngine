# data_pipeline/UK_data.py
# This module is responsible for fetching and processing market data for the data pipeline.

# import necessary libraries
import logging

# Setup logging ONCE, right after the first import
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Importing required libraries

# Standard library imports
import argparse # For command line argument parsing
import json # For JSON handling
import math # For mathematical operations
import os # For file and directory operations
import sys # For system operations
import sqlite3 # For SQLite database operations
import time # For time-related functions
from concurrent.futures import ThreadPoolExecutor, as_completed # For multithreading
from datetime import datetime, timedelta # For date handling
from typing import Optional # For type hinting
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation # For precise decimal rounding

# Third-party imports
import numpy as np # For numerical operations
import pandas as pd # For data manipulation
from tqdm import tqdm # For progress bar
import yfinance as yf # For fetching financial data


# Local imports
from compute_factors import compute_factors # Function to compute financial factors
from db_utils import DBHelper # Importing the DBHelper class for database operations
from gmail_utils import get_gmail_service, create_message, send_message # For Gmail API operations
import config # Importing configuration file
from financial_utils import round_financial_columns # For financial rounding utilities


# Ensure cache directory exists or create it
os.makedirs(config.CACHE_DIR, exist_ok=True)
# Ensure data directory exists or create it
os.makedirs(config.DATA_DIR, exist_ok=True)


# --- Caching functions ---

# The public functions ``load_cached_fundamentals`` and
# ``save_fundamentals_cache`` proxy to ``cache_utils`` so that the rest of this
# module does not need to know which backend is in use.  Any failures from the
# remote cache are logged and ignored so pipeline execution can continue.

from cache_utils import (
    load_cached_fundamentals as _load_cached_fundamentals,
    save_fundamentals_cache as _save_fundamentals_cache,
)


def load_cached_fundamentals(
    ticker: str,
    cache_dir: str = config.CACHE_DIR,
    expiry_minutes: int = config.CACHE_EXPIRY_MINUTES,
) -> Optional[dict]:
    try:
        return _load_cached_fundamentals(ticker, expiry_minutes=expiry_minutes)
    except Exception as e:  # pragma: no cover - best effort logging
        logging.warning(f"Failed to load cache for {ticker}: {e}")
        return None


def save_fundamentals_cache(
    ticker: str, data: dict, cache_dir: str = config.CACHE_DIR
) -> None:
    try:
        _save_fundamentals_cache(ticker, data)
    except Exception as e:  # pragma: no cover - best effort logging
        logging.warning(f"Failed to save cache for {ticker}: {e}")

def fetch_historical_data(
    tickers: list[str], start_date: str, end_date: str
) -> pd.DataFrame:
    """
    Downloads historical price data for tickers, cleans and rounds it.
    Returns a DataFrame or empty DataFrame on failure.
    """
    logging.info(f"Downloading historical price data for {len(tickers)} tickers from {start_date} to {end_date}...")
    if not tickers:
        logging.error("No tickers provided.")
        return pd.DataFrame()
    try:
        data = yf.download(tickers, start=start_date, end=end_date, progress=False)
        data = data.stack(level=1).reset_index()
        data.rename(columns={'level_1': 'Ticker'}, inplace=True)
        if 'Volume' in data.columns:
            data['Volume'] = data['Volume'].fillna(0).astype(int)
        logging.info("Historical data fetched successfully.")
        return data
    except Exception as e:
        logging.error(f"Error downloading historical data: {e}")
        return pd.DataFrame()

def fetch_fundamental_data(
    ticker_symbol: str,
    retries: int = config.MAX_RETRIES,
    backoff_factor: int = config.BACKOFF_FACTOR,
    use_cache: bool = True,
    cache_expiry_minutes: int = config.CACHE_EXPIRY_MINUTES # 1 day expires by default
) -> dict:
    """
    Fetches fundamental data for a given ticker, with optional caching.
    Returns the data as a dict.
    """
    if use_cache:
        cached = load_cached_fundamentals(ticker_symbol,expiry_minutes=cache_expiry_minutes)
        if cached is not None:
            logging.info(f"Loaded cached fundamentals for {ticker_symbol}")
            return cached

    ticker = yf.Ticker(ticker_symbol)
    attempt = 0
    delay = config.INITIAL_DELAY
    while attempt < retries:
        try:
            info = ticker.info
            key_ratios = {
                'Ticker': ticker_symbol,
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
                'averageVolume': info.get('averageVolume')
            }
            logging.info(f"Company Name: {info.get('longName')}")
            if use_cache:
                save_fundamentals_cache(ticker_symbol, key_ratios)
            logging.info(f"Fetched fundamentals for {ticker_symbol}")
            return key_ratios
        except Exception as e:
            logging.warning(f"Attempt {attempt+1} failed for {ticker_symbol}: {e}")
            attempt += 1
            time.sleep(delay)
            delay *= backoff_factor
    logging.error(f"Failed to fetch fundamentals for {ticker_symbol} after {retries} attempts")
    return {}

def fetch_fundamentals_threaded(
    tickers: list[str], use_cache: bool = True
) -> list[dict]:
    """
    Fetches fundamental data for a list of tickers using threads.
    Returns a list of dicts (one per successful fetch).
    """
    results = []
    with ThreadPoolExecutor(max_workers=config.MAX_THREADS) as executor:
        futures = {executor.submit(fetch_fundamental_data, ticker, use_cache=use_cache): ticker for ticker in tickers}
        for future in tqdm(as_completed(futures), total=len(futures), desc="Fetching Fundamentals"):
            ticker = futures[future]
            try:
                res = future.result()
                if res:
                    results.append(res)
                else:
                    logging.warning(f"No data returned for {ticker}")
            except Exception as e:
                logging.error(f"Error fetching data for {ticker}: {e}")
    return results

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
        logging.error("No historical data fetched. Exiting.")
        return

    fundamentals_list = fetch_fundamentals_threaded(tickers, use_cache=use_cache)
    if not fundamentals_list:
        logging.error("No fundamentals data fetched. Exiting.")
        return
    
    price_fundamentals_df = combine_price_and_fundamentals(hist_df, fundamentals_list)
    
    
    # Compute factors
    logging.info("Computing factors...")
    financial_df = compute_factors(price_fundamentals_df)

    if financial_df is None or financial_df.empty:
        logging.error("Failed to compute financial factors. Exiting.")
        return
    financial_df = round_financial_columns(financial_df)
    
    # Save computed factors to DB
    if financial_df is not None:
        financial_tbl = "financial_tbl"
        Dbhelper = DBHelper(config.DATABASE_URL)  # Create a new DBHelper instance
        Dbhelper.create_table(financial_tbl, financial_df) # Create table if not exists
        Dbhelper.insert_dataframe(financial_tbl, financial_df) # Insert computed factors into the table
        Dbhelper.close()

        # Prepare and send email notification
        gmail_service = get_gmail_service()  # Initialize Gmail API service once

        if gmail_service is None:
            logging.error("Failed to initialize Gmail service. Email notification will not be sent.")
            return
    
        sender = "raj.analystdata@gmail.com"
        recipient = "raj.analystdata@gmail.com"
        subject = "Data Fetch Success"
        body = "Financial data computed and saved to DB."

        msg = create_message(sender, recipient, subject, body)
        send_message(gmail_service, "me", msg)
        logging.info("Email notification sent successfully.")
        logging.info("Financial data computed and saved to DB.")
    else:
        logging.error("Failed to compute and not saved to DB. Exiting.")

if __name__ == "__main__":
    # Command line argument parsing
    parser = argparse.ArgumentParser(description="Fetch historical and fundamental data for FTSE 100 stocks.")
    parser.add_argument('--start_date', type=str, default='2020-01-01', help='Start date for historical data (YYYY-MM-DD)')
    parser.add_argument('--end_date', type=str, default=datetime.today().strftime('%Y-%m-%d'), help='End date for historical data (YYYY-MM-DD)')
    
    args = parser.parse_args()

    main(config.FTSE_100_TICKERS, args.start_date, args.end_date)
