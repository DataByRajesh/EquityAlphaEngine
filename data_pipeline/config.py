# Configuration for the data pipeline
# This file contains constants and settings used throughout the data pipeline.

# Importing necessary libraries
import os
import tempfile
import streamlit as st
from sqlalchemy import create_engine

# ---------------------------------------------------------------------------
# Directory structure
#
# Directories can be overridden via the environment variables `DATA_DIR`,
# `CACHE_DIR` and `LOG_DIR`.  On import we attempt to create each directory. If
# creation fails (e.g. running in a read-only environment), a temporary
# directory is used instead so the pipeline can still operate entirely in
# memory.
# ---------------------------------------------------------------------------


def _ensure_dir(env_var: str, default: str) -> str:
    """Return a directory path ensuring it exists.

    The directory is taken from the environment variable ``env_var`` when
    available. The path is created if missing.  If the directory cannot be
    created, a temporary directory is returned instead.
    """

    path = os.environ.get(env_var, default)
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        path = tempfile.mkdtemp()
    return path


DATA_DIR = _ensure_dir("DATA_DIR", os.path.join("data_pipeline", "data"))
CACHE_DIR = _ensure_dir("CACHE_DIR", os.path.join("data_pipeline", "cache"))
LOG_DIR = _ensure_dir("LOG_DIR", os.path.join("data_pipeline", "logs"))
DB_PATH = os.path.join(DATA_DIR, "stocks_data.db")  # Default SQLite database location

# Database configuration
# ``DATABASE_URL`` can point to any database supported by SQLAlchemy.  When not
# provided we fall back to a local SQLite file inside ``DATA_DIR``.
try:
    DATABASE_URL = st.secrets["DATABASE_URL"]
except Exception:
    DATABASE_URL = f"sqlite:///{DB_PATH}"
ENGINE = create_engine(DATABASE_URL)

# Cache backend configuration
#
# The cache system can be backed by different stores.  Set
# ``CACHE_BACKEND`` to one of:
#   * ``local`` – use a JSON file in ``CACHE_DIR`` (default)
#   * ``redis`` – use a Redis instance specified by ``CACHE_REDIS_URL``
#   * ``s3`` – use an S3 bucket specified by ``CACHE_S3_BUCKET``
CACHE_BACKEND = os.environ.get("CACHE_BACKEND", "local").lower()

# Redis configuration.  Only used when ``CACHE_BACKEND`` is ``redis``.
# Example: ``redis://localhost:6379/0``
CACHE_REDIS_URL = os.environ.get("CACHE_REDIS_URL", "redis://localhost:6379/0")

# S3 configuration.  Only used when ``CACHE_BACKEND`` is ``s3``.
# ``CACHE_S3_BUCKET`` is required, ``CACHE_S3_PREFIX`` is optional.
CACHE_S3_BUCKET = os.environ.get("CACHE_S3_BUCKET")
CACHE_S3_PREFIX = os.environ.get("CACHE_S3_PREFIX", "")

# Configuration settings
MAX_RETRIES = 5 # Maximum number of retry attempts for fetching data in case of failure
BACKOFF_FACTOR = 2 # Backoff multiplier to increase delay between retries exponentially
INITIAL_DELAY = 1  # Initial delay in seconds before retrying a failed request
RATE_LIMIT_DELAY = 1.5  # Delay in seconds between API calls to avoid hitting rate limits
MAX_THREADS = 5  # Maximum number of concurrent threads for parallelizing API calls
CACHE_EXPIRY_MINUTES = 1440  # Cache expiry time in minutes (default: 24 hours)

# Logging configuration
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"

# FTSE 100 Tickers List (as config)
FTSE_100_TICKERS = [
    "III.L", "ADM.L", "AAF.L", "ALW.L", "AAL.L", "ANTO.L", "AHT.L", "ABF.L", "AZN.L", "AUTO.L",
    "AV.L", "BAB.L", "BA.L", "BARC.L", "BTRW.L", "BEZ.L", "BKG.L", "BP.L", "BATS.L", "BT-A.L",
    "BNZL.L", "CNA.L", "CCEP.L", "CCH.L", "CPG.L", "CTEC.L", "CRDA.L", "DCC.L", "DGE.L", "DPLM.L",
    "EDV.L", "ENT.L", "EZJ.L", "EXPN.L", "FCIT.L", "FRES.L", "GAW.L", "GLEN.L", "GSK.L", "HLN.L",
    "HLMA.L", "HIK.L", "HSX.L", "HWDN.L", "HSBA.L", "IHG.L", "IMI.L", "IMB.L", "INF.L", "ICG.L",
    "IAG.L", "ITRK.L", "JD.L", "KGF.L", "LAND.L", "LGEN.L", "LLOY.L", "LMP.L", "LSEG.L", "MNG.L",
    "MKS.L", "MRO.L", "MNDI.L", "NG.L", "NWG.L", "NXT.L", "PSON.L", "PSH.L", "PSN.L", "PHNX.L",
    "PCT.L", "PRU.L", "RKT.L", "REL.L", "RTO.L", "RMV.L", "RIO.L", "RR.L", "SGE.L", "SBRY.L",
    "SDR.L", "SMT.L", "SGRO.L", "SVT.L", "SHEL.L", "SMIN.L", "SN.L", "SPX.L", "SSE.L", "STAN.L",
    "STJ.L", "TW.L", "TSCO.L", "ULVR.L", "UU.L", "UTG.L", "VOD.L", "WEIR.L", "WTB.L", "WPP.L"
]

# (other config constants)
