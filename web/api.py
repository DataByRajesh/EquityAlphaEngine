from contextlib import contextmanager
from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Any

import pandas as pd
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import text

from data_pipeline.compute_factors import compute_factors
from data_pipeline.db_utils import DBHelper
from data_pipeline.utils import get_secret

app = FastAPI()

# In-memory cache for API responses
CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_LOCK = Lock()
CACHE_TTL = timedelta(minutes=10)  # Cache for 10 minutes


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


class FactorsRequest(BaseModel):
    data: list[dict]


@app.get("/health")
def health() -> dict:
    """Simple health check endpoint."""
    return {"status": "ok"}


@app.post("/compute-factors")
def compute_factors_endpoint(payload: FactorsRequest) -> list[dict]:
    """Compute financial factors for the provided dataset.

    Parameters
    ----------
    payload : FactorsRequest
        Request body containing a list of dictionaries with price and
        fundamental fields.
    """
    df = pd.DataFrame(payload.data)
    result_df = compute_factors(df)
    return result_df.to_dict(orient="records")


@app.get("/", response_class=HTMLResponse)
async def root():
    return "<h2>Welcome to Equity Alpha Engine API!</h2><p>Visit <a href='/docs'>/docs</a> for the interactive API documentation.</p>"


@contextmanager
def get_db_context():
    """Context manager for proper database resource management."""
    db = DBHelper(get_secret("DATABASE_URL"))
    try:
        yield db
    finally:
        db.close()


def get_db():
    return DBHelper(get_secret("DATABASE_URL"))


def _query_stocks(order_by: str, min_mktcap: int, top_n: int):
    with get_db_context() as db:
        query = text(
            f"""
            SELECT * FROM financial_tbl
            WHERE marketCap >= :min_mktcap
            ORDER BY {order_by}
            LIMIT :top_n
        """
        )
        df = pd.read_sql(query, db.engine, params={
                         "min_mktcap": min_mktcap, "top_n": top_n})
        return df.to_dict(orient="records")


@app.get("/get_undervalued_stocks")
def get_undervalued_stocks(min_mktcap: int = 0, top_n: int = 10):
    key = f"undervalued_{min_mktcap}_{top_n}"
    return get_cached_or_compute(key, lambda: _query_stocks("factor_composite ASC", min_mktcap, top_n))


@app.get("/get_overvalued_stocks")
def get_overvalued_stocks(min_mktcap: int = 0, top_n: int = 10):
<<<<<<< HEAD
    key = f"overvalued_{min_mktcap}_{top_n}"
    return get_cached_or_compute(key, lambda: _query_stocks("factor_composite DESC", min_mktcap, top_n))
=======
    with get_db_context() as db:
        query = text(
            """
            SELECT * FROM financial_tbl
            WHERE marketCap >= :min_mktcap
            ORDER BY factor_composite DESC
            LIMIT :top_n
        """
        )
        df = pd.read_sql(query, db.engine, params={
                         "min_mktcap": min_mktcap, "top_n": top_n})
        return df.to_dict(orient="records")
>>>>>>> cf3849efaa1e4d896d51a3e39da94a6b5f886e93


@app.get("/get_high_quality_stocks")
def get_high_quality_stocks(min_mktcap: int = 0, top_n: int = 10):
<<<<<<< HEAD
    key = f"high_quality_{min_mktcap}_{top_n}"
    return get_cached_or_compute(key, lambda: _query_stocks("norm_quality_score DESC", min_mktcap, top_n))
=======
    with get_db_context() as db:
        query = text(
            """
            SELECT * FROM financial_tbl
            WHERE marketCap >= :min_mktcap
            ORDER BY norm_quality_score DESC
            LIMIT :top_n
        """
        )
        df = pd.read_sql(query, db.engine, params={
                         "min_mktcap": min_mktcap, "top_n": top_n})
        return df.to_dict(orient="records")
>>>>>>> cf3849efaa1e4d896d51a3e39da94a6b5f886e93


@app.get("/get_high_earnings_yield_stocks")
def get_high_earnings_yield_stocks(min_mktcap: int = 0, top_n: int = 10):
<<<<<<< HEAD
    key = f"high_earnings_yield_{min_mktcap}_{top_n}"
    return get_cached_or_compute(key, lambda: _query_stocks("earnings_yield DESC", min_mktcap, top_n))
=======
    with get_db_context() as db:
        query = text(
            """
            SELECT * FROM financial_tbl
            WHERE marketCap >= :min_mktcap
            ORDER BY earnings_yield DESC
            LIMIT :top_n
        """
        )
        df = pd.read_sql(query, db.engine, params={
                         "min_mktcap": min_mktcap, "top_n": top_n})
        return df.to_dict(orient="records")
>>>>>>> cf3849efaa1e4d896d51a3e39da94a6b5f886e93


@app.get("/get_top_market_cap_stocks")
def get_top_market_cap_stocks(min_mktcap: int = 0, top_n: int = 10):
<<<<<<< HEAD
    key = f"top_market_cap_{min_mktcap}_{top_n}"
    return get_cached_or_compute(key, lambda: _query_stocks("marketCap DESC", min_mktcap, top_n))
=======
    with get_db_context() as db:
        query = text(
            """
            SELECT * FROM financial_tbl
            WHERE marketCap >= :min_mktcap
            ORDER BY marketCap DESC
            LIMIT :top_n
        """
        )
        df = pd.read_sql(query, db.engine, params={
                         "min_mktcap": min_mktcap, "top_n": top_n})
        return df.to_dict(orient="records")
>>>>>>> cf3849efaa1e4d896d51a3e39da94a6b5f886e93


@app.get("/get_low_beta_stocks")
def get_low_beta_stocks(min_mktcap: int = 0, top_n: int = 10):
<<<<<<< HEAD
    key = f"low_beta_{min_mktcap}_{top_n}"
    return get_cached_or_compute(key, lambda: _query_stocks("beta ASC", min_mktcap, top_n))
=======
    with get_db_context() as db:
        query = text(
            """
            SELECT * FROM financial_tbl
            WHERE marketCap >= :min_mktcap
            ORDER BY beta ASC
            LIMIT :top_n
        """
        )
        df = pd.read_sql(query, db.engine, params={
                         "min_mktcap": min_mktcap, "top_n": top_n})
        return df.to_dict(orient="records")
>>>>>>> cf3849efaa1e4d896d51a3e39da94a6b5f886e93


@app.get("/get_high_dividend_yield_stocks")
def get_high_dividend_yield_stocks(min_mktcap: int = 0, top_n: int = 10):
<<<<<<< HEAD
    key = f"high_dividend_yield_{min_mktcap}_{top_n}"
    return get_cached_or_compute(key, lambda: _query_stocks("dividendYield DESC", min_mktcap, top_n))
=======
    with get_db_context() as db:
        query = text(
            """
            SELECT * FROM financial_tbl
            WHERE marketCap >= :min_mktcap
            ORDER BY dividendYield DESC
            LIMIT :top_n
        """
        )
        df = pd.read_sql(query, db.engine, params={
                         "min_mktcap": min_mktcap, "top_n": top_n})
        return df.to_dict(orient="records")
>>>>>>> cf3849efaa1e4d896d51a3e39da94a6b5f886e93


@app.get("/get_high_momentum_stocks")
def get_high_momentum_stocks(min_mktcap: int = 0, top_n: int = 10):
<<<<<<< HEAD
    key = f"high_momentum_{min_mktcap}_{top_n}"
    return get_cached_or_compute(key, lambda: _query_stocks("return_12m DESC", min_mktcap, top_n))
=======
    with get_db_context() as db:
        query = text(
            """
            SELECT * FROM financial_tbl
            WHERE marketCap >= :min_mktcap
            ORDER BY return_12m DESC
            LIMIT :top_n
        """
        )
        df = pd.read_sql(query, db.engine, params={
                         "min_mktcap": min_mktcap, "top_n": top_n})
        return df.to_dict(orient="records")
>>>>>>> cf3849efaa1e4d896d51a3e39da94a6b5f886e93


@app.get("/get_low_volatility_stocks")
def get_low_volatility_stocks(min_mktcap: int = 0, top_n: int = 10):
<<<<<<< HEAD
    key = f"low_volatility_{min_mktcap}_{top_n}"
    return get_cached_or_compute(key, lambda: _query_stocks("volatility ASC", min_mktcap, top_n))
=======
    with get_db_context() as db:
        query = text(
            """
            SELECT * FROM financial_tbl
            WHERE marketCap >= :min_mktcap
            ORDER BY volatility ASC
            LIMIT :top_n
        """
        )
        df = pd.read_sql(query, db.engine, params={
                         "min_mktcap": min_mktcap, "top_n": top_n})
        return df.to_dict(orient="records")
>>>>>>> cf3849efaa1e4d896d51a3e39da94a6b5f886e93


@app.get("/get_top_short_term_momentum_stocks")
def get_top_short_term_momentum_stocks(min_mktcap: int = 0, top_n: int = 10):
<<<<<<< HEAD
    key = f"top_short_term_momentum_{min_mktcap}_{top_n}"
    return get_cached_or_compute(key, lambda: _query_stocks("return_3m DESC", min_mktcap, top_n))
=======
    with get_db_context() as db:
        query = text(
            """
            SELECT * FROM financial_tbl
            WHERE marketCap >= :min_mktcap
            ORDER BY return_3m DESC
            LIMIT :top_n
        """
        )
        df = pd.read_sql(query, db.engine, params={
                         "min_mktcap": min_mktcap, "top_n": top_n})
        return df.to_dict(orient="records")
>>>>>>> cf3849efaa1e4d896d51a3e39da94a6b5f886e93


@app.get("/get_high_dividend_low_beta_stocks")
def get_high_dividend_low_beta_stocks(min_mktcap: int = 0, top_n: int = 10):
<<<<<<< HEAD
    key = f"high_dividend_low_beta_{min_mktcap}_{top_n}"
    return get_cached_or_compute(key, lambda: _query_stocks("dividendYield DESC, beta ASC", min_mktcap, top_n))
=======
    with get_db_context() as db:
        query = text(
            """
            SELECT * FROM financial_tbl
            WHERE marketCap >= :min_mktcap
            ORDER BY dividendYield DESC, beta ASC
            LIMIT :top_n
        """
        )
        df = pd.read_sql(query, db.engine, params={
                         "min_mktcap": min_mktcap, "top_n": top_n})
        return df.to_dict(orient="records")
>>>>>>> cf3849efaa1e4d896d51a3e39da94a6b5f886e93


@app.get("/get_top_factor_composite_stocks")
def get_top_factor_composite_stocks(min_mktcap: int = 0, top_n: int = 10):
<<<<<<< HEAD
    key = f"top_factor_composite_{min_mktcap}_{top_n}"
    return get_cached_or_compute(key, lambda: _query_stocks("factor_composite DESC", min_mktcap, top_n))
=======
    with get_db_context() as db:
        query = text(
            """
            SELECT * FROM financial_tbl
            WHERE marketCap >= :min_mktcap
            ORDER BY factor_composite DESC
            LIMIT :top_n
        """
        )
        df = pd.read_sql(query, db.engine, params={
                         "min_mktcap": min_mktcap, "top_n": top_n})
        return df.to_dict(orient="records")
>>>>>>> cf3849efaa1e4d896d51a3e39da94a6b5f886e93


@app.get("/get_high_risk_stocks")
def get_high_risk_stocks(min_mktcap: int = 0, top_n: int = 10):
<<<<<<< HEAD
    key = f"high_risk_{min_mktcap}_{top_n}"
    return get_cached_or_compute(key, lambda: _query_stocks("risk_score DESC", min_mktcap, top_n))
=======
    with get_db_context() as db:
        query = text(
            """
            SELECT * FROM financial_tbl
            WHERE marketCap >= :min_mktcap
            ORDER BY risk_score DESC
            LIMIT :top_n
        """
        )
        df = pd.read_sql(query, db.engine, params={
                         "min_mktcap": min_mktcap, "top_n": top_n})
        return df.to_dict(orient="records")
>>>>>>> cf3849efaa1e4d896d51a3e39da94a6b5f886e93


@app.get("/get_top_combined_screen_limited")
def get_top_combined_screen_limited(min_mktcap: int = 0, top_n: int = 10):
    key = f"top_combined_screen_limited_{min_mktcap}_{top_n}"
    return get_cached_or_compute(key, lambda: _query_combined_stocks(min_mktcap, top_n))


def _query_combined_stocks(min_mktcap: int, top_n: int):
    with get_db_context() as db:
        query = text(
            """
            SELECT * FROM financial_tbl
            WHERE marketCap >= :min_mktcap
            AND factor_composite > 0.5
            AND norm_quality_score > 0.5
            AND return_12m > 0.1
            ORDER BY factor_composite DESC, norm_quality_score DESC, return_12m DESC
            LIMIT :top_n
        """
        )
        df = pd.read_sql(query, db.engine, params={
                         "min_mktcap": min_mktcap, "top_n": top_n})
        return df.to_dict(orient="records")
