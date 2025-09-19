#!/usr/bin/env python3
"""
Enhanced test for OHLCV-specific API endpoints.
"""

import requests
import json
import time
from typing import Dict, List, Any, Optional

class OHLCVTester:
    """Class to test OHLCV-specific functionality."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.timeout = 15
        
    def test_ohlcv_endpoint(self, endpoint: str = "get_undervalued_stocks_ohlcv", 
                           params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Test a specific OHLCV endpoint."""
        if params is None:
            params = {"top_n": 5}
            
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/{endpoint}", params=params)
            response_time = time.time() - start_time
            
            result = {
                "endpoint": endpoint,
                "params": params,
                "status_code": response.status_code,
                "response_time": response_time,
                "data_count": 0,
                "ohlcv_completeness": {},
                "data_quality": {},
                "error": None
            }
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and data:
                    result["data_count"] = len(data)
                    
                    # Analyze OHLCV data quality
                    ohlcv_fields = ['Open', 'High', 'Low', 'close_price']
                    completeness_stats = {field: {"present": 0, "null": 0, "valid": 0} for field in ohlcv_fields}
                    
                    valid_records = 0
                    price_anomalies = []
                    
                    for i, record in enumerate(data):
                        record_valid = True
                        record_ohlcv = {}
                        
                        # Check OHLCV field presence and validity
                        for field in ohlcv_fields:
                            if field in record:
                                completeness_stats[field]["present"] += 1
                                value = record[field]
                                if value is not None:
                                    completeness_stats[field]["valid"] += 1
                                    record_ohlcv[field] = value
                                else:
                                    completeness_stats[field]["null"] += 1
                                    record_valid = False
                            else:
                                record_valid = False
                        
                        # Validate OHLCV relationships (High >= Low, etc.)
                        if record_valid and len(record_ohlcv) == 4:
                            try:
                                open_price = float(record_ohlcv['Open'])
                                high_price = float(record_ohlcv['High'])
                                low_price = float(record_ohlcv['Low'])
                                close_price = float(record_ohlcv['close_price'])
                                
                                # Check logical relationships
                                if not (low_price <= open_price <= high_price and 
                                       low_price <= close_price <= high_price):
                                    price_anomalies.append({
                                        "record_index": i,
                                        "ticker": record.get("Ticker", "Unknown"),
                                        "ohlc": record_ohlcv,
                                        "issue": "Invalid OHLC relationship"
                                    })
                                    record_valid = False
                                
                                # Check for extreme price movements (>50% gap)
                                if abs(close_price - open_price) / open_price > 0.5:
                                    price_anomalies.append({
                                        "record_index": i,
                                        "ticker": record.get("Ticker", "Unknown"),
                                        "ohlc": record_ohlcv,
                                        "issue": f"Extreme price movement: {((close_price - open_price) / open_price * 100):.1f}%"
                                    })
                                
                            except (ValueError, TypeError, ZeroDivisionError):
                                price_anomalies.append({
                                    "record_index": i,
                                    "ticker": record.get("Ticker", "Unknown"),
                                    "ohlc": record_ohlcv,
                                    "issue": "Invalid price data types"
                                })
                                record_valid = False
                        
                        if record_valid:
                            valid_records += 1
                    
                    # Calculate completeness percentages
                    total_records = len(data)
                    result["ohlcv_completeness"] = {
                        field: {
                            "present_pct": (stats["present"] / total_records) * 100,
                            "valid_pct": (stats["valid"] / total_records) * 100,
                            "null_pct": (stats["null"] / total_records) * 100
                        }
                        for field, stats in completeness_stats.items()
                    }
                    
                    result["data_quality"] = {
                        "total_records": total_records,
                        "valid_records": valid_records,
                        "valid_percentage": (valid_records / total_records) * 100,
                        "price_anomalies": price_anomalies,
                        "anomaly_count": len(price_anomalies)
                    }
                    
                elif isinstance(data, list):
                    result["error"] = "Empty data returned"
                else:
                    result["error"] = f"Unexpected data type: {type(data)}"
            else:
                result["error"] = f"HTTP {response.status_code}: {response.text[:200]}"
                
        except Exception as e:
            result["error"] = str(e)
            
        return result
    
    def test_all_ohlcv_endpoints(self) -> Dict[str, Dict[str, Any]]:
        """Test all OHLCV-related endpoints."""
        ohlcv_endpoints = [
            "get_undervalued_stocks_ohlcv",
            "get_overvalued_stocks_ohlcv",
            # Regular endpoints that should have OHLCV data
            "get_undervalued_stocks",
            "get_overvalued_stocks"
        ]
        
        results = {}
        for endpoint in ohlcv_endpoints:
            print(f"Testing {endpoint}...")
            results[endpoint] = self.test_ohlcv_endpoint(endpoint)
            time.sleep(0.2)  # Small delay between requests
            
        return results
    
    def test_ohlcv_filtering(self) -> Dict[str, Any]:
        """Test that OHLCV endpoints properly filter for valid OHLCV data."""
        # Compare regular vs OHLCV-specific endpoints
        regular_result = self.test_ohlcv_endpoint("get_undervalued_stocks", {"top_n": 20})
        ohlcv_result = self.test_ohlcv_endpoint("get_undervalued_stocks_ohlcv", {"top_n": 20})
        
        comparison = {
            "regular_endpoint": {
                "data_count": regular_result.get("data_count", 0),
                "valid_records": regular_result.get("data_quality", {}).get("valid_records", 0)
            },
            "ohlcv_endpoint": {
                "data_count": ohlcv_result.get("data_count", 0),
                "valid_records": ohlcv_result.get("data_quality", {}).get("valid_records", 0)
            }
        }
        
        # OHLCV endpoint should have higher percentage of valid records
        if (comparison["regular_endpoint"]["data_count"] > 0 and 
            comparison["ohlcv_endpoint"]["data_count"] > 0):
            
            regular_valid_pct = (comparison["regular_endpoint"]["valid_records"] / 
                               comparison["regular_endpoint"]["data_count"]) * 100
            ohlcv_valid_pct = (comparison["ohlcv_endpoint"]["valid_records"] / 
                             comparison["ohlcv_endpoint"]["data_count"]) * 100
            
            comparison["filtering_effectiveness"] = {
                "regular_valid_pct": regular_valid_pct,
                "ohlcv_valid_pct": ohlcv_valid_pct,
                "improvement": ohlcv_valid_pct - regular_valid_pct,
                "filtering_working": ohlcv_valid_pct >= regular_valid_pct
            }
        
        return comparison
    
    def test_parameter_combinations(self) -> Dict[str, Any]:
        """Test various parameter combinations with OHLCV endpoints."""
        test_cases = [
            {"top_n": 1, "min_mktcap": 0},
            {"top_n": 5, "min_mktcap": 1000000},
            {"top_n": 10, "min_mktcap": 10000000},
            {"top_n": 3, "company": "Apple"},
            {"top_n": 3, "sector": "Technology"}
        ]
        
        results = {}
        for i, params in enumerate(test_cases):
            test_name = f"param_test_{i+1}"
            print(f"Testing parameters: {params}")
            
            result = self.test_ohlcv_endpoint("get_undervalued_stocks_ohlcv", params)
            results[test_name] = {
                "params": params,
                "status_code": result["status_code"],
                "data_count": result["data_count"],
                "response_time": result["response_time"],
                "valid_percentage": result.get("data_quality", {}).get("valid_percentage", 0)
            }
            
        return results
    
    def generate_ohlcv_report(self) -> str:
        """Generate comprehensive OHLCV test report."""
        print("=" * 80)
        print("OHLCV ENDPOINT TEST REPORT")
        print("=" * 80)
        
        # Test basic OHLCV endpoint
        print("\n1. BASIC OHLCV ENDPOINT TEST")
        print("-" * 40)
        basic_result = self.test_ohlcv_endpoint()
        
        if basic_result["status_code"] == 200:
            print(f"✅ Status: {basic_result['status_code']}")
            print(f"✅ Response time: {basic_result['response_time']:.3f}s")
            print(f"✅ Records returned: {basic_result['data_count']}")
            
            if "data_quality" in basic_result:
                quality = basic_result["data_quality"]
                print(f"✅ Valid records: {quality['valid_records']}/{quality['total_records']} ({quality['valid_percentage']:.1f}%)")
                
                if quality["anomaly_count"] > 0:
                    print(f"⚠️  Price anomalies found: {quality['anomaly_count']}")
                    for anomaly in quality["price_anomalies"][:3]:  # Show first 3
                        print(f"   - {anomaly['ticker']}: {anomaly['issue']}")
                else:
                    print("✅ No price anomalies detected")
            
            if "ohlcv_completeness" in basic_result:
                print("\nOHLCV Field Completeness:")
                for field, stats in basic_result["ohlcv_completeness"].items():
                    print(f"  {field}: {stats['valid_pct']:.1f}% valid, {stats['null_pct']:.1f}% null")
        else:
            print(f"❌ Status: {basic_result['status_code']}")
            print(f"❌ Error: {basic_result['error']}")
        
        # Test all OHLCV endpoints
        print("\n2. ALL OHLCV ENDPOINTS TEST")
        print("-" * 40)
        all_results = self.test_all_ohlcv_endpoints()
        
        for endpoint, result in all_results.items():
            status = "✅" if result["status_code"] == 200 else "❌"
            count = result["data_count"]
            valid_pct = result.get("data_quality", {}).get("valid_percentage", 0)
            print(f"  {status} {endpoint}: {count} records, {valid_pct:.1f}% valid")
        
        # Test OHLCV filtering effectiveness
        print("\n3. OHLCV FILTERING TEST")
        print("-" * 40)
        filtering_result = self.test_ohlcv_filtering()
        
        if "filtering_effectiveness" in filtering_result:
            eff = filtering_result["filtering_effectiveness"]
            status = "✅" if eff["filtering_working"] else "❌"
            print(f"  {status} Regular endpoint: {eff['regular_valid_pct']:.1f}% valid")
            print(f"  {status} OHLCV endpoint: {eff['ohlcv_valid_pct']:.1f}% valid")
            print(f"  {status} Improvement: {eff['improvement']:.1f}%")
        else:
            print("  ❌ Could not test filtering effectiveness")
        
        # Test parameter combinations
        print("\n4. PARAMETER COMBINATION TEST")
        print("-" * 40)
        param_results = self.test_parameter_combinations()
        
        for test_name, result in param_results.items():
            status = "✅" if result["status_code"] == 200 else "❌"
            print(f"  {status} {result['params']}: {result['data_count']} records, {result['valid_percentage']:.1f}% valid")
        
        print("\n" + "=" * 80)
        return "OHLCV report generated successfully"


def test_ohlcv_endpoint():
    """Main test function for backward compatibility."""
    tester = OHLCVTester()
    
    # Run basic test
    result = tester.test_ohlcv_endpoint()
    
    if result["status_code"] == 200 and result["data_count"] > 0:
        record = result  # This will be updated to show first record
        print('OHLCV endpoint test results:')
        print(f'Status: {result["status_code"]}')
        print(f'Records returned: {result["data_count"]}')
        print(f'Response time: {result["response_time"]:.3f}s')
        
        if "data_quality" in result:
            quality = result["data_quality"]
            print(f'Valid records: {quality["valid_records"]}/{quality["total_records"]} ({quality["valid_percentage"]:.1f}%)')
            
        if "ohlcv_completeness" in result:
            print('\nOHLCV Field Status:')
            for field, stats in result["ohlcv_completeness"].items():
                print(f'  {field}: {stats["valid_pct"]:.1f}% valid')
    else:
        print(f'OHLCV endpoint test failed: {result.get("error", "Unknown error")}')


def test_comprehensive_ohlcv():
    """Comprehensive OHLCV testing."""
    tester = OHLCVTester()
    
    # Run all tests
    basic_result = tester.test_ohlcv_endpoint()
    all_results = tester.test_all_ohlcv_endpoints()
    filtering_result = tester.test_ohlcv_filtering()
    param_results = tester.test_parameter_combinations()
    
    # Save results
    comprehensive_results = {
        "basic_ohlcv_test": basic_result,
        "all_ohlcv_endpoints": all_results,
        "filtering_test": filtering_result,
        "parameter_tests": param_results,
        "summary": {
            "total_endpoints_tested": len(all_results),
            "successful_endpoints": sum(1 for r in all_results.values() if r["status_code"] == 200),
            "average_response_time": sum(r.get("response_time", 0) for r in all_results.values()) / len(all_results)
        }
    }
    
    with open("ohlcv_test_results.json", "w") as f:
        json.dump(comprehensive_results, f, indent=2, default=str)
    
    print("Comprehensive OHLCV test results saved to ohlcv_test_results.json")
    return comprehensive_results


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--comprehensive":
        test_comprehensive_ohlcv()
    elif len(sys.argv) > 1 and sys.argv[1] == "--report":
        tester = OHLCVTester()
        tester.generate_ohlcv_report()
    else:
        test_ohlcv_endpoint()
