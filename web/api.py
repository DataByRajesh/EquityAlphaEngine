from contextlib import contextmanager
from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Any
import time
import logging

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, TimeoutError as SQLTimeoutError
from pg8000.exceptions import InterfaceError

from data_pipeline.compute_factors import compute_factors
from data_pipeline.db_connection import engine, get_db
from data_pipeline.utils import get_secret

# Configure logging
logger = logging.getLogger(__name__)

app = FastAPI()

# In-memory cache for API responses
CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_LOCK = Lock()
CACHE_TTL = timedelta(minutes=10)  # Cache for 10 minutes

# Retry configuration for database operations
MAX_DB_RETRIES = 3
DB_RETRY_DELAY = 1  # seconds

# Query optimization settings
QUERY_TIMEOUT = 30  # seconds
CONNECTION_POOL_SIZE = 10
MAX_OVERFLOW = 20


def get_cached_or_compute(key: str, compute_func):
    """Get from cache or compute and cache the result."""
    now = datetime.now()
    with CACHE_LOCK:
        if key in CACHE:
            cached = CACHE[key]
            if now - cached['timestamp'] < CACHE_TTL:
                return cached['data']
            else:
                del CACHE[key]  # Expired, remove

    # Compute new
    data = compute_func()
    with CACHE_LOCK:
        CACHE[key] = {'data': data, 'timestamp': now}
    return data


def execute_query_with_retry(query: text, params: dict = None, max_retries: int = MAX_DB_RETRIES):
    """Execute a database query with retry logic for connection timeouts."""
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            logger.debug(f"Executing query attempt {attempt + 1}/{max_retries}")
            
            # Use the global engine with connection from pool
            with engine.connect() as conn:
                # Set query timeout
                conn = conn.execution_options(autocommit=True)
                df = pd.read_sql(query, conn, params=params or {})
                logger.debug(f"Query executed successfully, returned {len(df)} rows")
                return df.to_dict(orient="records")
                
        except (OperationalError, SQLTimeoutError, InterfaceError, ConnectionError) as e:
            last_exception = e
            logger.warning(
                f"Database query attempt {attempt + 1}/{max_retries} failed: {str(e)[:200]}..."
            )
            
            if attempt < max_retries - 1:
                wait_time = DB_RETRY_DELAY * (2 ** attempt)  # Exponential backoff
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error(f"All {max_retries} query attempts failed. Last error: {e}")
                
        except Exception as e:
            logger.error(f"Unexpected error during query execution: {e}")
            raise HTTPException(status_code=500, detail="Database query failed")
    
    # If we get here, all retries failed
    error_msg = f"Database query failed after {max_retries} attempts: {str(last_exception)}"
    logger.error(error_msg)
    raise HTTPException(status_code=503, detail="Database temporarily unavailable")


class FactorsRequest(BaseModel):
    data: list[dict]


@app.get("/health")
def health() -> dict:
    """Enhanced health check endpoint with database connectivity test."""
    try:
        # Test database connectivity
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "degraded", "database": "disconnected", "error": str(e)}


@app.post("/compute-factors")
def compute_factors_endpoint(payload: FactorsRequest) -> list[dict]:
    """Compute financial factors for the provided dataset.

    Parameters
    ----------
    payload : FactorsRequest
        Request body containing a list of dictionaries with price and
        fundamental fields.
    """
    try:
        df = pd.DataFrame(payload.data)
        result_df = compute_factors(df)
        return result_df.to_dict(orient="records")
    except Exception as e:
        logger.error(f"Error computing factors: {e}")
        raise HTTPException(status_code=500, detail="Factor computation failed")


@app.get("/", response_class=HTMLResponse)
async def root():
    return "<h2>Welcome to Equity Alpha Engine API!</h2><p>Visit <a href='/docs'>/docs</a> for the interactive API documentation.</p>"


def _query_stocks(order_by: str, min_mktcap: int, top_n: int, company: str = None, sector: str = None):
    """Query stocks with improved error handling and connection management.
    Selects only the latest data per ticker.
    """
    base_query = """
        SELECT
            f."Ticker",
            f."CompanyName",
            f."sector",
            CASE WHEN f."Open" IS NULL OR f."Open" != f."Open" THEN 0 ELSE f."Open" END as "Open",
            CASE WHEN f."High" IS NULL OR f."High" != f."High" THEN 0 ELSE f."High" END as "High",
            CASE WHEN f."Low" IS NULL OR f."Low" != f."Low" THEN 0 ELSE f."Low" END as "Low",
            CASE WHEN f."close_price" IS NULL OR f."close_price" != f."close_price" THEN 0 ELSE f."close_price" END as "Close",
            CASE WHEN f."Adj Close" IS NULL OR f."Adj Close" != f."Adj Close" THEN 0 ELSE f."Adj Close" END as "Adj Close",
            CASE WHEN f."Volume" IS NULL OR f."Volume" != f."Volume" THEN 0 ELSE f."Volume" END as "Volume",
            CASE WHEN f."marketCap" IS NULL OR f."marketCap" != f."marketCap" THEN 0 ELSE f."marketCap" END as "marketCap",
            CASE WHEN f."beta" IS NULL OR f."beta" != f."beta" THEN 0 ELSE f."beta" END as "beta",
            CASE WHEN f."dividendYield" IS NULL OR f."dividendYield" != f."dividendYield" THEN 0 ELSE f."dividendYield" END as "dividendYield",
            CASE WHEN f."returnOnEquity" IS NULL OR f."returnOnEquity" != f."returnOnEquity" THEN 0 ELSE f."returnOnEquity" END as "returnOnEquity",
            CASE WHEN f."grossMargins" IS NULL OR f."grossMargins" != f."grossMargins" THEN 0 ELSE f."grossMargins" END as "grossMargins",
            CASE WHEN f."operatingMargins" IS NULL OR f."operatingMargins" != f."operatingMargins" THEN 0 ELSE f."operatingMargins" END as "operatingMargins",
            CASE WHEN f."profitMargins" IS NULL OR f."profitMargins" != f."profitMargins" THEN 0 ELSE f."profitMargins" END as "profitMargins",
            CASE WHEN f."priceToBook" IS NULL OR f."priceToBook" != f."priceToBook" THEN 0 ELSE f."priceToBook" END as "priceToBook",
            CASE WHEN f."trailingPE" IS NULL OR f."trailingPE" != f."trailingPE" THEN 0 ELSE f."trailingPE" END as "trailingPE",
            CASE WHEN f."forwardPE" IS NULL OR f."forwardPE" != f."forwardPE" THEN 0 ELSE f."forwardPE" END as "forwardPE",
            CASE WHEN f."priceToSalesTrailing12Months" IS NULL OR f."priceToSalesTrailing12Months" != f."priceToSalesTrailing12Months" THEN 0 ELSE f."priceToSalesTrailing12Months" END as "priceToSalesTrailing12Months",
            CASE WHEN f."debtToEquity" IS NULL OR f."debtToEquity" != f."debtToEquity" THEN 0 ELSE f."debtToEquity" END as "debtToEquity",
            CASE WHEN f."currentRatio" IS NULL OR f."currentRatio" != f."currentRatio" THEN 0 ELSE f."currentRatio" END as "currentRatio",
            CASE WHEN f."quickRatio" IS NULL OR f."quickRatio" != f."quickRatio" THEN 0 ELSE f."quickRatio" END as "quickRatio",
            CASE WHEN f."averageVolume" IS NULL OR f."averageVolume" != f."averageVolume" THEN 0 ELSE f."averageVolume" END as "averageVolume",
            CASE WHEN f."earnings_yield" IS NULL OR f."earnings_yield" != f."earnings_yield" THEN 0 ELSE f."earnings_yield" END as "earnings_yield",
            CASE WHEN f."return_12m" IS NULL OR f."return_12m" != f."return_12m" THEN 0 ELSE f."return_12m" END as "return_12m",
            CASE WHEN f."return_3m" IS NULL OR f."return_3m" != f."return_3m" THEN 0 ELSE f."return_3m" END as "return_3m",
            CASE WHEN f."vol_21d" IS NULL OR f."vol_21d" != f."vol_21d" THEN 0 ELSE f."vol_21d" END as "vol_21d",
            CASE WHEN f."vol_252d" IS NULL OR f."vol_252d" != f."vol_252d" THEN 0 ELSE f."vol_252d" END as "vol_252d",
            CASE WHEN f."factor_composite" IS NULL OR f."factor_composite" != f."factor_composite" THEN 0 ELSE f."factor_composite" END as "factor_composite",
            CASE WHEN f."norm_quality_score" IS NULL OR f."norm_quality_score" != f."norm_quality_score" THEN 0 ELSE f."norm_quality_score" END as "norm_quality_score"
        FROM financial_tbl f
        INNER JOIN (
            SELECT "Ticker", MAX("Date") as max_date
            FROM financial_tbl
            GROUP BY "Ticker"
        ) m ON f."Ticker" = m."Ticker" AND f."Date" = m.max_date
        WHERE f."marketCap" >= :min_mktcap
    """

    if company:
        base_query += ' AND LOWER(f."CompanyName") LIKE LOWER(:company)'
    if sector:
        base_query += ' AND LOWER(f."sector") LIKE LOWER(:sector)'

    base_query += f" ORDER BY {order_by} LIMIT :top_n"

    params = {"min_mktcap": min_mktcap, "top_n": top_n}
    if company:
        params["company"] = f"%{company}%"
    if sector:
        params["sector"] = f"%{sector}%"

    query = text(base_query)
    return execute_query_with_retry(query, params)


def _query_combined_stocks(min_mktcap: int, top_n: int, company: str = None, sector: str = None):
    """Query combined stocks with specific criteria.
    Selects only the latest data per ticker.
    """
    base_query = """
        SELECT
            f."Ticker",
            f."CompanyName",
            f."sector",
            CASE WHEN f."Open" IS NULL OR f."Open" != f."Open" THEN 0 ELSE f."Open" END as "Open",
            CASE WHEN f."High" IS NULL OR f."High" != f."High" THEN 0 ELSE f."High" END as "High",
            CASE WHEN f."Low" IS NULL OR f."Low" != f."Low" THEN 0 ELSE f."Low" END as "Low",
            CASE WHEN f."close_price" IS NULL OR f."close_price" != f."close_price" THEN 0 ELSE f."close_price" END as "Close",
            CASE WHEN f."Adj Close" IS NULL OR f."Adj Close" != f."Adj Close" THEN 0 ELSE f."Adj Close" END as "Adj Close",
            CASE WHEN f."Volume" IS NULL OR f."Volume" != f."Volume" THEN 0 ELSE f."Volume" END as "Volume",
            CASE WHEN f."marketCap" IS NULL OR f."marketCap" != f."marketCap" THEN 0 ELSE f."marketCap" END as "marketCap",
            CASE WHEN f."beta" IS NULL OR f."beta" != f."beta" THEN 0 ELSE f."beta" END as "beta",
            CASE WHEN f."dividendYield" IS NULL OR f."dividendYield" != f."dividendYield" THEN 0 ELSE f."dividendYield" END as "dividendYield",
            CASE WHEN f."returnOnEquity" IS NULL OR f."returnOnEquity" != f."returnOnEquity" THEN 0 ELSE f."returnOnEquity" END as "returnOnEquity",
            CASE WHEN f."grossMargins" IS NULL OR f."grossMargins" != f."grossMargins" THEN 0 ELSE f."grossMargins" END as "grossMargins",
            CASE WHEN f."operatingMargins" IS NULL OR f."operatingMargins" != f."operatingMargins" THEN 0 ELSE f."operatingMargins" END as "operatingMargins",
            CASE WHEN f."profitMargins" IS NULL OR f."profitMargins" != f."profitMargins" THEN 0 ELSE f."profitMargins" END as "profitMargins",
            CASE WHEN f."priceToBook" IS NULL OR f."priceToBook" != f."priceToBook" THEN 0 ELSE f."priceToBook" END as "priceToBook",
            CASE WHEN f."trailingPE" IS NULL OR f."trailingPE" != f."trailingPE" THEN 0 ELSE f."trailingPE" END as "trailingPE",
            CASE WHEN f."forwardPE" IS NULL OR f."forwardPE" != f."forwardPE" THEN 0 ELSE f."forwardPE" END as "forwardPE",
            CASE WHEN f."priceToSalesTrailing12Months" IS NULL OR f."priceToSalesTrailing12Months" != f."priceToSalesTrailing12Months" THEN 0 ELSE f."priceToSalesTrailing12Months" END as "priceToSalesTrailing12Months",
            CASE WHEN f."debtToEquity" IS NULL OR f."debtToEquity" != f."debtToEquity" THEN 0 ELSE f."debtToEquity" END as "debtToEquity",
            CASE WHEN f."currentRatio" IS NULL OR f."currentRatio" != f."currentRatio" THEN 0 ELSE f."currentRatio" END as "currentRatio",
            CASE WHEN f."quickRatio" IS NULL OR f."quickRatio" != f."quickRatio" THEN 0 ELSE f."quickRatio" END as "quickRatio",
            CASE WHEN f."averageVolume" IS NULL OR f."averageVolume" != f."averageVolume" THEN 0 ELSE f."averageVolume" END as "averageVolume",
            CASE WHEN f."earnings_yield" IS NULL OR f."earnings_yield" != f."earnings_yield" THEN 0 ELSE f."earnings_yield" END as "earnings_yield",
            CASE WHEN f."return_12m" IS NULL OR f."return_12m" != f."return_12m" THEN 0 ELSE f."return_12m" END as "return_12m",
            CASE WHEN f."return_3m" IS NULL OR f."return_3m" != f."return_3m" THEN 0 ELSE f."return_3m" END as "return_3m",
            CASE WHEN f."vol_21d" IS NULL OR f."vol_21d" != f."vol_21d" THEN 0 ELSE f."vol_21d" END as "vol_21d",
            CASE WHEN f."vol_252d" IS NULL OR f."vol_252d" != f."vol_252d" THEN 0 ELSE f."vol_252d" END as "vol_252d",
            CASE WHEN f."factor_composite" IS NULL OR f."factor_composite" != f."factor_composite" THEN 0 ELSE f."factor_composite" END as "factor_composite",
            CASE WHEN f."norm_quality_score" IS NULL OR f."norm_quality_score" != f."norm_quality_score" THEN 0 ELSE f."norm_quality_score" END as "norm_quality_score"
        FROM financial_tbl f
        INNER JOIN (
            SELECT "Ticker", MAX("Date") as max_date
            FROM financial_tbl
            GROUP BY "Ticker"
        ) m ON f."Ticker" = m."Ticker" AND f."Date" = m.max_date
        WHERE f."marketCap" >= :min_mktcap
        AND f.factor_composite > 0.5
        AND f.norm_quality_score > 0.5
        AND f.return_12m > 0.1
    """

    if company:
        base_query += ' AND LOWER(f."CompanyName") LIKE LOWER(:company)'
    if sector:
        base_query += ' AND LOWER(f."sector") LIKE LOWER(:sector)'

    base_query += " ORDER BY f.factor_composite DESC, f.norm_quality_score DESC, f.return_12m DESC LIMIT :top_n"

    params = {"min_mktcap": min_mktcap, "top_n": top_n}
    if company:
        params["company"] = f"%{company}%"
    if sector:
        params["sector"] = f"%{sector}%"

    query = text(base_query)
    return execute_query_with_retry(query, params)


@app.get("/get_undervalued_stocks")
def get_undervalued_stocks(min_mktcap: int = 0, top_n: int = 10, company: str = None, sector: str = None):
    key = f"undervalued_{min_mktcap}_{top_n}_{company or ''}_{sector or ''}"
    return get_cached_or_compute(key, lambda: _query_stocks("factor_composite ASC", min_mktcap, top_n, company, sector))


@app.get("/get_overvalued_stocks")
def get_overvalued_stocks(min_mktcap: int = 0, top_n: int = 10, company: str = None, sector: str = None):
    key = f"overvalued_{min_mktcap}_{top_n}_{company or ''}_{sector or ''}"
    return get_cached_or_compute(key, lambda: _query_stocks("factor_composite DESC", min_mktcap, top_n, company, sector))


@app.get("/get_high_quality_stocks")
def get_high_quality_stocks(min_mktcap: int = 0, top_n: int = 10, company: str = None, sector: str = None):
    key = f"high_quality_{min_mktcap}_{top_n}_{company or ''}_{sector or ''}"
    return get_cached_or_compute(key, lambda: _query_stocks("norm_quality_score DESC", min_mktcap, top_n, company, sector))


@app.get("/get_high_earnings_yield_stocks")
def get_high_earnings_yield_stocks(min_mktcap: int = 0, top_n: int = 10, company: str = None, sector: str = None):
    key = f"high_earnings_yield_{min_mktcap}_{top_n}_{company or ''}_{sector or ''}"
    return get_cached_or_compute(key, lambda: _query_stocks("earnings_yield DESC", min_mktcap, top_n, company, sector))


@app.get("/get_top_market_cap_stocks")
def get_top_market_cap_stocks(min_mktcap: int = 0, top_n: int = 10, company: str = None, sector: str = None):
    key = f"top_market_cap_{min_mktcap}_{top_n}_{company or ''}_{sector or ''}"
    return get_cached_or_compute(key, lambda: _query_stocks('"marketCap" DESC', min_mktcap, top_n, company, sector))


@app.get("/get_low_beta_stocks")
def get_low_beta_stocks(min_mktcap: int = 0, top_n: int = 10, company: str = None, sector: str = None):
    key = f"low_beta_{min_mktcap}_{top_n}_{company or ''}_{sector or ''}"
    return get_cached_or_compute(key, lambda: _query_stocks("beta ASC", min_mktcap, top_n, company, sector))


@app.get("/get_high_dividend_yield_stocks")
def get_high_dividend_yield_stocks(min_mktcap: int = 0, top_n: int = 10, company: str = None, sector: str = None):
    key = f"high_dividend_yield_{min_mktcap}_{top_n}_{company or ''}_{sector or ''}"
    return get_cached_or_compute(key, lambda: _query_stocks('"dividendYield" DESC', min_mktcap, top_n, company, sector))


@app.get("/get_high_momentum_stocks")
def get_high_momentum_stocks(min_mktcap: int = 0, top_n: int = 10, company: str = None, sector: str = None):
    key = f"high_momentum_{min_mktcap}_{top_n}_{company or ''}_{sector or ''}"
    return get_cached_or_compute(key, lambda: _query_stocks("return_12m DESC", min_mktcap, top_n, company, sector))


@app.get("/get_low_volatility_stocks")
def get_low_volatility_stocks(min_mktcap: int = 0, top_n: int = 10, company: str = None, sector: str = None):
    key = f"low_volatility_{min_mktcap}_{top_n}_{company or ''}_{sector or ''}"
    return get_cached_or_compute(key, lambda: _query_stocks("vol_21d ASC", min_mktcap, top_n, company, sector))


@app.get("/get_top_short_term_momentum_stocks")
def get_top_short_term_momentum_stocks(min_mktcap: int = 0, top_n: int = 10, company: str = None, sector: str = None):
    key = f"top_short_term_momentum_{min_mktcap}_{top_n}_{company or ''}_{sector or ''}"
    return get_cached_or_compute(key, lambda: _query_stocks("return_3m DESC", min_mktcap, top_n, company, sector))


@app.get("/get_high_dividend_low_beta_stocks")
def get_high_dividend_low_beta_stocks(min_mktcap: int = 0, top_n: int = 10, company: str = None, sector: str = None):
    key = f"high_dividend_low_beta_{min_mktcap}_{top_n}_{company or ''}_{sector or ''}"
    return get_cached_or_compute(key, lambda: _query_stocks('"dividendYield" DESC, beta ASC', min_mktcap, top_n, company, sector))


@app.get("/get_top_factor_composite_stocks")
def get_top_factor_composite_stocks(min_mktcap: int = 0, top_n: int = 10, company: str = None, sector: str = None):
    key = f"top_factor_composite_{min_mktcap}_{top_n}_{company or ''}_{sector or ''}"
    return get_cached_or_compute(key, lambda: _query_stocks("factor_composite DESC", min_mktcap, top_n, company, sector))


@app.get("/get_high_risk_stocks")
def get_high_risk_stocks(min_mktcap: int = 0, top_n: int = 10, company: str = None, sector: str = None):
    key = f"high_risk_{min_mktcap}_{top_n}_{company or ''}_{sector or ''}"
    return get_cached_or_compute(key, lambda: _query_stocks("vol_252d DESC", min_mktcap, top_n, company, sector))


@app.get("/get_top_combined_screen_limited")
def get_top_combined_screen_limited(min_mktcap: int = 0, top_n: int = 10, company: str = None, sector: str = None):
    key = f"top_combined_screen_limited_{min_mktcap}_{top_n}_{company or ''}_{sector or ''}"
    return get_cached_or_compute(key, lambda: _query_combined_stocks(min_mktcap, top_n, company, sector))


def _query_macro_data():
    """Query macroeconomic data from macro_data_tbl."""
    try:
        query = text(
            """
            SELECT
                "Date",
                COALESCE("GDP_Growth_YoY", 0) as "GDP_Growth_YoY",
                COALESCE("Inflation_YoY", 0) as "Inflation_YoY"
            FROM macro_data_tbl
            ORDER BY "Date" ASC
            """
        )
        return execute_query_with_retry(query)
    except Exception as e:
        logger.warning(f"Macro data table not available: {e}")
        return []


@app.get("/get_macro_data")
def get_macro_data():
    """Get macroeconomic data (GDP growth and inflation)."""
    key = "macro_data"
    return get_cached_or_compute(key, lambda: _query_macro_data())
