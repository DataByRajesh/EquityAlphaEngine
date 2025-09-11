## Summary

This PR fixes critical DataFrame assignment errors in `compute_factors.py` that were causing workflow failures with the error: "Cannot set a DataFrame with multiple columns to the single column".

## Changes Made

### data_pipeline/compute_factors.py
- **Momentum calculations**: Replaced `transform()` with `apply().reset_index()` for pct_change operations to ensure Series output and avoid DataFrame assignment issues.
- **Volatility calculations**: Updated to use `apply().reset_index()` with `pct_change(fill_method=None).fillna(0.0).squeeze()`.
- **Moving Averages**: Changed to `apply().reset_index()` with `ta.trend.sma_indicator().fillna(0.0).squeeze()`.
- **RSI**: Updated to `apply().reset_index()` with `ta.momentum.rsi().fillna(0.0).squeeze()`.
- **Average Volume**: Changed to `apply().reset_index()` with `rolling().mean().fillna(0.0).squeeze()`.
- **MACD and Bollinger Bands**: Already using `apply().reset_index()`, no changes needed.
- **Amihud Illiquidity**: Updated pct_change to use `fill_method=None`.

### data_pipeline/config.py
- Set default value for `CACHE_GCS_BUCKET` to `"equity-alpha-engine-cache"` to resolve warnings when the environment variable is not set.

### data_pipeline/cache_utils.py
- Added GCS bucket existence check with fallback to in-memory cache.

## Technical Details
- Used `apply().reset_index(level=0, drop=True)` to ensure Series output aligned with original DataFrame index.
- Added `fill_method=None` to `pct_change()` to comply with pandas deprecation warnings.
- Added `.fillna(0.0)` and `.squeeze()` to handle NaN values and ensure Series output.
- Ensured all groupby operations return Series compatible with DataFrame column assignment.

## Testing
- Verified that pct_change operations no longer raise DataFrame assignment errors.
- Confirmed CACHE_GCS_BUCKET default resolves environment variable warnings.
- All changes maintain backward compatibility with existing data structures.

## Related Issues
- Resolves workflow failures in update-data.yml due to pct_change DataFrame errors.
- Addresses pandas deprecation warnings for fill_method parameter.
- Fixes GCS bucket 404 errors with graceful fallback.
