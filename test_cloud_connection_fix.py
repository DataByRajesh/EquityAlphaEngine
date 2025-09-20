#!/usr/bin/env python3
"""
Critical-path testing for Cloud Run connection fixes.
Tests the specific endpoints that were failing: get_high_earnings_yield_stocks and get_unique_sectors.
"""

import requests
import time
import logging
import os
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# API URL - use environment variable or default
API_URL = os.getenv("API_URL", "https://equity-api-248891289968.europe-west2.run.app")

# Test configuration
TEST_TIMEOUT = 30  # seconds
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

def test_api_health() -> bool:
    """Test API health endpoint."""
    try:
        logger.info("Testing API health endpoint...")
        response = requests.get(f"{API_URL}/health", timeout=TEST_TIMEOUT)
        
        if response.status_code == 200:
            logger.info("✅ API health check passed")
            return True
        else:
            logger.error(f"❌ API health check failed: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ API health check failed with exception: {e}")
        return False

def test_get_unique_sectors() -> bool:
    """Test the get_unique_sectors endpoint that was failing."""
    try:
        logger.info("Testing get_unique_sectors endpoint...")
        response = requests.get(f"{API_URL}/get_unique_sectors", timeout=TEST_TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                logger.info(f"✅ get_unique_sectors passed - returned {len(data)} sectors")
                logger.info(f"Sample sectors: {data[:3]}")
                return True
            else:
                logger.error("❌ get_unique_sectors returned empty or invalid data")
                return False
        else:
            logger.error(f"❌ get_unique_sectors failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ get_unique_sectors failed with exception: {e}")
        return False

def test_get_high_earnings_yield_stocks() -> bool:
    """Test the get_high_earnings_yield_stocks endpoint that was failing."""
    try:
        logger.info("Testing get_high_earnings_yield_stocks endpoint...")
        params = {"min_mktcap": 0, "top_n": 5}  # Small test dataset
        response = requests.get(f"{API_URL}/get_high_earnings_yield_stocks", 
                              params=params, timeout=TEST_TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                logger.info(f"✅ get_high_earnings_yield_stocks passed - returned {len(data)} stocks")
                if len(data) > 0:
                    logger.info(f"Sample stock: {data[0].get('Ticker', 'N/A')} - {data[0].get('CompanyName', 'N/A')}")
                return True
            else:
                logger.error("❌ get_high_earnings_yield_stocks returned invalid data format")
                return False
        else:
            logger.error(f"❌ get_high_earnings_yield_stocks failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ get_high_earnings_yield_stocks failed with exception: {e}")
        return False

def test_connection_resilience() -> bool:
    """Test connection resilience with multiple rapid requests."""
    try:
        logger.info("Testing connection resilience with multiple requests...")
        success_count = 0
        total_requests = 5
        
        for i in range(total_requests):
            try:
                response = requests.get(f"{API_URL}/health", timeout=TEST_TIMEOUT)
                if response.status_code == 200:
                    success_count += 1
                time.sleep(0.5)  # Small delay between requests
            except Exception as e:
                logger.warning(f"Request {i+1} failed: {e}")
        
        success_rate = success_count / total_requests
        if success_rate >= 0.8:  # 80% success rate acceptable
            logger.info(f"✅ Connection resilience test passed - {success_rate:.1%} success rate")
            return True
        else:
            logger.error(f"❌ Connection resilience test failed - {success_rate:.1%} success rate")
            return False
            
    except Exception as e:
        logger.error(f"❌ Connection resilience test failed with exception: {e}")
        return False

def run_critical_path_tests() -> Dict[str, bool]:
    """Run all critical path tests."""
    logger.info("=" * 60)
    logger.info("STARTING CRITICAL-PATH TESTING FOR CLOUD CONNECTION FIXES")
    logger.info("=" * 60)
    
    results = {}
    
    # Test 1: API Health
    results['api_health'] = test_api_health()
    time.sleep(1)
    
    # Test 2: Sectors endpoint (was failing)
    results['get_unique_sectors'] = test_get_unique_sectors()
    time.sleep(1)
    
    # Test 3: High earnings yield stocks endpoint (was failing)
    results['get_high_earnings_yield_stocks'] = test_get_high_earnings_yield_stocks()
    time.sleep(1)
    
    # Test 4: Connection resilience
    results['connection_resilience'] = test_connection_resilience()
    
    return results

def print_test_summary(results: Dict[str, bool]):
    """Print test summary."""
    logger.info("=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, passed_test in results.items():
        status = "✅ PASSED" if passed_test else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
    
    logger.info("-" * 60)
    logger.info(f"OVERALL: {passed}/{total} tests passed ({passed/total:.1%})")
    
    if passed == total:
        logger.info("🎉 ALL CRITICAL-PATH TESTS PASSED!")
        logger.info("The cloud connection fixes are working correctly.")
    else:
        logger.error("⚠️  Some tests failed. Review the logs above for details.")

if __name__ == "__main__":
    try:
        results = run_critical_path_tests()
        print_test_summary(results)
        
        # Exit with appropriate code
        if all(results.values()):
            exit(0)  # Success
        else:
            exit(1)  # Some tests failed
            
    except KeyboardInterrupt:
        logger.info("Testing interrupted by user")
        exit(130)
    except Exception as e:
        logger.error(f"Testing failed with unexpected error: {e}")
        exit(1)
