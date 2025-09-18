from contextlib import contextmanager
from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Any
import time
import logging
import urllib.parse

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
            logger.error(f"Unexpected error during query execution: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)[:100]}")
    
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
    # Input validation
    if top_n <= 0 or top_n > 100:
        raise HTTPException(status_code=400, detail="top_n must be between 1 and 100")
    if min_mktcap < 0:
        raise HTTPException(status_code=400, detail="min_mktcap cannot be negative")

    # Validate sector parameter against available sectors
    if sector:
        sector_clean = sector.replace("'", "''").strip()
        sector_clean = urllib.parse.unquote(sector_clean)
        logger.debug(f"Sector parameter: {sector}, cleaned and decoded: {sector_clean}")

        # Get list of available sectors
        available_sectors_query = text("""
            SELECT DISTINCT TRIM("sector") as sector
            FROM financial_tbl
            WHERE TRIM("sector") IS NOT NULL AND TRIM("sector") != ''
        """)
        try:
            available_sectors_result = execute_query_with_retry(available_sectors_query)
            available_sectors = [row["sector"] for row in available_sectors_result]

            # Check if provided sector exists (case-insensitive)
            sector_found = any(sector_clean.lower() == avail_sector.lower() for avail_sector in available_sectors)
            if not sector_found:
                raise HTTPException(
                    status_code=400,
                    detail=f"Sector '{sector_clean}' not found. Available sectors: {', '.join(sorted(available_sectors))}"
                )
        except Exception as e:
            logger.warning(f"Failed to validate sector: {e}")
            # Continue without validation if database query fails

    base_query = """
        SELECT
            f."Ticker",
            f."CompanyName",
            f."sector",
            f."Open",
            f."High",
            f."Low",
            f."close_price" as "Close",
            f."Adj Close",
            f."Volume",
            f."marketCap",
            f."beta",
            f."dividendYield",
            f."returnOnEquity",
            f."grossMargins",
            f."operatingMargins",
            f."profitMargins",
            f."priceToBook",
            f."trailingPE",
            f."forwardPE",
            f."priceToSalesTrailing12Months",
            f."debtToEquity",
            f."currentRatio",
            f."quickRatio",
            f."averageVolume",
            f."earnings_yield",
            f."return_12m",
            f."return_3m",
            f."vol_21d",
            f."vol_252d",
            f."factor_composite",
            f."norm_quality_score"
        FROM financial_tbl f
        INNER JOIN (
            SELECT "Ticker", MAX("Date") as max_date
            FROM financial_tbl
            GROUP BY "Ticker"
        ) m ON f."Ticker" = m."Ticker" AND f."Date" = m.max_date
        WHERE f."marketCap" >= :min_mktcap
    """

    if company:
        # Sanitize company input to prevent SQL injection
        company_clean = company.replace("'", "''").strip()
        company_clean = urllib.parse.unquote(company_clean)
        if len(company_clean) > 100:
            raise HTTPException(status_code=400, detail="Company name too long")
        base_query += ' AND LOWER(f."CompanyName") LIKE LOWER(:company)'
    if sector:
        # Sanitize sector input
        sector_clean = sector.replace("'", "''").strip()
        sector_clean = urllib.parse.unquote(sector_clean)
        logger.debug(f"Sector parameter: {sector}, cleaned and decoded: {sector_clean}")
        if len(sector_clean) > 100:
            raise HTTPException(status_code=400, detail="Sector name too long")
        if '%' in sector_clean:
            base_query += ' AND LOWER(TRIM(f."sector")) LIKE LOWER(TRIM(:sector))'
        else:
            base_query += ' AND LOWER(TRIM(f."sector")) = LOWER(TRIM(:sector))'

    base_query += f" ORDER BY {order_by} LIMIT :top_n"

    params = {"min_mktcap": min_mktcap, "top_n": top_n}
    if company:
        params["company"] = f"%{company_clean}%"
    if sector:
        params["sector"] = sector_clean

    query = text(base_query)
    result = execute_query_with_retry(query, params)
    # Handle NaN values that are not JSON compliant
    for row in result:
        for key, value in row.items():
            if isinstance(value, float) and (pd.isna(value) or value != value):  # Check for NaN
                row[key] = None
    return result


def _query_combined_stocks(min_mktcap: int, top_n: int, company: str = None, sector: str = None):
    """Query combined stocks with specific criteria.
    Selects only the latest data per ticker.
    """
    # Input validation
    if top_n <= 0 or top_n > 100:
        raise HTTPException(status_code=400, detail="top_n must be between 1 and 100")
    if min_mktcap < 0:
        raise HTTPException(status_code=400, detail="min_mktcap cannot be negative")

    # Validate sector parameter against available sectors
    if sector:
        sector_clean = sector.replace("'", "''").strip()
        sector_clean = urllib.parse.unquote(sector_clean)
        logger.debug(f"Sector parameter: {sector}, cleaned and decoded: {sector_clean}")

        # Get list of available sectors
        available_sectors_query = text("""
            SELECT DISTINCT TRIM("sector") as sector
            FROM financial_tbl
            WHERE TRIM("sector") IS NOT NULL AND TRIM("sector") != ''
        """)
        try:
            available_sectors_result = execute_query_with_retry(available_sectors_query)
            available_sectors = [row["sector"] for row in available_sectors_result]

            # Check if provided sector exists (case-insensitive)
            sector_found = any(sector_clean.lower() == avail_sector.lower() for avail_sector in available_sectors)
            if not sector_found:
                raise HTTPException(
                    status_code=400,
                    detail=f"Sector '{sector_clean}' not found. Available sectors: {', '.join(sorted(available_sectors))}"
                )
        except Exception as e:
            logger.warning(f"Failed to validate sector: {e}")
            # Continue without validation if database query fails

    base_query = """
        SELECT
            f."Ticker",
            f."CompanyName",
            f."sector",
            f."Open",
            f."High",
            f."Low",
            f."close_price" as "Close",
            f."Adj Close",
            f."Volume",
            f."marketCap",
            f."beta",
            f."dividendYield",
            f."returnOnEquity",
            f."grossMargins",
            f."operatingMargins",
            f."profitMargins",
            f."priceToBook",
            f."trailingPE",
            f."forwardPE",
            f."priceToSalesTrailing12Months",
            f."debtToEquity",
            f."currentRatio",
            f."quickRatio",
            f."averageVolume",
            f."earnings_yield",
            f."return_12m",
            f."return_3m",
            f."vol_21d",
            f."vol_252d",
            f."factor_composite",
            f."norm_quality_score"
        FROM financial_tbl f
        INNER JOIN (
            SELECT "Ticker", MAX("Date") as max_date
            FROM financial_tbl
            GROUP BY "Ticker"
        ) m ON f."Ticker" = m."Ticker" AND f."Date" = m.max_date
        WHERE f."marketCap" >= :min_mktcap
        AND f."factor_composite" > 0.5
        AND f."norm_quality_score" > 0.5
        AND f."return_12m" > 0.1
    """

    if company:
        # Sanitize company input to prevent SQL injection
        company_clean = company.replace("'", "''").strip()
        company_clean = urllib.parse.unquote(company_clean)
        if len(company_clean) > 100:
            raise HTTPException(status_code=400, detail="Company name too long")
        base_query += ' AND LOWER(f."CompanyName") LIKE LOWER(:company)'
    if sector:
        # Sanitize sector input
        sector_clean = sector.replace("'", "''").strip()
        sector_clean = urllib.parse.unquote(sector_clean)
        logger.debug(f"Sector parameter: {sector}, cleaned and decoded: {sector_clean}")
        if len(sector_clean) > 100:
            raise HTTPException(status_code=400, detail="Sector name too long")
        if '%' in sector_clean:
            base_query += ' AND LOWER(TRIM(f."sector")) LIKE LOWER(TRIM(:sector))'
        else:
            base_query += ' AND LOWER(TRIM(f."sector")) = LOWER(TRIM(:sector))'

    base_query += " ORDER BY f.\"factor_composite\" DESC, f.\"norm_quality_score\" DESC, f.\"return_12m\" DESC LIMIT :top_n"

    params = {"min_mktcap": min_mktcap, "top_n": top_n}
    if company:
        params["company"] = f"%{company_clean}%"
    if sector:
        params["sector"] = sector_clean

    query = text(base_query)
    result = execute_query_with_retry(query, params)
    # Handle NaN values that are not JSON compliant
    for row in result:
        for key, value in row.items():
            if isinstance(value, float) and (pd.isna(value) or value != value):  # Check for NaN
                row[key] = None
    return result


@app.get("/get_undervalued_stocks")
def get_undervalued_stocks(min_mktcap: int = 0, top_n: int = 10, company: str = None, sector: str = None):
    key = f"undervalued_{min_mktcap}_{top_n}_{company or ''}_{sector or ''}"
    return get_cached_or_compute(key, lambda: _query_stocks('"factor_composite" ASC', min_mktcap, top_n, company, sector))


@app.get("/get_overvalued_stocks")
def get_overvalued_stocks(min_mktcap: int = 0, top_n: int = 10, company: str = None, sector: str = None):
    key = f"overvalued_{min_mktcap}_{top_n}_{company or ''}_{sector or ''}"
    return get_cached_or_compute(key, lambda: _query_stocks('"factor_composite" DESC', min_mktcap, top_n, company, sector))


@app.get("/get_high_quality_stocks")
def get_high_quality_stocks(min_mktcap: int = 0, top_n: int = 10, company: str = None, sector: str = None):
    key = f"high_quality_{min_mktcap}_{top_n}_{company or ''}_{sector or ''}"
    return get_cached_or_compute(key, lambda: _query_stocks('"norm_quality_score" DESC', min_mktcap, top_n, company, sector))


@app.get("/get_high_earnings_yield_stocks")
def get_high_earnings_yield_stocks(min_mktcap: int = 0, top_n: int = 10, company: str = None, sector: str = None):
    key = f"high_earnings_yield_{min_mktcap}_{top_n}_{company or ''}_{sector or ''}"
    return get_cached_or_compute(key, lambda: _query_stocks('"earnings_yield" DESC', min_mktcap, top_n, company, sector))


@app.get("/get_top_market_cap_stocks")
def get_top_market_cap_stocks(min_mktcap: int = 0, top_n: int = 10, company: str = None, sector: str = None):
    key = f"top_market_cap_{min_mktcap}_{top_n}_{company or ''}_{sector or ''}"
    return get_cached_or_compute(key, lambda: _query_stocks('"marketCap" DESC', min_mktcap, top_n, company, sector))


@app.get("/get_low_beta_stocks")
def get_low_beta_stocks(min_mktcap: int = 0, top_n: int = 10, company: str = None, sector: str = None):
    key = f"low_beta_{min_mktcap}_{top_n}_{company or ''}_{sector or ''}"
    return get_cached_or_compute(key, lambda: _query_stocks('"beta" ASC', min_mktcap, top_n, company, sector))


@app.get("/get_high_dividend_yield_stocks")
def get_high_dividend_yield_stocks(min_mktcap: int = 0, top_n: int = 10, company: str = None, sector: str = None):
    key = f"high_dividend_yield_{min_mktcap}_{top_n}_{company or ''}_{sector or ''}"
    return get_cached_or_compute(key, lambda: _query_stocks('"dividendYield" DESC', min_mktcap, top_n, company, sector))


@app.get("/get_high_momentum_stocks")
def get_high_momentum_stocks(min_mktcap: int = 0, top_n: int = 10, company: str = None, sector: str = None):
    key = f"high_momentum_{min_mktcap}_{top_n}_{company or ''}_{sector or ''}"
    return get_cached_or_compute(key, lambda: _query_stocks('"return_12m" DESC', min_mktcap, top_n, company, sector))


@app.get("/get_low_volatility_stocks")
def get_low_volatility_stocks(min_mktcap: int = 0, top_n: int = 10, company: str = None, sector: str = None):
    key = f"low_volatility_{min_mktcap}_{top_n}_{company or ''}_{sector or ''}"
    return get_cached_or_compute(key, lambda: _query_stocks('"vol_21d" ASC', min_mktcap, top_n, company, sector))


@app.get("/get_top_short_term_momentum_stocks")
def get_top_short_term_momentum_stocks(min_mktcap: int = 0, top_n: int = 10, company: str = None, sector: str = None):
    key = f"top_short_term_momentum_{min_mktcap}_{top_n}_{company or ''}_{sector or ''}"
    return get_cached_or_compute(key, lambda: _query_stocks('"return_3m" DESC', min_mktcap, top_n, company, sector))


@app.get("/get_high_dividend_low_beta_stocks")
def get_high_dividend_low_beta_stocks(min_mktcap: int = 0, top_n: int = 10, company: str = None, sector: str = None):
    key = f"high_dividend_low_beta_{min_mktcap}_{top_n}_{company or ''}_{sector or ''}"
    return get_cached_or_compute(key, lambda: _query_stocks('"dividendYield" DESC, "beta" ASC', min_mktcap, top_n, company, sector))


@app.get("/get_top_factor_composite_stocks")
def get_top_factor_composite_stocks(min_mktcap: int = 0, top_n: int = 10, company: str = None, sector: str = None):
    key = f"top_factor_composite_{min_mktcap}_{top_n}_{company or ''}_{sector or ''}"
    return get_cached_or_compute(key, lambda: _query_stocks('"factor_composite" DESC', min_mktcap, top_n, company, sector))


@app.get("/get_high_risk_stocks")
def get_high_risk_stocks(min_mktcap: int = 0, top_n: int = 10, company: str = None, sector: str = None):
    key = f"high_risk_{min_mktcap}_{top_n}_{company or ''}_{sector or ''}"
    return get_cached_or_compute(key, lambda: _query_stocks('"vol_252d" DESC', min_mktcap, top_n, company, sector))


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
                "GDP_Growth_YoY",
                "Inflation_YoY"
            FROM macro_data_tbl
            ORDER BY "Date" ASC
            """
        )
        result = execute_query_with_retry(query)
        # Handle NaN values that are not JSON compliant
        for row in result:
            for key, value in row.items():
                if isinstance(value, float) and (pd.isna(value) or value != value):  # Check for NaN
                    row[key] = None
        return result
    except Exception as e:
        logger.warning(f"Macro data table not available: {e}")
        return []


@app.get("/get_macro_data")
def get_macro_data():
    """Get macroeconomic data (GDP growth and inflation)."""
    key = "macro_data"
    return get_cached_or_compute(key, lambda: _query_macro_data())


def _query_unique_sectors():
    """Query unique sectors from financial_tbl."""
    try:
        query = text(
            """
            SELECT DISTINCT TRIM("sector") as sector
            FROM financial_tbl
            WHERE TRIM("sector") IS NOT NULL AND TRIM("sector") != ''
            ORDER BY TRIM("sector") ASC
            """
        )
        result = execute_query_with_retry(query)
        return [row["sector"] for row in result]
    except Exception as e:
        logger.warning(f"Failed to query unique sectors: {e}")
        return []


@app.get("/get_unique_sectors")
def get_unique_sectors():
    """Get list of unique sectors."""
    key = "unique_sectors"
    return get_cached_or_compute(key, lambda: _query_unique_sectors())
