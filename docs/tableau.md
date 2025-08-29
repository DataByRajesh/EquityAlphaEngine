
# Tableau Public Integration Guide

This guide explains how to connect your EquityAlphaEngine pipeline output to Tableau Public for free, public dashboarding.

## Why Tableau Public?
- Free for public dashboards
- Easy to use, runs on Windows and Mac
- No software install required for viewing dashboards

## How to Connect Tableau Public to Your Pipeline

1. **Export Data to CSV:**
   - Your pipeline writes output to a CSV file (e.g., `financial_tbl.csv`, `macro_data_tbl.csv`).
   - Example Python code:
     ```python
     import pandas as pd
     from sqlalchemy import create_engine
     engine = create_engine(DATABASE_URL)
     df = pd.read_sql("SELECT * FROM financial_tbl", engine)
     df.to_csv("financial_tbl.csv", index=False)
     ```

2. **Upload CSV to Tableau Public:**
   - Go to [Tableau Public](https://public.tableau.com/)
   - Click 'Create a Viz' and upload your CSV file
   - Build charts and dashboards using your data

3. **Update Data:**
   - To refresh your dashboard, export a new CSV and re-upload to Tableau Public

## Notes
- Tableau Public does not support live connections or scheduled refresh from cloud databases
- All dashboards are public and discoverable online
# Export macro data to CSV
psql $DATABASE_URL -c "\\COPY (SELECT * FROM macro_data) TO 'macro_data.csv' WITH CSV HEADER"
```

These CSV files can then be imported into Tableau if a direct database connection is not available.

