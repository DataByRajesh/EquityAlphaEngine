import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import pandas as pd

from web.api import app

client = TestClient(app)


def test_health_endpoint():
    """Test health endpoint returns correct status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "database" in data


def test_health_endpoint_database_error():
    """Test health endpoint when database is unavailable."""
    with patch('web.api.engine.connect') as mock_connect:
        mock_connect.side_effect = Exception("Database connection failed")
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["database"] == "disconnected"


def test_compute_factors_endpoint():
    """Test compute factors endpoint with valid data."""
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
                "averageVolume": 1000,
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
                "averageVolume": 1000,
            },
        ]
    }
    response = client.post("/compute-factors", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list) and len(data) == 2
    assert "factor_composite" in data[0]


def test_compute_factors_invalid_data():
    """Test compute factors endpoint with invalid data."""
    payload = {"data": [{"invalid": "data"}]}
    response = client.post("/compute-factors", json=payload)
    assert response.status_code == 400


def test_compute_factors_empty_data():
    """Test compute factors endpoint with empty data."""
    payload = {"data": []}
    response = client.post("/compute-factors", json=payload)
    assert response.status_code == 400


def test_root_endpoint():
    """Test root endpoint returns HTML welcome message."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Welcome to Equity Alpha Engine API" in response.text
    assert "/docs" in response.text


class TestStockEndpoints:
    """Test class for all stock screening endpoints."""
    
    def test_get_undervalued_stocks(self):
        """Test undervalued stocks endpoint."""
        response = client.get("/get_undervalued_stocks?min_mktcap=0&top_n=5")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if data:  # If data is returned
            assert len(data) <= 5
            assert "Ticker" in data[0]
            assert "factor_composite" in data[0]

    def test_get_overvalued_stocks(self):
        """Test overvalued stocks endpoint."""
        response = client.get("/get_overvalued_stocks?min_mktcap=0&top_n=5")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_high_quality_stocks(self):
        """Test high quality stocks endpoint."""
        response = client.get("/get_high_quality_stocks?min_mktcap=0&top_n=5")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_high_earnings_yield_stocks(self):
        """Test high earnings yield stocks endpoint."""
        response = client.get("/get_high_earnings_yield_stocks?min_mktcap=0&top_n=5")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_top_market_cap_stocks(self):
        """Test top market cap stocks endpoint."""
        response = client.get("/get_top_market_cap_stocks?min_mktcap=0&top_n=5")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_low_beta_stocks(self):
        """Test low beta stocks endpoint."""
        response = client.get("/get_low_beta_stocks?min_mktcap=0&top_n=5")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_high_dividend_yield_stocks(self):
        """Test high dividend yield stocks endpoint."""
        response = client.get("/get_high_dividend_yield_stocks?min_mktcap=0&top_n=5")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_high_momentum_stocks(self):
        """Test high momentum stocks endpoint."""
        response = client.get("/get_high_momentum_stocks?min_mktcap=0&top_n=5")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_low_volatility_stocks(self):
        """Test low volatility stocks endpoint."""
        response = client.get("/get_low_volatility_stocks?min_mktcap=0&top_n=5")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_top_short_term_momentum_stocks(self):
        """Test top short term momentum stocks endpoint."""
        response = client.get("/get_top_short_term_momentum_stocks?min_mktcap=0&top_n=5")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_high_dividend_low_beta_stocks(self):
        """Test high dividend low beta stocks endpoint."""
        response = client.get("/get_high_dividend_low_beta_stocks?min_mktcap=0&top_n=5")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_top_factor_composite_stocks(self):
        """Test top factor composite stocks endpoint."""
        response = client.get("/get_top_factor_composite_stocks?min_mktcap=0&top_n=5")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_high_risk_stocks(self):
        """Test high risk stocks endpoint."""
        response = client.get("/get_high_risk_stocks?min_mktcap=0&top_n=5")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_top_combined_screen_limited(self):
        """Test top combined screen limited endpoint."""
        response = client.get("/get_top_combined_screen_limited?min_mktcap=0&top_n=5")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_undervalued_stocks_ohlcv(self):
        """Test undervalued stocks with OHLCV endpoint."""
        response = client.get("/get_undervalued_stocks_ohlcv?min_mktcap=0&top_n=5")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if data:  # If data is returned, check OHLCV fields
            record = data[0]
            assert "Open" in record
            assert "High" in record
            assert "Low" in record
            assert "close_price" in record

    def test_get_overvalued_stocks_ohlcv(self):
        """Test overvalued stocks with OHLCV endpoint."""
        response = client.get("/get_overvalued_stocks_ohlcv?min_mktcap=0&top_n=5")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestParameterValidation:
    """Test parameter validation for stock endpoints."""
    
    def test_invalid_top_n_negative(self):
        """Test negative top_n parameter."""
        response = client.get("/get_undervalued_stocks?top_n=-1")
        assert response.status_code == 400

    def test_invalid_top_n_too_large(self):
        """Test top_n parameter too large."""
        response = client.get("/get_undervalued_stocks?top_n=101")
        assert response.status_code == 400

    def test_invalid_min_mktcap_negative(self):
        """Test negative min_mktcap parameter."""
        response = client.get("/get_undervalued_stocks?min_mktcap=-1")
        assert response.status_code == 400

    def test_valid_company_filter(self):
        """Test company name filtering."""
        response = client.get("/get_undervalued_stocks?company=Apple&top_n=5")
        assert response.status_code == 200

    def test_valid_sector_filter(self):
        """Test sector filtering."""
        response = client.get("/get_undervalued_stocks?sector=Technology&top_n=5")
        # This might return 400 if sector doesn't exist, which is expected behavior
        assert response.status_code in [200, 400]

    def test_company_name_too_long(self):
        """Test company name that's too long."""
        long_name = "A" * 101
        response = client.get(f"/get_undervalued_stocks?company={long_name}&top_n=5")
        assert response.status_code == 400

    def test_sector_name_too_long(self):
        """Test sector name that's too long."""
        long_sector = "A" * 101
        response = client.get(f"/get_undervalued_stocks?sector={long_sector}&top_n=5")
        assert response.status_code == 400


class TestUtilityEndpoints:
    """Test utility endpoints."""
    
    def test_get_macro_data(self):
        """Test macro data endpoint."""
        response = client.get("/get_macro_data")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_unique_sectors(self):
        """Test unique sectors endpoint."""
        response = client.get("/get_unique_sectors")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestDataValidation:
    """Test data validation and structure."""
    
    def test_response_data_structure(self):
        """Test that response data has expected structure."""
        response = client.get("/get_undervalued_stocks?top_n=1")
        assert response.status_code == 200
        data = response.json()
        
        if data:  # If data is returned
            record = data[0]
            expected_fields = [
                "Ticker", "CompanyName", "marketCap", "close_price",
                "factor_composite", "earnings_yield"
            ]
            for field in expected_fields:
                assert field in record, f"Missing field: {field}"

    def test_nan_handling(self):
        """Test that NaN values are properly handled as null."""
        response = client.get("/get_undervalued_stocks?top_n=5")
        assert response.status_code == 200
        data = response.json()
        
        if data:
            for record in data:
                for key, value in record.items():
                    # Ensure no NaN values (should be None/null)
                    assert value != "NaN"
                    assert str(value) != "nan"


class TestCaching:
    """Test caching functionality."""
    
    def test_cache_functionality(self):
        """Test that caching works by making repeated requests."""
        # First request
        response1 = client.get("/get_undervalued_stocks?top_n=5")
        assert response1.status_code == 200
        
        # Second request (should use cache)
        response2 = client.get("/get_undervalued_stocks?top_n=5")
        assert response2.status_code == 200
        
        # Responses should be identical
        assert response1.json() == response2.json()


@pytest.mark.parametrize("endpoint", [
    "get_undervalued_stocks",
    "get_overvalued_stocks", 
    "get_high_quality_stocks",
    "get_high_earnings_yield_stocks",
    "get_top_market_cap_stocks",
    "get_low_beta_stocks",
    "get_high_dividend_yield_stocks",
    "get_high_momentum_stocks",
    "get_low_volatility_stocks",
    "get_top_short_term_momentum_stocks",
    "get_high_dividend_low_beta_stocks",
    "get_top_factor_composite_stocks",
    "get_high_risk_stocks",
    "get_top_combined_screen_limited",
    "get_undervalued_stocks_ohlcv",
    "get_overvalued_stocks_ohlcv"
])
def test_all_endpoints_basic(endpoint):
    """Parametrized test for all stock endpoints."""
    response = client.get(f"/{endpoint}?top_n=3")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
