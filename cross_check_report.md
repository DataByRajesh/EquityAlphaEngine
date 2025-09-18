# API and Streamlit App Cross-Check Report

## Overview
This report cross-checks the API endpoints in `web/api.py` with their usage in `streamlit_app.py` to ensure consistency, completeness, and identify any potential issues.

## API Endpoints Summary
Total API endpoints: 20

### GET Endpoints
1. `/health` - Health check with database connectivity test
2. `/` - Root endpoint returning HTML welcome message
3. `/get_undervalued_stocks` - Returns undervalued stocks based on factor_composite ASC
4. `/get_overvalued_stocks` - Returns overvalued stocks based on factor_composite DESC
5. `/get_high_quality_stocks` - Returns high quality stocks based on norm_quality_score DESC
6. `/get_high_earnings_yield_stocks` - Returns stocks with high earnings yield
7. `/get_top_market_cap_stocks` - Returns top market cap stocks
8. `/get_low_beta_stocks` - Returns low beta stocks
9. `/get_high_dividend_yield_stocks` - Returns high dividend yield stocks
10. `/get_high_momentum_stocks` - Returns high momentum stocks (12m return)
11. `/get_low_volatility_stocks` - Returns low volatility stocks (21d vol)
12. `/get_top_short_term_momentum_stocks` - Returns short-term momentum stocks (3m return)
13. `/get_high_dividend_low_beta_stocks` - Returns stocks with high dividend and low beta
14. `/get_top_factor_composite_stocks` - Returns top factor composite stocks
15. `/get_high_risk_stocks` - Returns high risk stocks (252d vol DESC)
16. `/get_top_combined_screen_limited` - Returns combined screener results
17. `/get_macro_data` - Returns macroeconomic data
18. `/get_unique_sectors` - Returns list of unique sectors

### POST Endpoints
19. `/compute-factors` - Computes financial factors for provided dataset

## Streamlit App Usage Analysis

### Used Endpoints (16/20)
All GET endpoints except `/health` and `/` are used in the Streamlit app.

### Mapping to Tabs
1. **Undervalued Stocks** → `/get_undervalued_stocks`
2. **Overvalued Stocks** → `/get_overvalued_stocks`
3. **High Quality Stocks** → `/get_high_quality_stocks`
4. **High Earnings Yield** → `/get_high_earnings_yield_stocks`
5. **Top Market Cap Stocks** → `/get_top_market_cap_stocks`
6. **Low Beta Stocks** → `/get_low_beta_stocks`
7. **High Dividend Yield** → `/get_high_dividend_yield_stocks`
8. **High Momentum Stocks** → `/get_high_momentum_stocks`
9. **Low Volatility Stocks** → `/get_low_volatility_stocks`
10. **Short-Term Momentum** → `/get_top_short_term_momentum_stocks`
11. **High Dividend & Low Beta** → `/get_high_dividend_low_beta_stocks`
12. **Top Factor Composite** → `/get_top_factor_composite_stocks`
13. **High Risk Stocks** → `/get_high_risk_stocks`
14. **Top Combined Screener** → `/get_top_combined_screen_limited`
15. **Macro Data Visualization** → `/get_macro_data`
16. **Sector Filter** → `/get_unique_sectors`

### Unused Endpoints
1. `/health` - Not used in Streamlit app
2. `/` - Root HTML endpoint, not used
3. `/compute-factors` - POST endpoint, requires data input UI

## Parameter Consistency Check

### Common Parameters
All stock-related endpoints use consistent parameters:
- `min_mktcap` (int, default 0)
- `top_n` (int, default 10, max 100)
- `company` (str, optional)
- `sector` (str, optional)

### Validation
- Streamlit enforces `top_n` between 5-50
- API validates `top_n` between 1-100
- Both handle sector validation against available sectors
- Company name filtering uses LIKE queries
- Input sanitization prevents SQL injection

## Data Handling Consistency

### API Response Format
- All endpoints return JSON arrays of objects
- NaN values converted to null
- Consistent field naming (e.g., "close_price" → "Close")

### Streamlit Processing
- Converts JSON to pandas DataFrame
- Formats marketCap (B/M formatting)
- Handles empty responses gracefully
- Provides CSV download functionality

## Error Handling

### API Error Handling
- Database connection retries with exponential backoff
- HTTP status codes: 400 (validation), 503 (unavailable), 500 (server error)
- Comprehensive logging

### Streamlit Error Handling
- Timeout handling (30s)
- Connection error handling
- Status code specific messages
- Graceful degradation (fallback sector list)

## Caching Strategy

### API Caching
- In-memory cache with 10-minute TTL
- Thread-safe with locks
- Cache keys include all parameters

### Streamlit Caching
- Relies on API caching
- No additional client-side caching

## Potential Issues and Recommendations

### Unused Endpoints
1. **`/health`** - Consider adding a status indicator in Streamlit sidebar
2. **`/compute-factors`** - Could add a new tab for factor computation with file upload
3. **`/`** - Not applicable for Streamlit integration

### Minor Inconsistencies
1. **top_n limits**: API allows 1-100, Streamlit 5-50 - consider aligning
2. **Sector validation**: API validates against DB, Streamlit has fallback list

### Fixed Issues
1. **Import Error**: Streamlit app was missing import for `get_db` from `data_pipeline.db_connection` - **FIXED** by adding the import statement

### Runtime Considerations
1. **API Availability**: Streamlit app requires the API server to be running (default localhost:8000 in development). Connection errors occur if API is unavailable, but graceful fallbacks are implemented (e.g., default sector list).
2. **JSON Parsing Errors**: If API returns non-JSON responses (e.g., HTML error pages), the app catches JSONDecodeError and falls back to default values.

### Performance Considerations
- API has connection pooling (size 10, overflow 20)
- Query timeouts set to 30 seconds
- Consider adding rate limiting for production

## Conclusion
The API and Streamlit app are well-aligned with consistent parameter usage and error handling. 16 out of 20 endpoints are actively used, with the unused ones being utility/health endpoints that don't require UI integration. The integration is robust with proper error handling and data formatting.

**Status: ✅ Cross-check complete - No critical issues found**
