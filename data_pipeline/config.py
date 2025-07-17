# Configuration for the data pipeline
# This file contains constants and settings used throughout the data pipeline.

# Importing necessary libraries
import os

# Directory structure
DATA_DIR = os.path.join("data_pipeline", "data") # Directory for storing data files
DB_PATH = os.path.join(DATA_DIR, "stocks_data.db") # Path to the SQLite database
CACHE_DIR = os.path.join("data_pipeline", "cache") # Directory for caching data
LOG_DIR = os.path.join("data_pipeline", "logs") # Directory for log files

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
