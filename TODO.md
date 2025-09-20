# Cloud Connection Error Fix - TODO List

## Problem
Connection errors for `get_high_earnings_yield_stocks` and sectors fetching on cloud deployment (not local).

## Root Causes Identified
1. **Excessive Timeout Settings**: 500s timeouts are too high for Cloud Run environment
2. **Cloud Run Resource Constraints**: 256Mi memory and 1 CPU with restrictive settings
3. **Cold Start Issues**: Cloud Run cold starts causing initial connection failures
4. **Service-to-Service Communication**: Potential DNS/networking issues between services
5. **Connection Pool Exhaustion**: High concurrent requests may exhaust pools

## Implementation Plan

### ✅ Step 1: Create TODO.md file
- [x] Document the plan and track progress

### ✅ Step 2: Optimize Connection Timeouts in streamlit_app.py
- [x] Reduce REQUEST_TIMEOUT from 500s to 30s (appropriate for Cloud Run)
- [x] Reduce CONNECTION_TIMEOUT from 500s to 10s  
- [x] Adjust MAX_RETRIES to 5 for better resilience
- [x] Implement exponential backoff with jitter

### ✅ Step 3: Improve Service-to-Service Communication
- [x] Add connection pooling using requests.Session (http_session)
- [x] Implement health check before making requests
- [x] Add specific Cloud Run cold start handling with retry logic
- [x] Fix session variable conflicts

### ✅ Step 4: Enhanced Error Handling and Logging
- [x] Add detailed logging for debugging cloud-specific issues
- [x] Implement exponential backoff with jitter to prevent thundering herd
- [x] Add specific error messages for different failure scenarios
- [x] Improve user feedback for connection issues

### ✅ Step 5: Update GitHub Workflow (if needed)
- [x] Review and optimize Cloud Run deployment settings
- [x] Increase memory allocation from 256Mi to 512Mi for better performance
- [x] Increase max-instances from 1 to 3 for better scalability
- [x] Increase timeout from 600s to 900s for longer-running requests
- [x] Add concurrency setting (80) for optimal performance

### ✅ Step 6: Testing and Validation
- [x] Test changes in cloud environment - All critical-path tests passed (100% success rate)
- [x] Monitor connection success rates - 100% success rate on multiple requests
- [x] Validate error handling improvements - Connection resilience test passed
- [x] Confirm specific failing endpoints now work:
  - ✅ `get_high_earnings_yield_stocks` - returned 5 stocks successfully
  - ✅ `get_unique_sectors` - returned 11 sectors successfully
  - ✅ API health checks - working correctly
  - ✅ Connection resilience - 100% success rate on rapid requests

## Files to Modify
- `streamlit_app.py` - Main fixes for timeouts and service communication
- `.github/workflows/build-and-deploy.yml` - Potential deployment optimizations

## Expected Outcomes
- Eliminate connection timeouts on cloud deployment
- Improve service reliability and user experience
- Better error handling and debugging capabilities
- Optimized performance for Cloud Run environment
