# Configuration for the data pipeline
# This file contains constants and settings used throughout the data pipeline.
#
# ---
# Google Cloud (GCP) Only:
# This configuration is designed for GCP services (Cloud SQL, Cloud Storage, Artifact Registry, etc.).
# No AWS services are supported or referenced.
#
# ---
# Google Cloud (GCP) Deployment:
# Set environment variables in your deployment (e.g., Cloud Run) using the
# --set-env-vars flag or the GCP console. Example:
#   gcloud run deploy SERVICE_NAME \
#     --image IMAGE_URI \
#     --set-env-vars "DATABASE_URL=your-db-url,CACHE_BACKEND=gcs,CACHE_GCS_BUCKET=your-bucket"
#
# If an environment variable is not set, a safe default is used for local development.


import logging
# Standard library imports
import os
import tempfile

# Third-party imports
from sqlalchemy import create_engine

try:
    from google.cloud import secretmanager
except ImportError:
    secretmanager = None

# ---------------------------------------------------------------------------
# Directory structure
#
# Directories can be overridden via the environment variables `DATA_DIR`,
# `CACHE_DIR` and `LOG_DIR`. On import we attempt to create each directory. If
# creation fails (e.g. running in a read-only environment), a temporary
# directory is used instead so the pipeline can still operate entirely in
# memory.
# ---------------------------------------------------------------------------


def _ensure_dir(env_var: str, default: str) -> str:
    """Return a directory path ensuring it exists.

    The directory is taken from the environment variable ``env_var`` when
    available. The path is created if missing. If the directory cannot be
    created, a temporary directory is returned instead.
    """
    path = os.path.abspath(os.environ.get(env_var, default))
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        path = tempfile.mkdtemp()
    return path


DATA_DIR = _ensure_dir("DATA_DIR", os.path.join("data_pipeline", "data"))
CACHE_DIR = _ensure_dir("CACHE_DIR", os.path.join("data_pipeline", "cache"))
LOG_DIR = _ensure_dir("LOG_DIR", os.path.join("data_pipeline", "logs"))


# PROJECT_ID = "your-gcp-project-id"
GCP_PROJECT_ID = "equity-alpha-engine-alerts"


# ---------------------------------------------------------------------------
# Database configuration
#
"""
Database configuration (GCP-first)

For GCP deployments, store DATABASE_URL as a GitHub repository secret.
Inject it into your CI/CD pipeline as an environment variable.
Example (GitHub Actions):
        - name: Deploy to Cloud Run
            run: |
                gcloud run deploy SERVICE_NAME \
                    --image IMAGE_URI \
                    --set-env-vars "DATABASE_URL=${{ secrets.DATABASE_URL }}"

If DATABASE_URL is not set, the application will raise an error and stop.
"""
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Gmail API configuration
#
"""
Gmail API configuration (GitHub Secrets for individuals)

Store your Gmail OAuth credentials file as a GitHub repository secret (e.g., GMAIL_CREDENTIALS_FILE).
Inject it into your CI/CD pipeline as an environment variable and write it to a file before running your app.
Example (GitHub Actions):
        - name: Write Gmail credentials
            run: |
                echo "${{ secrets.GMAIL_CREDENTIALS_FILE }}" > credentials.json
                export GMAIL_CREDENTIALS_FILE=credentials.json

Default path is used for local development if the environment variable is not set.
"""
GMAIL_CREDENTIALS_FILE = os.environ.get(
    "GMAIL_CREDENTIALS_FILE", "credentials.json")
GMAIL_TOKEN_FILE = os.environ.get("GMAIL_TOKEN_FILE", "token.json")


# ---------------------------------------------------------------------------
# Cache backend configuration (GCS-only)
#
# The cache system uses Google Cloud Storage. Set the bucket name via the
# environment variable ``CACHE_GCS_BUCKET``. Optionally, set a prefix via
# ``CACHE_GCS_PREFIX``.
# ---------------------------------------------------------------------------
CACHE_GCS_BUCKET = os.environ.get("CACHE_GCS_BUCKET")
CACHE_GCS_PREFIX = os.environ.get("CACHE_GCS_PREFIX", "")

# ---------------------------------------------------------------------------
# Configuration settings
# ---------------------------------------------------------------------------
MAX_RETRIES = 5  # Maximum retry attempts for fetching data
BACKOFF_FACTOR = 2  # Exponential backoff multiplier
INITIAL_DELAY = 1  # Initial delay (seconds) before retrying a failed request
# Delay (seconds) between API calls to avoid rate limits
RATE_LIMIT_DELAY = 1.5
# Concurrency for parallel API calls. Default scales with CPU cores but can be
# overridden via the ``MAX_THREADS`` environment variable.
MAX_THREADS = int(os.environ.get("MAX_THREADS", (os.cpu_count() or 1) * 5))
CACHE_EXPIRY_MINUTES = 1440  # Cache expiry time in minutes (24 hours)

# Yfinance configuration to prevent database lock issues
YF_DISABLE_CACHE = os.environ.get("YF_DISABLE_CACHE", "true").lower() == "true"
YF_CACHE_DIR = os.environ.get(
    "YF_CACHE_DIR", os.path.join(CACHE_DIR, "yfinance"))


# Logging configuration
"""
Logging configuration

Set the LOG_LEVEL environment variable to control log verbosity at runtime:
    LOG_LEVEL=DEBUG      # See detailed logs (debugging)
    LOG_LEVEL=INFO       # See informational logs (default)
    LOG_LEVEL=WARNING    # See only warnings and errors
    LOG_LEVEL=ERROR      # See only errors
    LOG_LEVEL=CRITICAL   # See only critical errors

You can set LOG_LEVEL in your shell, CI/CD, or GCP deployment (Cloud Run, etc).
If not set, defaults to INFO.
"""

# --- Logging helpers (formerly in logging_config.py) ---
VALID_LEVELS = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}


def level_from_env(default: str = "INFO") -> int:
    """
    Get logging level from LOG_LEVEL environment variable, fallback to default.
    Returns logging level constant (e.g., logging.INFO).
    """
    raw = os.environ.get("LOG_LEVEL", default).upper()
    if raw not in VALID_LEVELS:
        raw = default
    return getattr(logging, raw, logging.INFO)


def configure_logging(level: int = None) -> None:
    """
    Idempotently set up root logging for CLIs/jobs.
    - If handlers already exist, only adjusts levels.
    - If not, creates a simple StreamHandler with a useful format.
    """
    lvl = level if level is not None else level_from_env()
    root = logging.getLogger()
    if root.handlers:
        root.setLevel(lvl)
        return
    logging.basicConfig(
        level=lvl,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


LOG_LEVEL = level_from_env()
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
configure_logging(LOG_LEVEL)


def get_file_logger(name: str, filename: str = None):
    """Create and return a logger that writes to a file in LOG_DIR."""
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)
    log_file = os.path.join(LOG_DIR, filename or f"{name}.log")
    file_handler = logging.FileHandler(log_file)
    formatter = logging.Formatter(LOG_FORMAT)
    file_handler.setFormatter(formatter)
    # Avoid duplicate handlers
    if not any(
        isinstance(h, logging.FileHandler)
        and getattr(h, "baseFilename", None) == file_handler.baseFilename
        for h in logger.handlers
    ):
        logger.addHandler(file_handler)
    return logger


# FTSE 100 Tickers List (as config)
FTSE_100_TICKERS = [
    "III.L",
    "ADM.L",
    "AAF.L",
    "ALW.L",
    "AAL.L",
    "ANTO.L",
    "AHT.L",
    "ABF.L",
    "AZN.L",
    "AUTO.L",
    "AV.L",
    "BAB.L",
    "BA.L",
    "BARC.L",
    "BTRW.L",
    "BEZ.L",
    "BKG.L",
    "BP.L",
    "BATS.L",
    "BT-A.L",
    "BNZL.L",
    "CNA.L",
    "CCEP.L",
    "CCH.L",
    "CPG.L",
    "CTEC.L",
    "CRDA.L",
    "DCC.L",
    "DGE.L",
    "DPLM.L",
    "EDV.L",
    "ENT.L",
    "EZJ.L",
    "EXPN.L",
    "FCIT.L",
    "FRES.L",
    "GAW.L",
    "GLEN.L",
    "GSK.L",
    "HLN.L",
    "HLMA.L",
    "HIK.L",
    "HSX.L",
    "HWDN.L",
    "HSBA.L",
    "IHG.L",
    "IMI.L",
    "IMB.L",
    "INF.L",
    "ICG.L",
    "IAG.L",
    "ITRK.L",
    "JD.L",
    "KGF.L",
    "LAND.L",
    "LGEN.L",
    "LLOY.L",
    "LMP.L",
    "LSEG.L",
    "MNG.L",
    "MKS.L",
    "MRO.L",
    "MNDI.L",
    "NG.L",
    "NWG.L",
    "NXT.L",
    "PSON.L",
    "PSH.L",
    "PSN.L",
    "PHNX.L",
    "PCT.L",
    "PRU.L",
    "RKT.L",
    "REL.L",
    "RTO.L",
    "RMV.L",
    "RIO.L",
    "RR.L",
    "SGE.L",
    "SBRY.L",
    "SDR.L",
    "SMT.L",
    "SGRO.L",
    "SVT.L",
    "SHEL.L",
    "SMIN.L",
    "SN.L",
    "SPX.L",
    "SSE.L",
    "STAN.L",
    "STJ.L",
    "TW.L",
    "TSCO.L",
    "ULVR.L",
    "UU.L",
    "UTG.L",
    "VOD.L",
    "WEIR.L",
    "WTB.L",
    "WPP.L",
]
