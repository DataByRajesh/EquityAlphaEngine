#!/bin/bash
# Script to run the Streamlit Equity Alpha Engine dashboard locally

set -e

echo "Starting Streamlit Equity Alpha Engine Dashboard..."
echo "Open your browser to http://localhost:8501"

# Set environment variable for local development
export ENVIRONMENT=development

# Run streamlit
streamlit run streamlit_app.py --server.port=8501 --server.address=0.0.0.0
