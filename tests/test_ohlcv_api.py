#!/usr/bin/env python3
"""
Test script to verify OHLCV API endpoints work correctly.
"""

import sys
import os
import requests
import time
sys.path.append(os.path.join(os.path.dirname(__file__), 'data_pipeline'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'web'))

def test_ohlcv_endpoints():
    """Test the OHLCV-specific API endpoints."""
    base_url = "http://localhost:8000"

    print("Testing OHLCV API endpoints...")

    # Test endpoints that require OHLCV data
    endpoints = [
        "/get_undervalued_stocks_ohlcv?top_n=5",
        "/get_overvalued_stocks_ohlcv?top_n=5",
        "/get_undervalued_stocks?top_n=5",  # Regular endpoint for comparison
        "/get_overvalued_stocks?top_n=5",   # Regular endpoint for comparison
    ]

    results = {}

    for endpoint in endpoints:
        try:
            print(f"\nTesting {endpoint}...")
            response = requests.get(f"{base_url}{endpoint}", timeout=30)

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Status 200 - Received {len(data)} records")

                if data:
                    # Check if records have OHLCV data
                    sample_record = data[0]
                    ohlcv_fields = ['Open', 'High', 'Low', 'close_price']
                    has_ohlcv = all(field in sample_record for field in ohlcv_fields)

                    if has_ohlcv:
                        # Check if OHLCV values are not null
                        ohlcv_values = [sample_record.get(field) for field in ohlcv_fields]
                        ohlcv_complete = all(val is not None for val in ohlcv_values)
                        print(f"✅ OHLCV data present and {'complete' if ohlcv_complete else 'incomplete'}")
                    else:
                        print("❌ OHLCV fields missing from response")

                    results[endpoint] = {
                        'status': 'success',
                        'record_count': len(data),
                        'has_ohlcv': has_ohlcv,
                        'sample_ticker': sample_record.get('Ticker')
                    }
                else:
                    print("⚠️  Empty response")
                    results[endpoint] = {'status': 'empty', 'record_count': 0}

            else:
                print(f"❌ Status {response.status_code}: {response.text}")
                results[endpoint] = {'status': 'error', 'code': response.status_code}

        except requests.exceptions.ConnectionError:
            print(f"❌ Connection failed - API server not running")
            return False
        except Exception as e:
            print(f"❌ Error: {e}")
            results[endpoint] = {'status': 'exception', 'error': str(e)}

    return results

def test_health_endpoint():
    """Test the health endpoint to verify API connectivity."""
    try:
        response = requests.get("http://localhost:8000/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

if __name__ == "__main__":
    print("Testing OHLCV API endpoints...")

    # First check if API server is running
    if not test_health_endpoint():
        print("\n❌ API server is not running. Please start the API server first.")
        print("Run: cd web && python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload")
        sys.exit(1)

    # Test OHLCV endpoints
    results = test_ohlcv_endpoints()

    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)

    success_count = 0
    total_count = len(results)

    for endpoint, result in results.items():
        status = result.get('status')
        if status == 'success':
            success_count += 1
            record_count = result.get('record_count', 0)
            has_ohlcv = result.get('has_ohlcv', False)
            ticker = result.get('sample_ticker', 'N/A')
            print(f"✅ {endpoint}: {record_count} records, OHLCV={'Yes' if has_ohlcv else 'No'}, Sample: {ticker}")
        else:
            print(f"❌ {endpoint}: {status}")

    print(f"\nOverall: {success_count}/{total_count} endpoints working")

    if success_count == total_count:
        print("🎉 All OHLCV endpoints are working correctly!")
        sys.exit(0)
    else:
        print("⚠️  Some endpoints have issues")
        sys.exit(1)
