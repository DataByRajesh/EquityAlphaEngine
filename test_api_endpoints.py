#!/usr/bin/env python3
"""
Enhanced integration tests for API endpoints.
"""

import requests
import json
import time
import concurrent.futures
from typing import Dict, List, Any, Optional
import statistics

class APIIntegrationTester:
    """Class for comprehensive API integration testing."""
    
    def __init__(self, api_url: str = "http://localhost:8000"):
        # Use localhost by default, can be overridden for deployed testing
        self.api_url = api_url
        self.session = requests.Session()
        self.session.timeout = 30
        
    def test_health(self) -> Dict[str, Any]:
        """Test health endpoint with detailed analysis."""
        try:
            start_time = time.time()
            response = self.session.get(f"{self.api_url}/health")
            response_time = time.time() - start_time
            
            result = {
                "endpoint": "health",
                "status_code": response.status_code,
                "response_time": response_time,
                "success": False,
                "data": None,
                "error": None
            }
            
            if response.status_code == 200:
                data = response.json()
                result["data"] = data
                result["success"] = data.get("status") == "ok"
                
                if "database" in data:
                    result["database_status"] = data["database"]
            else:
                result["error"] = f"HTTP {response.status_code}: {response.text[:200]}"
                
        except Exception as e:
            result["error"] = str(e)
            
        return result
    
    def test_endpoint(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Test a single endpoint with comprehensive analysis."""
        if params is None:
            params = {"min_mktcap": 0, "top_n": 5}
            
        try:
            start_time = time.time()
            response = self.session.get(f"{self.api_url}/{endpoint}", params=params)
            response_time = time.time() - start_time
            
            result = {
                "endpoint": endpoint,
                "params": params,
                "status_code": response.status_code,
                "response_time": response_time,
                "success": False,
                "data_count": 0,
                "data_sample": None,
                "error": None
            }
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    result["success"] = True
                    result["data_count"] = len(data)
                    if data:
                        result["data_sample"] = data[0]  # First record as sample
                        
                        # Analyze data quality
                        result["data_quality"] = self._analyze_data_quality(data)
                else:
                    result["error"] = f"Unexpected data type: {type(data)}"
            else:
                result["error"] = f"HTTP {response.status_code}: {response.text[:200]}"
                
        except Exception as e:
            result["error"] = str(e)
            
        return result
    
    def _analyze_data_quality(self, data: List[Dict]) -> Dict[str, Any]:
        """Analyze data quality metrics."""
        if not data:
            return {"empty": True}
            
        total_records = len(data)
        null_counts = {}
        field_types = {}
        
        # Analyze first record to get field structure
        sample_record = data[0]
        for field in sample_record.keys():
            null_counts[field] = 0
            field_types[field] = set()
        
        # Count nulls and track types
        for record in data:
            for field, value in record.items():
                if value is None:
                    null_counts[field] += 1
                else:
                    field_types[field].add(type(value).__name__)
        
        # Calculate null percentages
        null_percentages = {
            field: (count / total_records) * 100 
            for field, count in null_counts.items()
        }
        
        return {
            "total_records": total_records,
            "null_percentages": null_percentages,
            "field_types": {field: list(types) for field, types in field_types.items()},
            "high_null_fields": [field for field, pct in null_percentages.items() if pct > 50]
        }
    
    def test_all_endpoints(self) -> Dict[str, Dict[str, Any]]:
        """Test all stock screening endpoints."""
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
            "get_top_combined_screen_limited",
            "get_undervalued_stocks_ohlcv",
            "get_overvalued_stocks_ohlcv",
            "get_macro_data",
            "get_unique_sectors"
        ]
        
        results = {}
        for endpoint in endpoints:
            print(f"Testing {endpoint}...")
            
            # Use different params for utility endpoints
            if endpoint in ["get_macro_data", "get_unique_sectors"]:
                params = None
            else:
                params = {"min_mktcap": 0, "top_n": 5}
                
            results[endpoint] = self.test_endpoint(endpoint, params)
            time.sleep(0.1)  # Small delay between requests
            
        return results
    
    def test_parameter_variations(self) -> Dict[str, Dict[str, Any]]:
        """Test various parameter combinations."""
        test_cases = [
            {"name": "small_mktcap", "params": {"min_mktcap": 1000000, "top_n": 3}},
            {"name": "large_mktcap", "params": {"min_mktcap": 10000000, "top_n": 3}},
            {"name": "max_results", "params": {"min_mktcap": 0, "top_n": 100}},
            {"name": "min_results", "params": {"min_mktcap": 0, "top_n": 1}},
            {"name": "with_company", "params": {"company": "Apple", "top_n": 5}},
            {"name": "with_sector", "params": {"sector": "Technology", "top_n": 5}},
        ]
        
        results = {}
        endpoint = "get_undervalued_stocks"  # Use one endpoint for parameter testing
        
        for test_case in test_cases:
            print(f"Testing parameters: {test_case['name']}")
            results[test_case["name"]] = self.test_endpoint(endpoint, test_case["params"])
            time.sleep(0.1)
            
        return results
    
    def test_concurrent_requests(self, num_concurrent: int = 5) -> Dict[str, Any]:
        """Test API under concurrent load."""
        endpoint = "get_undervalued_stocks"
        params = {"min_mktcap": 0, "top_n": 5}
        
        def make_request():
            return self.test_endpoint(endpoint, params)
        
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = [executor.submit(make_request) for _ in range(num_concurrent)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        total_time = time.time() - start_time
        
        # Analyze results
        successful_requests = sum(1 for r in results if r["success"])
        response_times = [r["response_time"] for r in results if "response_time" in r]
        
        return {
            "total_requests": num_concurrent,
            "successful_requests": successful_requests,
            "success_rate": (successful_requests / num_concurrent) * 100,
            "total_time": total_time,
            "average_response_time": statistics.mean(response_times) if response_times else 0,
            "max_response_time": max(response_times) if response_times else 0,
            "min_response_time": min(response_times) if response_times else 0,
            "individual_results": results
        }
    
    def test_error_conditions(self) -> Dict[str, Dict[str, Any]]:
        """Test various error conditions."""
        error_tests = [
            {"name": "invalid_endpoint", "endpoint": "nonexistent_endpoint", "params": {}},
            {"name": "negative_top_n", "endpoint": "get_undervalued_stocks", "params": {"top_n": -1}},
            {"name": "excessive_top_n", "endpoint": "get_undervalued_stocks", "params": {"top_n": 1000}},
            {"name": "negative_mktcap", "endpoint": "get_undervalued_stocks", "params": {"min_mktcap": -1}},
            {"name": "invalid_sector", "endpoint": "get_undervalued_stocks", "params": {"sector": "NonexistentSector"}},
        ]
        
        results = {}
        for test in error_tests:
            print(f"Testing error condition: {test['name']}")
            try:
                response = self.session.get(f"{self.api_url}/{test['endpoint']}", params=test["params"])
                results[test["name"]] = {
                    "status_code": response.status_code,
                    "expected_error": True,
                    "got_error": response.status_code >= 400,
                    "response_text": response.text[:200]
                }
            except Exception as e:
                results[test["name"]] = {
                    "status_code": None,
                    "expected_error": True,
                    "got_error": True,
                    "error": str(e)
                }
            time.sleep(0.1)
            
        return results
    
    def generate_integration_report(self) -> str:
        """Generate comprehensive integration test report."""
        print("=" * 80)
        print("API INTEGRATION TEST REPORT")
        print("=" * 80)
        
        # Test health endpoint
        print("\n1. HEALTH ENDPOINT TEST")
        print("-" * 40)
        health_result = self.test_health()
        
        if health_result["success"]:
            print(f"✅ Health check passed ({health_result['response_time']:.3f}s)")
            print(f"✅ Database status: {health_result.get('database_status', 'unknown')}")
        else:
            print(f"❌ Health check failed: {health_result['error']}")
        
        # Test all endpoints
        print("\n2. ALL ENDPOINTS TEST")
        print("-" * 40)
        all_results = self.test_all_endpoints()
        
        successful_endpoints = sum(1 for r in all_results.values() if r["success"])
        total_endpoints = len(all_results)
        avg_response_time = statistics.mean([r["response_time"] for r in all_results.values() if "response_time" in r])
        
        print(f"Success rate: {successful_endpoints}/{total_endpoints} ({(successful_endpoints/total_endpoints)*100:.1f}%)")
        print(f"Average response time: {avg_response_time:.3f}s")
        
        for endpoint, result in all_results.items():
            status = "✅" if result["success"] else "❌"
            count = result["data_count"] if result["success"] else 0
            time_str = f"{result['response_time']:.3f}s" if "response_time" in result else "N/A"
            print(f"  {status} {endpoint}: {count} records, {time_str}")
        
        # Test parameter variations
        print("\n3. PARAMETER VARIATION TEST")
        print("-" * 40)
        param_results = self.test_parameter_variations()
        
        for test_name, result in param_results.items():
            status = "✅" if result["success"] else "❌"
            count = result["data_count"] if result["success"] else 0
            print(f"  {status} {test_name}: {count} records")
        
        # Test concurrent requests
        print("\n4. CONCURRENT REQUEST TEST")
        print("-" * 40)
        concurrent_result = self.test_concurrent_requests()
        
        print(f"✅ Concurrent requests: {concurrent_result['total_requests']}")
        print(f"✅ Success rate: {concurrent_result['success_rate']:.1f}%")
        print(f"✅ Average response time: {concurrent_result['average_response_time']:.3f}s")
        print(f"✅ Max response time: {concurrent_result['max_response_time']:.3f}s")
        
        # Test error conditions
        print("\n5. ERROR CONDITION TEST")
        print("-" * 40)
        error_results = self.test_error_conditions()
        
        for test_name, result in error_results.items():
            status = "✅" if result["got_error"] else "❌"
            status_code = result.get("status_code", "N/A")
            print(f"  {status} {test_name}: HTTP {status_code}")
        
        print("\n" + "=" * 80)
        return "Integration test report generated successfully"


def test_health():
    """Backward compatibility function."""
    tester = APIIntegrationTester()
    result = tester.test_health()
    
    if result["success"]:
        print("Health endpoint OK")
        return True
    else:
        print(f"Health endpoint failed: {result['error']}")
        return False


def test_endpoint(endpoint, params=None):
    """Backward compatibility function."""
    tester = APIIntegrationTester()
    result = tester.test_endpoint(endpoint, params)
    
    if result["success"]:
        print(f"{endpoint} returned {result['data_count']} records")
        return True
    else:
        print(f"{endpoint} failed: {result['error']}")
        return False


def test_comprehensive_integration():
    """Comprehensive integration testing."""
    tester = APIIntegrationTester()
    
    # Run all tests
    health_result = tester.test_health()
    all_results = tester.test_all_endpoints()
    param_results = tester.test_parameter_variations()
    concurrent_result = tester.test_concurrent_requests()
    error_results = tester.test_error_conditions()
    
    # Save comprehensive results
    comprehensive_results = {
        "health_test": health_result,
        "all_endpoints": all_results,
        "parameter_variations": param_results,
        "concurrent_test": concurrent_result,
        "error_conditions": error_results,
        "summary": {
            "total_endpoints_tested": len(all_results),
            "successful_endpoints": sum(1 for r in all_results.values() if r["success"]),
            "average_response_time": statistics.mean([r["response_time"] for r in all_results.values() if "response_time" in r]),
            "concurrent_success_rate": concurrent_result["success_rate"],
            "error_handling_tests": len(error_results)
        }
    }
    
    with open("integration_test_results.json", "w") as f:
        json.dump(comprehensive_results, f, indent=2, default=str)
    
    print("Comprehensive integration test results saved to integration_test_results.json")
    return comprehensive_results


if __name__ == "__main__":
    import sys
    
    # Check if API URL is provided as argument
    api_url = "http://localhost:8000"
    if len(sys.argv) > 1 and sys.argv[1].startswith("http"):
        api_url = sys.argv[1]
        print(f"Using API URL: {api_url}")
    
    # Initialize tester with provided URL
    tester = APIIntegrationTester(api_url)
    
    if len(sys.argv) > 1 and "--comprehensive" in sys.argv:
        test_comprehensive_integration()
    elif len(sys.argv) > 1 and "--report" in sys.argv:
        tester.generate_integration_report()
    else:
        # Run basic tests for backward compatibility
        if test_health():
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
                "get_top_combined_screen_limited",
            ]
            
            failed_endpoints = []
            for ep in endpoints:
                if not test_endpoint(ep, params={"min_mktcap": 0, "top_n": 5}):
                    failed_endpoints.append(ep)
            
            if not failed_endpoints:
                print("All API endpoint tests passed.")
            else:
                print(f"Failed endpoints: {failed_endpoints}")
