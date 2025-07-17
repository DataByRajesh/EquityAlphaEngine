import sqlite3
import pandas as pd

import logging
def analyze_db(path):

DB_PATH = "data_pipeline/data/stocks_data.db"
conn = sqlite3.connect(DB_PATH)

# Load a sample of the data
df = pd.read_sql("SELECT * FROM stock_data", conn)

# General stats
print(df.info())
print(f'describe {df.describe()}')

# Check for missing data
print(f' Missing data count {df.isnull().sum()}')

# Check for duplicates
print(f'duplicates data count {df.duplicated(subset=['Date', 'Ticker']).sum()}')

# Check data coverage per ticker
print(f'data coverage per ticker {df['Ticker'].value_counts()}')

# Spot-check for outliers
print(df[['Close', 'Volume', 'marketCap']].describe(),end='\n\n')

conn.close()
