#!/usr/bin/env python3
"""
Comprehensive API testing script for database connection timeout fixes.
"""

import requests
import time
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# API base URL
BASE_URL = "http://127.0.0.1:8000"

# Test endpoints
ENDPOINTS = [
    "/health",
    "/get_undervalued_stocks?min_mktcap=0&top_n=5",
    "/get_overvalued_stocks?min_mktcap=0&top_n=5", 
    "/get_high_quality_stocks?min_mktcap=0&top_n=5",
    "/get_high_earnings_yield_stocks?min_mktcap=0&top_n=5",
    "/get_top_market_cap_stocks?min_mktcap=0&top_n=5",
    "/get_low_beta_stocks?min_mktcap=0&top_n=5",
    "/get_high_dividend_yield_stocks?min_mktcap=0&top_n=5",
    "/get_high_momentum_stocks?min_mktcap=0&top_n=5",
    "/get_low_volatility_stocks?min_mktcap=0&top_n=5",
    "/get_top_short_term_momentum_stocks?min_mktcap=0&top_n=5",
    "/get_high_dividend_low_beta_stocks?min_mktcap=0&top_n=5",
    "/get_top_factor_composite_stocks?min_mktcap=0&top_n=5",
    "/get_high_risk_stocks?min_mktcap=0&top_n=5",
    "/get_top_combined_screen_limited?min_mktcap=0&top_n=5"
]

def test_endpoint(endpoint, timeout=30):
    """Test a single endpoint with timeout and error handling."""
    url = f"{BASE_URL}{endpoint}"
    start_time = time.time()
    
    try:
        logger.info(f"Testing: {endpoint}")
        response = requests.get(url, timeout=timeout)
        elapsed_time = time.time() - start_time
        
        result = {
            'endpoint': endpoint,
            'status_code': response.status_code,
            'response_time': round(elapsed_time, 2),
            'success': response.status_code == 200,
            'error': None
        }
        
        if response.status_code == 200:
            try:
                data = response.json()
                if endpoint == "/health":
                    result['database_status'] = data.get('database', 'unknown')
                else:
                    result['data_count'] = len(data) if isinstance(data, list) else 1
                logger.info(f"✅ {endpoint} - {response.status_code} - {elapsed_time:.2f}s")
            except json.JSONDecodeError:
                result['error'] = "Invalid JSON response"
                logger.warning(f"⚠️ {endpoint} - Invalid JSON")
        else:
            result['error'] = f"HTTP {response.status_code}: {response.text[:200]}"
            logger.error(f"❌ {endpoint} - {response.status_code}")
            
    except requests.exceptions.Timeout:
        elapsed_time = time.time() - start_time
        result = {
            'endpoint': endpoint,
            'status_code': 'TIMEOUT',
            'response_time': round(elapsed_time, 2),
            'success': False,
            'error': f'Request timeout after {timeout}s'
        }
        logger.error(f"⏰ {endpoint} - TIMEOUT after {elapsed_time:.2f}s")
        
    except requests.exceptions.ConnectionError:
        elapsed_time = time.time() - start_time
        result = {
            'endpoint': endpoint,
            'status_code': 'CONNECTION_ERROR',
            'response_time': round(elapsed_time, 2),
            'success': False,
            'error': 'Connection refused - server may not be running'
        }
        logger.error(f"🔌 {endpoint} - CONNECTION_ERROR")
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        result = {
            'endpoint': endpoint,
            'status_code': 'ERROR',
            'response_time': round(elapsed_time, 2),
            'success': False,
            'error': str(e)
        }
        logger.error(f"💥 {endpoint} - ERROR: {e}")
    
    return result

def test_concurrent_requests(endpoint, num_requests=5):
    """Test concurrent requests to simulate load."""
    logger.info(f"Testing concurrent requests to {endpoint} ({num_requests} requests)")
    
    with ThreadPoolExecutor(max_workers=num_requests) as executor:
        futures = [executor.submit(test_endpoint, endpoint, 60) for _ in range(num_requests)]
        results = []
        
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(f"Concurrent test error: {e}")
                results.append({
                    'endpoint': endpoint,
                    'status_code': 'ERROR',
                    'response_time': 0,
                    'success': False,
                    'error': str(e)
                })
    
    return results

def wait_for_server(max_attempts=10, delay=2):
    """Wait for the server to be ready."""
    for attempt in range(max_attempts):
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            if response.status_code in [200, 503]:  # 503 is acceptable if DB is down
                logger.info("✅ Server is responding")
                return True
        except requests.exceptions.RequestException:
            logger.info(f"Waiting for server... attempt {attempt + 1}/{max_attempts}")
            time.sleep(delay)
    
    logger.error("❌ Server is not responding after maximum attempts")
    return False

def main():
    """Run comprehensive API tests."""
    logger.info("🚀 Starting comprehensive API testing...")
    
    # Wait for server to be ready
    if not wait_for_server():
        logger.error("Server is not available. Please start the API server first.")
        return
    
    # Test 1: Individual endpoint testing
    logger.info("\n📋 Test 1: Individual Endpoint Testing")
    results = []
    
    for endpoint in ENDPOINTS:
        result = test_endpoint(endpoint)
        results.append(result)
        time.sleep(0.5)  # Small delay between requests
    
    # Test 2: Concurrent request testing (focusing on previously failing endpoints)
    logger.info("\n🔄 Test 2: Concurrent Request Testing")
    critical_endpoints = [
        "/get_undervalued_stocks?min_mktcap=0&top_n=5",
        "/get_overvalued_stocks?min_mktcap=0&top_n=5",
        "/get_high_quality_stocks?min_mktcap=0&top_n=5"
    ]
    
    concurrent_results = []
    for endpoint in critical_endpoints:
        concurrent_result = test_concurrent_requests(endpoint, 3)
        concurrent_results.extend(concurrent_result)
        time.sleep(1)  # Delay between concurrent test batches
    
    # Test 3: Error handling testing
    logger.info("\n🚨 Test 3: Error Handling Testing")
    error_test_results = []
    
    # Test invalid endpoint
    invalid_result = test_endpoint("/invalid_endpoint")
    error_test_results.append(invalid_result)
    
    # Test with invalid parameters
    invalid_params_result = test_endpoint("/get_undervalued_stocks?min_mktcap=invalid&top_n=abc")
    error_test_results.append(invalid_params_result)
    
    # Generate summary report
    logger.info("\n📊 TEST SUMMARY REPORT")
    logger.info("=" * 50)
    
    # Individual tests summary
    successful_tests = sum(1 for r in results if r['success'])
    total_tests = len(results)
    logger.info(f"Individual Tests: {successful_tests}/{total_tests} passed")
    
    # Response time analysis
    successful_results = [r for r in results if r['success']]
    if successful_results:
        avg_response_time = sum(r['response_time'] for r in successful_results) / len(successful_results)
        max_response_time = max(r['response_time'] for r in successful_results)
        logger.info(f"Average Response Time: {avg_response_time:.2f}s")
        logger.info(f"Maximum Response Time: {max_response_time:.2f}s")
    
    # Concurrent tests summary
    concurrent_successful = sum(1 for r in concurrent_results if r['success'])
    concurrent_total = len(concurrent_results)
    logger.info(f"Concurrent Tests: {concurrent_successful}/{concurrent_total} passed")
    
    # Failed tests details
    failed_tests = [r for r in results + concurrent_results + error_test_results if not r['success']]
    if failed_tests:
        logger.info(f"\n❌ Failed Tests ({len(failed_tests)}):")
        for failed in failed_tests:
            logger.info(f"  - {failed['endpoint']}: {failed['error']}")
    
    # Health check specific results
    health_results = [r for r in results if r['endpoint'] == '/health']
    if health_results:
        health_result = health_results[0]
        if health_result['success']:
            db_status = health_result.get('database_status', 'unknown')
            logger.info(f"✅ Database Status: {db_status}")
        else:
            logger.info(f"❌ Health Check Failed: {health_result['error']}")
    
    logger.info("\n🎯 CONCLUSION:")
    if successful_tests == total_tests and concurrent_successful == concurrent_total:
        logger.info("✅ ALL TESTS PASSED - Database connection timeout fixes are working!")
    elif successful_tests > 0:
        logger.info("⚠️ PARTIAL SUCCESS - Some endpoints are working, but issues remain")
    else:
        logger.info("❌ ALL TESTS FAILED - Database connection issues persist")
    
    return results, concurrent_results, error_test_results

if __name__ == "__main__":
    main()
