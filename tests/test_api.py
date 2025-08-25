from fastapi.testclient import TestClient
from web.api import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_compute_factors_endpoint():
    payload = {
        "data": [
            {
                "Date": "2023-07-01",
                "Ticker": "ADV.L",
                "Open": 100,
                "High": 110,
                "Low": 90,
                "Close": 105,
                "Volume": 1000,
                "returnOnEquity": 0.2,
                "profitMargins": 0.15,
                "priceToBook": 1.8,
                "trailingPE": 12.0,
                "marketCap": 2000000,
                "grossMargins": 0.3,
                "operatingMargins": 0.2,
                "forwardPE": 11.5,
                "priceToSalesTrailing12Months": 2.0,
                "debtToEquity": 0.4,
                "currentRatio": 1.2,
                "quickRatio": 1.1,
                "dividendYield": 0.03,
                "beta": 1.05,
                "averageVolume": 1000
            },
            {
                "Date": "2023-07-02",
                "Ticker": "ADV.L",
                "Open": 101,
                "High": 111,
                "Low": 91,
                "Close": 106,
                "Volume": 1100,
                "returnOnEquity": 0.2,
                "profitMargins": 0.15,
                "priceToBook": 1.8,
                "trailingPE": 12.0,
                "marketCap": 2000000,
                "grossMargins": 0.3,
                "operatingMargins": 0.2,
                "forwardPE": 11.5,
                "priceToSalesTrailing12Months": 2.0,
                "debtToEquity": 0.4,
                "currentRatio": 1.2,
                "quickRatio": 1.1,
                "dividendYield": 0.03,
                "beta": 1.05,
                "averageVolume": 1000
            }
        ]
    }
    response = client.post("/compute-factors", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list) and len(data) == 2
    assert "factor_composite" in data[0]
