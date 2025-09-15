# TODO: Fix Data Pipeline Errors

## Tasks
- [x] Fix pandas FutureWarning in Macro_data.py: change freq="Y" to "YE"
- [x] Add mock GDP data fallback in Macro_data.py fetch_gdp_growth on Quandl failure
- [x] Make Gmail notification optional in market_data.py: continue pipeline without exiting if credentials missing
