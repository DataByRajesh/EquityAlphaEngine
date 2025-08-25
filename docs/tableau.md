# Tableau Integration Guide

This guide explains how to connect Tableau to the EquityAlphaEngine database.

## Prerequisites

- Access to the PostgreSQL database used by the data pipeline.
- Tableau Desktop or Tableau Server with the PostgreSQL driver installed.
- Connection details such as host, port, database name, username, and password.

## Connecting Tableau

1. Retrieve the connection information from your environment or `.env` file. It
   follows the pattern: `postgresql://user:password@host:5432/database`.
2. In Tableau, choose **Connect → PostgreSQL**.
3. Enter the host, port, database, username, and password.
4. After connecting, select the desired schema and drag tables like
   `stock_data` or `macro_data` onto the canvas to begin building views.

## Sample SQL queries

```sql
-- Recent close prices
SELECT symbol, date, close
FROM stock_data
ORDER BY date DESC
LIMIT 100;

-- Macroeconomic indicator example
SELECT indicator, date, value
FROM macro_data
WHERE indicator = 'GDP'
ORDER BY date DESC;
```

## Exporting tables to CSV

```bash
# Export stock data to CSV
psql $DATABASE_URL -c "\\COPY (SELECT * FROM stock_data) TO 'stock_data.csv' WITH CSV HEADER"

# Export macro data to CSV
psql $DATABASE_URL -c "\\COPY (SELECT * FROM macro_data) TO 'macro_data.csv' WITH CSV HEADER"
```

These CSV files can then be imported into Tableau if a direct database connection is not available.

