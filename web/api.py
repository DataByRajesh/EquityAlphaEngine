from fastapi import FastAPI, Query
from pydantic import BaseModel
import pandas as pd
from data_pipeline.compute_factors import compute_factors
from data_pipeline.db_utils import DBHelper
from data_pipeline.config import DATABASE_URL
from fastapi.responses import HTMLResponse

app = FastAPI()


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

def get_db():
    return DBHelper(DATABASE_URL)


@app.get("/get_undervalued_stocks")
def get_undervalued_stocks(min_mktcap: int = 0, top_n: int = 10):
    db = get_db()
    query = f"""
        SELECT * FROM financial_tbl
        WHERE marketCap >= {min_mktcap}
        ORDER BY factor_composite ASC
        LIMIT {top_n}
    """
    df = pd.read_sql(query, db.engine)
    db.close()
    return df.to_dict(orient="records")


@app.get("/get_overvalued_stocks")
def get_overvalued_stocks(min_mktcap: int = 0, top_n: int = 10):
    db = get_db()
    query = f"""
        SELECT * FROM financial_tbl
        WHERE marketCap >= {min_mktcap}
        ORDER BY factor_composite DESC
        LIMIT {top_n}
    """
    df = pd.read_sql(query, db.engine)
    db.close()
    return df.to_dict(orient="records")


@app.get("/get_high_quality_stocks")
def get_high_quality_stocks(min_mktcap: int = 0, top_n: int = 10):
    db = get_db()
    query = f"""
        SELECT * FROM financial_tbl
        WHERE marketCap >= {min_mktcap}
        ORDER BY norm_quality_score DESC
        LIMIT {top_n}
    """
    df = pd.read_sql(query, db.engine)
    db.close()
    return df.to_dict(orient="records")


@app.get("/get_high_earnings_yield_stocks")
def get_high_earnings_yield_stocks(min_mktcap: int = 0, top_n: int = 10):
    db = get_db()
    query = f"""
        SELECT * FROM financial_tbl
        WHERE marketCap >= {min_mktcap}
        ORDER BY earnings_yield DESC
        LIMIT {top_n}
    """
    df = pd.read_sql(query, db.engine)
    db.close()
    return df.to_dict(orient="records")


@app.get("/get_top_market_cap_stocks")
def get_top_market_cap_stocks(min_mktcap: int = 0, top_n: int = 10):
    db = get_db()
    query = f"""
        SELECT * FROM financial_tbl
        WHERE marketCap >= {min_mktcap}
        ORDER BY marketCap DESC
        LIMIT {top_n}
    """
    df = pd.read_sql(query, db.engine)
    db.close()
    return df.to_dict(orient="records")


@app.get("/get_low_beta_stocks")
def get_low_beta_stocks(min_mktcap: int = 0, top_n: int = 10):
    db = get_db()
    query = f"""
        SELECT * FROM financial_tbl
        WHERE marketCap >= {min_mktcap}
        ORDER BY beta ASC
        LIMIT {top_n}
    """
    df = pd.read_sql(query, db.engine)
    db.close()
    return df.to_dict(orient="records")


@app.get("/get_high_dividend_yield_stocks")
def get_high_dividend_yield_stocks(min_mktcap: int = 0, top_n: int = 10):
    db = get_db()
    query = f"""
        SELECT * FROM financial_tbl
        WHERE marketCap >= {min_mktcap}
        ORDER BY dividendYield DESC
        LIMIT {top_n}
    """
    df = pd.read_sql(query, db.engine)
    db.close()
    return df.to_dict(orient="records")


@app.get("/get_high_momentum_stocks")
def get_high_momentum_stocks(min_mktcap: int = 0, top_n: int = 10):
    db = get_db()
    query = f"""
        SELECT * FROM financial_tbl
        WHERE marketCap >= {min_mktcap}
        ORDER BY return_12m DESC
        LIMIT {top_n}
    """
    df = pd.read_sql(query, db.engine)
    db.close()
    return df.to_dict(orient="records")


@app.get("/get_low_volatility_stocks")
def get_low_volatility_stocks(min_mktcap: int = 0, top_n: int = 10):
    db = get_db()
    query = f"""
        SELECT * FROM financial_tbl
        WHERE marketCap >= {min_mktcap}
        ORDER BY volatility ASC
        LIMIT {top_n}
    """
    df = pd.read_sql(query, db.engine)
    db.close()
    return df.to_dict(orient="records")


@app.get("/get_top_short_term_momentum_stocks")
def get_top_short_term_momentum_stocks(min_mktcap: int = 0, top_n: int = 10):
    db = get_db()
    query = f"""
        SELECT * FROM financial_tbl
        WHERE marketCap >= {min_mktcap}
        ORDER BY return_3m DESC
        LIMIT {top_n}
    """
    df = pd.read_sql(query, db.engine)
    db.close()
    return df.to_dict(orient="records")


@app.get("/get_high_dividend_low_beta_stocks")
def get_high_dividend_low_beta_stocks(min_mktcap: int = 0, top_n: int = 10):
    db = get_db()
    query = f"""
        SELECT * FROM financial_tbl
        WHERE marketCap >= {min_mktcap}
        ORDER BY dividendYield DESC, beta ASC
        LIMIT {top_n}
    """
    df = pd.read_sql(query, db.engine)
    db.close()
    return df.to_dict(orient="records")


@app.get("/get_top_factor_composite_stocks")
def get_top_factor_composite_stocks(min_mktcap: int = 0, top_n: int = 10):
    db = get_db()
    query = f"""
        SELECT * FROM financial_tbl
        WHERE marketCap >= {min_mktcap}
        ORDER BY factor_composite DESC
        LIMIT {top_n}
    """
    df = pd.read_sql(query, db.engine)
    db.close()
    return df.to_dict(orient="records")


@app.get("/get_high_risk_stocks")
def get_high_risk_stocks(min_mktcap: int = 0, top_n: int = 10):
    db = get_db()
    query = f"""
        SELECT * FROM financial_tbl
        WHERE marketCap >= {min_mktcap}
        ORDER BY risk_score DESC
        LIMIT {top_n}
    """
    df = pd.read_sql(query, db.engine)
    db.close()
    return df.to_dict(orient="records")


@app.get("/get_top_combined_screen_limited")
def get_top_combined_screen_limited(min_mktcap: int = 0, top_n: int = 10):
    db = get_db()
    query = f"""
        SELECT * FROM financial_tbl
        WHERE marketCap >= {min_mktcap}
        AND factor_composite > 0.5
        AND norm_quality_score > 0.5
        AND return_12m > 0.1
        ORDER BY factor_composite DESC, norm_quality_score DESC, return_12m DESC
        LIMIT {top_n}
    """
    df = pd.read_sql(query, db.engine)
    db.close()
    return df.to_dict(orient="records")
