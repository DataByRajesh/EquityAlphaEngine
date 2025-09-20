#!/usr/bin/env python3
"""
Enhanced test script to check what fields are returned by API endpoints.
"""

import requests
import json
from typing import Dict, List, Any
import time

class APIFieldTester:
    """Class to test API field validation and data structure."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.timeout = 10
        
    def test_endpoint_fields(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Test fields returned by a specific endpoint."""
        if params is None:
            params = {"top_n": 1}
            
        try:
            response = self.session.get(f"{self.base_url}/{endpoint}", params=params)
            
            result = {
                "endpoint": endpoint,
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds(),
                "data_count": 0,
                "fields": {},
                "missing_fields": [],
                "null_fields": [],
                "error": None
            }
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and data:
                    result["data_count"] = len(data)
                    record = data[0]
                    
                    # Analyze fields
                    for key, value in record.items():
                        result["fields"][key] = {
                            "value": value,
                            "type": type(value).__name__,
                            "is_null": value is None
                        }
                        
                        if value is None:
                            result["null_fields"].append(key)
                            
                    # Check for expected fields
                    expected_fields = [
                        "Ticker", "CompanyName", "marketCap", "close_price",
                        "factor_composite", "earnings_yield"
                    ]
                    
                    for field in expected_fields:
                        if field not in record:
                            result["missing_fields"].append(field)
                            
                elif isinstance(data, list):
                    result["data_count"] = 0
                    result["error"] = "Empty data returned"
                else:
                    result["error"] = f"Unexpected data type: {type(data)}"
            else:
                result["error"] = f"HTTP {response.status_code}: {response.text[:200]}"
                
        except Exception as e:
            result["error"] = str(e)
            
        return result
    
    def test_ohlcv_fields(self, endpoint: str = "get_undervalued_stocks_ohlcv") -> Dict[str, Any]:
        """Test OHLCV-specific fields."""
        result = self.test_endpoint_fields(endpoint)
        
        if result["status_code"] == 200 and result["data_count"] > 0:
            ohlcv_fields = ['Open', 'High', 'Low', 'close_price']  # Note: Close is close_price
            ohlcv_status = {}
            
            for field in ohlcv_fields:
                if field in result["fields"]:
                    field_info = result["fields"][field]
                    ohlcv_status[field] = {
                        "present": True,
                        "value": field_info["value"],
                        "is_null": field_info["is_null"]
                    }
                else:
                    ohlcv_status[field] = {
                        "present": False,
                        "value": None,
                        "is_null": True
                    }
            
            result["ohlcv_status"] = ohlcv_status
            
        return result
    
    def test_all_stock_endpoints(self) -> Dict[str, Dict[str, Any]]:
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
            "get_overvalued_stocks_ohlcv"
        ]
        
        results = {}
        for endpoint in endpoints:
            print(f"Testing {endpoint}...")
            results[endpoint] = self.test_endpoint_fields(endpoint)
            time.sleep(0.1)  # Small delay to avoid overwhelming the API
            
        return results
    
    def test_parameter_validation(self) -> Dict[str, Any]:
        """Test parameter validation."""
        test_cases = [
            {"endpoint": "get_undervalued_stocks", "params": {"top_n": -1}, "expected_status": 400},
            {"endpoint": "get_undervalued_stocks", "params": {"top_n": 101}, "expected_status": 400},
            {"endpoint": "get_undervalued_stocks", "params": {"min_mktcap": -1}, "expected_status": 400},
            {"endpoint": "get_undervalued_stocks", "params": {"company": "A" * 101}, "expected_status": 400},
            {"endpoint": "get_undervalued_stocks", "params": {"sector": "A" * 101}, "expected_status": 400},
            {"endpoint": "get_undervalued_stocks", "params": {"top_n": 5, "min_mktcap": 1000000}, "expected_status": 200},
        ]
        
        results = {}
        for i, test_case in enumerate(test_cases):
            try:
                response = self.session.get(
                    f"{self.base_url}/{test_case['endpoint']}", 
                    params=test_case["params"]
                )
                
                results[f"test_{i+1}"] = {
                    "endpoint": test_case["endpoint"],
                    "params": test_case["params"],
                    "expected_status": test_case["expected_status"],
                    "actual_status": response.status_code,
                    "passed": response.status_code == test_case["expected_status"],
                    "response_time": response.elapsed.total_seconds()
                }
                
            except Exception as e:
                results[f"test_{i+1}"] = {
                    "endpoint": test_case["endpoint"],
                    "params": test_case["params"],
                    "expected_status": test_case["expected_status"],
                    "actual_status": None,
                    "passed": False,
                    "error": str(e)
                }
                
        return results
    
    def generate_report(self) -> str:
        """Generate a comprehensive test report."""
        print("=" * 80)
        print("API FIELD VALIDATION TEST REPORT")
        print("=" * 80)
        
        # Test basic field structure
        print("\n1. BASIC FIELD STRUCTURE TEST")
        print("-" * 40)
        basic_result = self.test_endpoint_fields("get_undervalued_stocks")
        
        if basic_result["status_code"] == 200:
            print(f"✅ Status: {basic_result['status_code']}")
            print(f"✅ Response time: {basic_result['response_time']:.3f}s")
            print(f"✅ Records returned: {basic_result['data_count']}")
            
            if basic_result["fields"]:
                print(f"\nFields returned ({len(basic_result['fields'])}):")
                for field, info in sorted(basic_result["fields"].items()):
                    status = "❌ NULL" if info["is_null"] else "✅"
                    print(f"  {status} {field}: {info['value']} ({info['type']})")
                    
            if basic_result["missing_fields"]:
                print(f"\n❌ Missing expected fields: {basic_result['missing_fields']}")
            else:
                print("\n✅ All expected fields present")
                
        else:
            print(f"❌ Status: {basic_result['status_code']}")
            print(f"❌ Error: {basic_result['error']}")
        
        # Test OHLCV fields
        print("\n2. OHLCV FIELD TEST")
        print("-" * 40)
        ohlcv_result = self.test_ohlcv_fields()
        
        if "ohlcv_status" in ohlcv_result:
            for field, status in ohlcv_result["ohlcv_status"].items():
                if status["present"] and not status["is_null"]:
                    print(f"  ✅ {field}: {status['value']}")
                elif status["present"] and status["is_null"]:
                    print(f"  ⚠️  {field}: Present but NULL")
                else:
                    print(f"  ❌ {field}: Missing")
        else:
            print("❌ Could not test OHLCV fields")
        
        # Test parameter validation
        print("\n3. PARAMETER VALIDATION TEST")
        print("-" * 40)
        param_results = self.test_parameter_validation()
        
        passed_tests = sum(1 for r in param_results.values() if r.get("passed", False))
        total_tests = len(param_results)
        
        print(f"Passed: {passed_tests}/{total_tests}")
        
        for test_name, result in param_results.items():
            status = "✅" if result.get("passed", False) else "❌"
            print(f"  {status} {test_name}: {result['params']} -> {result.get('actual_status', 'ERROR')}")
        
        # Test all endpoints
        print("\n4. ALL ENDPOINTS TEST")
        print("-" * 40)
        all_results = self.test_all_stock_endpoints()
        
        successful_endpoints = sum(1 for r in all_results.values() if r["status_code"] == 200)
        total_endpoints = len(all_results)
        
        print(f"Successful endpoints: {successful_endpoints}/{total_endpoints}")
        
        for endpoint, result in all_results.items():
            status = "✅" if result["status_code"] == 200 else "❌"
            count = result["data_count"] if result["status_code"] == 200 else 0
            time_str = f"{result['response_time']:.3f}s" if "response_time" in result else "N/A"
            print(f"  {status} {endpoint}: {count} records, {time_str}")
        
        print("\n" + "=" * 80)
        return "Report generated successfully"


def test_api_fields():
    """Main test function for backward compatibility."""
    tester = APIFieldTester()
    tester.generate_report()


def test_comprehensive_api_validation():
    """Comprehensive API validation test."""
    tester = APIFieldTester()
    
    # Run all tests
    basic_result = tester.test_endpoint_fields("get_undervalued_stocks")
    ohlcv_result = tester.test_ohlcv_fields()
    param_results = tester.test_parameter_validation()
    all_results = tester.test_all_stock_endpoints()
    
    # Save results to file
    comprehensive_results = {
        "basic_test": basic_result,
        "ohlcv_test": ohlcv_result,
        "parameter_validation": param_results,
        "all_endpoints": all_results,
        "summary": {
            "total_endpoints_tested": len(all_results),
            "successful_endpoints": sum(1 for r in all_results.values() if r["status_code"] == 200),
            "parameter_tests_passed": sum(1 for r in param_results.values() if r.get("passed", False)),
            "total_parameter_tests": len(param_results)
        }
    }
    
    with open("api_validation_results.json", "w") as f:
        json.dump(comprehensive_results, f, indent=2, default=str)
    
    print("Comprehensive test results saved to api_validation_results.json")
    return comprehensive_results


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--comprehensive":
        test_comprehensive_api_validation()
    else:
        test_api_fields()
