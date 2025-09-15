#!/usr/bin/env python3
"""
Start the API server for testing.
"""

import sys
sys.path.append('.')
from web.api import app
import uvicorn

if __name__ == "__main__":
    print("Starting API server on http://127.0.0.1:8000")
    uvicorn.run(app, host='127.0.0.1', port=8000, log_level='info')
