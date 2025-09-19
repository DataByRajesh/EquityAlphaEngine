#!/usr/bin/env python3
"""
Script to run the Streamlit Equity Alpha Engine dashboard locally.
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Run the Streamlit application."""
    # Get the directory of this script
    script_dir = Path(__file__).parent

    # Change to the script directory
    os.chdir(script_dir)

    # Set environment variables for local development
    env = os.environ.copy()
    env['ENVIRONMENT'] = 'development'

    # Run streamlit
    cmd = [
        sys.executable, '-m', 'streamlit', 'run',
        'streamlit_app.py',
        '--server.port=8501',
        '--server.address=0.0.0.0'
    ]

    print("Starting Streamlit Equity Alpha Engine Dashboard...")
    print(f"Command: {' '.join(cmd)}")
    print("Open your browser to http://localhost:8501")

    try:
        subprocess.run(cmd, env=env, check=True)
    except KeyboardInterrupt:
        print("\nStreamlit server stopped.")
    except subprocess.CalledProcessError as e:
        print(f"Error running streamlit: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
