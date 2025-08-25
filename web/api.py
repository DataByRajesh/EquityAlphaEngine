from fastapi import FastAPI
from pydantic import BaseModel
import pandas as pd
from data_pipeline.compute_factors import compute_factors

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
