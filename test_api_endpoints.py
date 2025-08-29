import requests

API_URL = "https://YOUR_CLOUD_RUN_URL"  # Replace with your deployed FastAPI URL

def test_health():
    r = requests.get(f"{API_URL}/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    print("Health endpoint OK")

def test_endpoint(endpoint, params=None):
    r = requests.get(f"{API_URL}/{endpoint}", params=params)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    print(f"{endpoint} returned {len(data)} records")

if __name__ == "__main__":
    test_health()
    endpoints = [
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
        "get_top_combined_screen_limited"
    ]
    for ep in endpoints:
        test_endpoint(ep, params={"min_mktcap":0, "top_n":5})
    print("All API endpoint tests passed.")
