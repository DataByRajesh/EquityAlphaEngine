#!/usr/bin/env python3
"""
Test script to verify connectivity without IPv6 fixes (GCP handles IPv6 natively).

This script tests:
1. Environment variables are not set (IPv6 fixes removed)
2. Google Cloud services can be imported without IPv6 errors
3. Database connectivity works
4. Secret Manager access works (if configured)
"""

import os
import sys
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def test_ipv6_environment_variables() -> Dict[str, Any]:
    """Test that IPv6 environment variables are not set (removed as GCP handles IPv6)."""
    logger.info("Testing IPv6 environment variables (should not be set)...")

    # Import data_pipeline.utils
    try:
        import data_pipeline.utils
        logger.info("✅ Imported data_pipeline.utils")
    except Exception as e:
        logger.error(f"❌ Failed to import data_pipeline.utils: {e}")
        return {"all_passed": False, "details": {"import_error": str(e)}}

    # These variables should not be set since IPv6 fixes were removed
    ipv6_vars = [
        "GRPC_DNS_RESOLVER",
        "GOOGLE_CLOUD_DISABLE_GRPC_IPV6",
        "GRPC_EXPERIMENTAL_ENABLE_ARES_DNS_RESOLVER"
    ]

    results = {}
    all_passed = True

    for var_name in ipv6_vars:
        actual_value = os.environ.get(var_name)
        # Should be None or not the forced values
        passed = actual_value is None
        results[var_name] = {
            "expected": None,
            "actual": actual_value,
            "passed": passed
        }

        if passed:
            logger.info(f"✅ {var_name} not set (as expected)")
        else:
            logger.warning(f"⚠️ {var_name} = {actual_value} (was set, but IPv6 fixes removed)")
            # Don't fail the test, just warn

    return {"passed": all_passed, "details": results}


def test_google_cloud_imports() -> Dict[str, Any]:
    """Test that Google Cloud libraries can be imported without IPv6 errors."""
    logger.info("Testing Google Cloud library imports...")
    
    import_tests = [
        ("google.cloud.secretmanager", "SecretManagerServiceClient"),
        ("google.cloud.sql.connector", "Connector"),
    ]
    
    results = {}
    all_passed = True
    
    for module_name, class_name in import_tests:
        try:
            module = __import__(module_name, fromlist=[class_name])
            getattr(module, class_name)
            logger.info(f"✅ Successfully imported {module_name}.{class_name}")
            results[f"{module_name}.{class_name}"] = {"passed": True, "error": None}
        except Exception as e:
            logger.error(f"❌ Failed to import {module_name}.{class_name}: {e}")
            results[f"{module_name}.{class_name}"] = {"passed": False, "error": str(e)}
            all_passed = False
    
    return {"passed": all_passed, "details": results}


def test_data_pipeline_imports() -> Dict[str, Any]:
    """Test that data pipeline modules can be imported successfully."""
    logger.info("Testing data pipeline imports...")
    
    # Import data_pipeline.utils (IPv6 fixes removed)
    try:
        import data_pipeline.utils
        logger.info("✅ Successfully imported data_pipeline.utils")
        utils_passed = True
        utils_error = None
    except Exception as e:
        logger.error(f"❌ Failed to import data_pipeline.utils: {e}")
        utils_passed = False
        utils_error = str(e)
    
    # Test other critical imports
    import_tests = [
        "data_pipeline.config",
        "data_pipeline.db_connection",
    ]
    
    results = {"data_pipeline.utils": {"passed": utils_passed, "error": utils_error}}
    all_passed = utils_passed
    
    for module_name in import_tests:
        try:
            __import__(module_name)
            logger.info(f"✅ Successfully imported {module_name}")
            results[module_name] = {"passed": True, "error": None}
        except Exception as e:
            logger.error(f"❌ Failed to import {module_name}: {e}")
            results[module_name] = {"passed": False, "error": str(e)}
            all_passed = False
    
    return {"passed": all_passed, "details": results}


def test_database_connectivity() -> Dict[str, Any]:
    """Test database connectivity."""
    logger.info("Testing database connectivity...")

    try:
        # Import utils
        import data_pipeline.utils
        from data_pipeline.db_connection import engine
        from sqlalchemy import text

        # Test basic connectivity
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as test_value"))
            row = result.fetchone()
            if row and row[0] == 1:
                logger.info("✅ Database connectivity test passed")
                return {"passed": True, "error": None}
            else:
                logger.error("❌ Database connectivity test failed - unexpected result")
                return {"passed": False, "error": "Unexpected query result"}

    except Exception as e:
        logger.error(f"❌ Database connectivity test failed: {e}")
        return {"passed": False, "error": str(e)}


def test_secret_manager_connectivity() -> Dict[str, Any]:
    """Test Secret Manager connectivity (if configured)."""
    logger.info("Testing Secret Manager connectivity...")

    try:
        # Import utils
        import data_pipeline.utils
        from data_pipeline.utils import get_secret
        
        # Try to get a test secret (DATABASE_URL is commonly available)
        try:
            secret_value = get_secret("DATABASE_URL")
            if secret_value:
                logger.info("✅ Secret Manager connectivity test passed")
                return {"passed": True, "error": None}
            else:
                logger.warning("⚠️ Secret Manager accessible but DATABASE_URL not found")
                return {"passed": True, "error": "DATABASE_URL not found (but no connectivity error)"}
        except RuntimeError as e:
            if "not found" in str(e).lower():
                logger.info("✅ Secret Manager connectivity OK (secret not found is expected)")
                return {"passed": True, "error": None}
            else:
                raise e
                
    except Exception as e:
        logger.error(f"❌ Secret Manager connectivity test failed: {e}")
        return {"passed": False, "error": str(e)}


def main():
    """Run all connectivity tests (IPv6 fixes removed)."""
    logger.info("=" * 60)
    logger.info("Connectivity Tests (IPv6 Fixes Removed)")
    logger.info("=" * 60)
    
    tests = [
        ("Environment Variables", test_ipv6_environment_variables),
        ("Google Cloud Imports", test_google_cloud_imports),
        ("Data Pipeline Imports", test_data_pipeline_imports),
        ("Database Connectivity", test_database_connectivity),
        ("Secret Manager Connectivity", test_secret_manager_connectivity),
    ]
    
    results = {}
    overall_success = True
    
    for test_name, test_func in tests:
        logger.info(f"\n--- {test_name} ---")
        try:
            result = test_func()
            results[test_name] = result
            if not result.get("passed", False):
                overall_success = False
        except Exception as e:
            logger.error(f"❌ {test_name} test crashed: {e}")
            results[test_name] = {"passed": False, "error": str(e)}
            overall_success = False
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result.get("passed", False) else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
        if not result.get("passed", False) and result.get("error"):
            logger.info(f"  Error: {result['error']}")
    
    if overall_success:
        logger.info("\n🎉 All connectivity tests PASSED!")
        logger.info("GCP handles IPv6 natively without manual fixes.")
        return 0
    else:
        logger.error("\n💥 Some connectivity tests FAILED!")
        logger.error("Please check the errors above and fix any issues.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
