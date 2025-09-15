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


def _query_stocks(order_by: str, min_mktcap: int, top_n: int):
    """Query stocks with improved error handling and connection management."""
    query = text(
        f"""
        SELECT * FROM financial_tbl
        WHERE "marketCap" >= :min_mktcap
        ORDER BY {order_by}
        LIMIT :top_n
        """
    )
    return execute_query_with_retry(query, {"min_mktcap": min_mktcap, "top_n": top_n})


def _query_combined_stocks(min_mktcap: int, top_n: int):
    """Query combined stocks with specific criteria."""
    query = text(
        """
        SELECT * FROM financial_tbl
        WHERE "marketCap" >= :min_mktcap
        AND factor_composite > 0.5
        AND norm_quality_score > 0.5
        AND return_12m > 0.1
        ORDER BY factor_composite DESC, norm_quality_score DESC, return_12m DESC
        LIMIT :top_n
        """
    )
    return execute_query_with_retry(query, {"min_mktcap": min_mktcap, "top_n": top_n})


@app.get("/get_undervalued_stocks")
def get_undervalued_stocks(min_mktcap: int = 0, top_n: int = 10):
    key = f"undervalued_{min_mktcap}_{top_n}"
    return get_cached_or_compute(key, lambda: _query_stocks("factor_composite ASC", min_mktcap, top_n))


@app.get("/get_overvalued_stocks")
def get_overvalued_stocks(min_mktcap: int = 0, top_n: int = 10):
    key = f"overvalued_{min_mktcap}_{top_n}"
    return get_cached_or_compute(key, lambda: _query_stocks("factor_composite DESC", min_mktcap, top_n))


@app.get("/get_high_quality_stocks")
def get_high_quality_stocks(min_mktcap: int = 0, top_n: int = 10):
    key = f"high_quality_{min_mktcap}_{top_n}"
    return get_cached_or_compute(key, lambda: _query_stocks("norm_quality_score DESC", min_mktcap, top_n))


@app.get("/get_high_earnings_yield_stocks")
def get_high_earnings_yield_stocks(min_mktcap: int = 0, top_n: int = 10):
    key = f"high_earnings_yield_{min_mktcap}_{top_n}"
    return get_cached_or_compute(key, lambda: _query_stocks("earnings_yield DESC", min_mktcap, top_n))


@app.get("/get_top_market_cap_stocks")
def get_top_market_cap_stocks(min_mktcap: int = 0, top_n: int = 10):
    key = f"top_market_cap_{min_mktcap}_{top_n}"
    return get_cached_or_compute(key, lambda: _query_stocks('"marketCap" DESC', min_mktcap, top_n))


@app.get("/get_low_beta_stocks")
def get_low_beta_stocks(min_mktcap: int = 0, top_n: int = 10):
    key = f"low_beta_{min_mktcap}_{top_n}"
    return get_cached_or_compute(key, lambda: _query_stocks("beta ASC", min_mktcap, top_n))


@app.get("/get_high_dividend_yield_stocks")
def get_high_dividend_yield_stocks(min_mktcap: int = 0, top_n: int = 10):
    key = f"high_dividend_yield_{min_mktcap}_{top_n}"
    return get_cached_or_compute(key, lambda: _query_stocks('"dividendYield" DESC', min_mktcap, top_n))


@app.get("/get_high_momentum_stocks")
def get_high_momentum_stocks(min_mktcap: int = 0, top_n: int = 10):
    key = f"high_momentum_{min_mktcap}_{top_n}"
    return get_cached_or_compute(key, lambda: _query_stocks("return_12m DESC", min_mktcap, top_n))


@app.get("/get_low_volatility_stocks")
def get_low_volatility_stocks(min_mktcap: int = 0, top_n: int = 10):
    key = f"low_volatility_{min_mktcap}_{top_n}"
    return get_cached_or_compute(key, lambda: _query_stocks("volatility ASC", min_mktcap, top_n))


@app.get("/get_top_short_term_momentum_stocks")
def get_top_short_term_momentum_stocks(min_mktcap: int = 0, top_n: int = 10):
    key = f"top_short_term_momentum_{min_mktcap}_{top_n}"
    return get_cached_or_compute(key, lambda: _query_stocks("return_3m DESC", min_mktcap, top_n))


@app.get("/get_high_dividend_low_beta_stocks")
def get_high_dividend_low_beta_stocks(min_mktcap: int = 0, top_n: int = 10):
    key = f"high_dividend_low_beta_{min_mktcap}_{top_n}"
    return get_cached_or_compute(key, lambda: _query_stocks('"dividendYield" DESC, beta ASC', min_mktcap, top_n))


@app.get("/get_top_factor_composite_stocks")
def get_top_factor_composite_stocks(min_mktcap: int = 0, top_n: int = 10):
    key = f"top_factor_composite_{min_mktcap}_{top_n}"
    return get_cached_or_compute(key, lambda: _query_stocks("factor_composite DESC", min_mktcap, top_n))


@app.get("/get_high_risk_stocks")
def get_high_risk_stocks(min_mktcap: int = 0, top_n: int = 10):
    key = f"high_risk_{min_mktcap}_{top_n}"
    return get_cached_or_compute(key, lambda: _query_stocks("risk_score DESC", min_mktcap, top_n))


@app.get("/get_top_combined_screen_limited")
def get_top_combined_screen_limited(min_mktcap: int = 0, top_n: int = 10):
    key = f"top_combined_screen_limited_{min_mktcap}_{top_n}"
    return get_cached_or_compute(key, lambda: _query_combined_stocks(min_mktcap, top_n))
