# TODO: Equity Alpha Engine Pending Tasks

## 1. Add CSV Download to All Stock Screener Tabs
- [ ] Add CSV download button to "Undervalued Stocks" tab
- [ ] Add CSV download button to "Overvalued Stocks" tab
- [ ] Add CSV download button to "High Quality Stocks" tab
- [ ] Add CSV download button to "High Earnings Yield" tab
- [ ] Add CSV download button to "Top Market Cap Stocks" tab
- [ ] Add CSV download button to "Low Beta Stocks" tab
- [ ] Add CSV download button to "High Dividend Yield" tab
- [ ] Add CSV download button to "High Momentum Stocks" tab
- [ ] Add CSV download button to "Low Volatility Stocks" tab
- [ ] Add CSV download button to "Short-Term Momentum" tab
- [ ] Add CSV download button to "High Dividend & Low Beta" tab
- [ ] Add CSV download button to "Top Factor Composite" tab
- [ ] Add CSV download button to "High Risk Stocks" tab
- [ ] Verify "Top Combined Screener" CSV download still works

## 2. Add Macro Data Visualization Tab
- [ ] Add new "Macro Data Visualization" tab to streamlit_app.py
- [ ] Add API endpoint for macro data in web/api.py
- [ ] Implement charts for GDP growth and inflation in the new tab

## 3. Add Company Filtering Support
- [ ] Add optional company parameter to all stock screener API endpoints
- [ ] Update SQL queries to filter by company name when provided
- [ ] Update streamlit_app.py to include company filter input

## 4. Handle None Values in Price Columns
- [ ] Update SQL queries to use COALESCE for price columns (Open, High, Low, Close, Adj Close)
- [ ] Ensure UI can display data without None-related errors

## 5. Testing and Validation
- [ ] Test Streamlit app locally
- [ ] Verify all CSV downloads work
- [ ] Test macro data visualization
- [ ] Test company filtering functionality
- [ ] Check for None value display issues
