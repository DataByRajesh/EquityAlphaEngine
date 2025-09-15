# TODO: Database Connection Timeout Fix & Data Pipeline Errors

## Database Connection Timeout Fix

### Problem
API endpoints are experiencing database connection timeouts with `TimeoutError: [Errno 110] Connection timed out` errors.

### Root Causes
1. Each API request creates new DBHelper instances with separate connections
2. API endpoints not using the global connection pool properly
3. Inefficient connection management leading to timeouts
4. Missing retry logic for transient network failures

### Tasks to Complete

#### 1. Fix API Connection Management ✅
- [x] Update web/api.py to use global engine from db_connection.py
- [x] Remove individual DBHelper creation per request
- [x] Implement proper connection context management

#### 2. Improve Connection Pool Settings ✅
- [x] Update data_pipeline/db_connection.py with better pool settings
- [x] Add connection timeout and retry configurations
- [x] Optimize pool size and overflow settings

#### 3. Add Connection Retry Logic ✅
- [x] Implement retry logic in API endpoints for transient failures
- [x] Add exponential backoff for connection attempts
- [x] Better error handling and logging

#### 4. Optimize Database Queries ✅
- [x] Add query timeouts to prevent hanging connections
- [x] Update execute_query_with_retry function with better timeout handling
- [x] Implement connection health checks

#### 5. Testing and Validation ✅
- [ ] Test API endpoints after changes
- [ ] Monitor connection pool usage
- [ ] Verify timeout handling works properly

### Progress
- [x] Analysis completed
- [x] Implementation completed
- [ ] Testing pending
- [ ] Deployment pending

### Changes Made

#### 1. Database Connection Improvements (data_pipeline/db_connection.py)
- Increased pool size from 10 to 20 for better concurrent request handling
- Increased max overflow from 20 to 30 for peak load handling
- Added CONNECTION_TIMEOUT constant (30 seconds)
- Improved pool timeout to 60 seconds
- Added pool recycle every 30 minutes (1800 seconds)
- Implemented exponential backoff in retry logic

#### 2. API Connection Management (web/api.py)
- Replaced individual DBHelper instances with global engine usage
- Added execute_query_with_retry function with robust error handling
- Implemented proper exception handling for connection timeouts
- Added enhanced health check endpoint with database connectivity test
- Improved logging for better debugging
- Added caching with proper error handling

#### 3. Error Handling and Resilience
- Added specific exception handling for OperationalError, SQLTimeoutError, InterfaceError
- Implemented exponential backoff retry strategy
- Added proper HTTP status codes (503 for temporary unavailability)
- Enhanced logging with detailed error messages

## Data Pipeline Error Fixes

### Tasks
- [x] Fix pandas FutureWarning in Macro_data.py: change freq="Y" to "YE"
- [x] Add mock GDP data fallback in Macro_data.py fetch_gdp_growth on Quandl failure
- [x] Make Gmail notification optional in market_data.py: continue pipeline without exiting if credentials missing
