#!/bin/bash
# Wrapper script to update UK data for the last 10 years
set -e
cd "$(dirname "$0")"
python data_pipeline/update_financial_data.py --years 10
