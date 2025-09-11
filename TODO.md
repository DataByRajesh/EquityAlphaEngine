# TODO: Fix Issues in Financial Data Update Pipeline

## Issues Identified from Logs
1. **Database Locked Error**: OperationalError('database is locked') during yfinance download for RIO.L.
2. **Cache Warnings**: CACHE_GCS_BUCKET not set, causing warnings for every ticker.
3. **Pandas Deprecation Warnings**: pct_change default fill_method deprecated.
4. **Multiple Data Population Triggers**: Pipeline runs multiple times due to empty table checks.
5. **Long Runtime**: Script runs for 19+ minutes before cancellation.

## Planned Fixes
- [x] Update pct_change calls in compute_factors.py to use fill_method=None
- [x] Modify cache_utils.py to handle missing CACHE_GCS_BUCKET gracefully (fallback to in-memory)
- [x] Add retry logic for database operations in db_utils.py
- [x] Prevent multiple data population triggers in db_utils.py
- [x] Optimize yfinance fetch in market_data.py with better error handling
- [x] Add timeout and progress tracking to prevent long runs
- [x] Fix yfinance "database is locked" error with cache management and retry logic

## Implementation Steps
1. Fix pct_change deprecation warnings
2. Improve cache handling for missing GCS bucket
3. Add database retry logic
4. Prevent duplicate data population
5. Enhance error handling in market data fetch
6. Test the fixes with a smaller dataset

## Bulk Insert Optimization
- [x] Increase default chunksize from 15000 to 50000 in insert_dataframe
- [x] Add detailed timing logs for each chunk in _chunked_insert
- [x] Implement copy_from method for non-upsert inserts
- [x] Fix temp table column assignment error
- [x] Fix pg8000 parameter limit issue by reducing chunksize to 900
- [x] Commit and push changes to test the pg8000 fix
- [x] Monitor logs for improved performance

## Performance Optimization and Debug Enhancement
- [x] Optimize yfinance fetch with cache management and retry logic
- [x] Add enhanced logging for database operations and yfinance calls
- [x] Implement process-specific cache directories to prevent conflicts
- [x] Add detailed timing logs for all major operations
- [x] Improve error handling with specific error types and recovery strategies
- [x] Create pull request for yfinance database lock fix
- [x] Fix Ticker column overwrite causing database insert errors
- [ ] Test optimized pipeline performance
- [ ] Monitor execution time improvements
