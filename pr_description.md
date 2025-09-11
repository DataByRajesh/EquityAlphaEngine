## Summary

This PR fixes critical DataFrame assignment errors in `compute_factors.py` that were causing workflow failures with the error: "Cannot set a DataFrame with multiple columns to the single column".

## Changes Made

### data_pipeline/compute_factors.py
- **Momentum calculations**: Replaced `apply().reset_index()` with `transform()` for pct_change operations to avoid DataFrame assignment issues.
- **Volatility calculations**: Updated to use `transform()` with `pct_change(fill_method=None).fillna(0.0)`.
- **Moving Averages**: Changed to `transform()` with `ta.trend.sma_indicator().fillna(0.0)`.
- **RSI**: Updated to `transform()` with `ta.momentum.rsi().fillna(0.0)`.
- **MACD**: Modified `_macd` function to work with full series instead of `x.iloc[:, 0]`.
- **Bollinger Bands**: Updated `_bb` function similarly.
- **Average Volume**: Changed to `transform()` with `rolling().mean().fillna(0.0)`.
- **Amihud Illiquidity**: Updated pct_change to use `fill_method=None`.

### data_pipeline/config.py
- Set default value for `CACHE_GCS_BUCKET` to `"equity-alpha-engine-cache"` to resolve warnings when the environment variable is not set.

## Technical Details
- Used `transform()` instead of `apply()` to maintain Series output for single-column assignments.
- Added `fill_method=None` to `pct_change()` to comply with pandas deprecation warnings.
- Added `.fillna(0.0)` to handle NaN values consistently.
- Ensured all groupby operations return Series compatible with DataFrame column assignment.

## Testing
- Verified that pct_change operations no longer raise DataFrame assignment errors.
- Confirmed CACHE_GCS_BUCKET default resolves environment variable warnings.
- All changes maintain backward compatibility with existing data structures.

## Related Issues
- Resolves workflow failures in update-data.yml due to pct_change DataFrame errors.
- Addresses pandas deprecation warnings for fill_method parameter.
