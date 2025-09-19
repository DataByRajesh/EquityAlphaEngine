# Equity Alpha Engine - Bug Fixes TODO

## Issues to Fix

### 1. Stock Categorization Issue ✅
- [x] Fix inconsistent `require_ohlcv` parameter usage across API endpoints
- [x] Make OHLCV filtering optional for all endpoints
- [x] Ensure proper data filtering logic

### 2. Filter Functionality Issue ✅
- [x] Standardize sector filter logic across all Streamlit tabs
- [x] Fix inconsistent "All" vs specific sector handling
- [x] Ensure all tabs apply filters consistently

### 3. Gmail Failure Handling ✅
- [x] Improve error logging in `send_message` function
- [x] Add better exception handling in main pipeline
- [x] Provide detailed failure information for debugging

### 4. LSE Market Cap Currency Issue ✅
- [x] Add currency field for market cap values
- [x] Document LSE stocks (.L suffix) use GBP currency
- [x] Add currency indicator in API responses

### 5. Macro Data API Failure Issue ✅
- [x] Improve error handling for Quandl API 403 errors
- [x] Add specific error messages for different failure types
- [x] Enhanced fallback to mock data with better logging
- [x] Create more realistic mock GDP data with variation

### 6. GCP ALTS Credentials Warning ✅
- [x] Suppress harmless ALTS credentials warning when not running on GCP
- [x] Add targeted warning filter for cleaner log output
- [x] Maintain compatibility with both GCP and local environments

### 7. Enhanced OAuth and Service Account Integration ✅
- [x] Enable proper OAuth token storage and retrieval from Secret Manager
- [x] Add automatic OAuth token refresh and re-saving to Secret Manager
- [x] Improve Service Account authentication with Secret Manager integration
- [x] Add comprehensive logging for authentication flow debugging
- [x] Support both local file and Secret Manager token storage

## Files Modified
- `web/api.py` - API endpoint fixes and currency handling
- `streamlit_app.py` - Filter logic standardization
- `data_pipeline/gmail_utils.py` - Enhanced error handling, warning suppression, and Secret Manager integration
- `data_pipeline/market_data.py` - Better email failure handling
- `data_pipeline/Macro_data.py` - Enhanced Quandl API error handling

## Summary of Changes Made

### 1. API Endpoints (`web/api.py`)
- ✅ Added optional `require_ohlcv` parameter to all stock endpoints
- ✅ Made OHLCV filtering consistent across all endpoints
- ✅ Added `marketCapCurrency` field to all API responses
- ✅ LSE stocks (.L suffix) now show "GBP", others show "USD"
- ✅ Updated cache keys to include `require_ohlcv` parameter

### 2. Streamlit App (`streamlit_app.py`)
- ✅ Standardized sector filter logic: all tabs now use `if sector_filter != "All"`
- ✅ Fixed inconsistent filter application across tabs
- ✅ Ensured all tabs properly handle the "All" sector option

### 3. Gmail Error Handling (`data_pipeline/gmail_utils.py`)
- ✅ Enhanced `send_message` function with detailed error logging
- ✅ Added specific error type detection (authentication, quota, permissions, network)
- ✅ Improved return value handling and validation
- ✅ Added input validation for service and message parameters

### 4. Pipeline Email Handling (`data_pipeline/market_data.py`)
- ✅ Enhanced email notification error handling with specific error types
- ✅ Added detailed logging for different failure scenarios
- ✅ Improved email body with pipeline execution details
- ✅ Better error messages for debugging Gmail issues

## Issues Resolved

1. **Stock categorization**: All endpoints now have consistent OHLCV filtering options
2. **Filter functionality**: Streamlit filters now work consistently across all tabs
3. **Gmail failures**: Detailed error logging helps identify specific failure causes
4. **LSE currency**: Market cap values now include currency information (GBP for .L stocks)

## Testing Required
- [ ] Test all API endpoints return data with new `require_ohlcv` parameter
- [ ] Test Streamlit filter functionality across all tabs
- [ ] Test email notification system with various failure scenarios
- [ ] Verify currency handling for LSE stocks shows "GBP"
- [ ] Verify non-LSE stocks show "USD" currency
