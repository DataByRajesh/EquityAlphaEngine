
import json
import os
import logging
from datetime import datetime, timedelta

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError, EndpointConnectionError
    from botocore.config import Config as BotoConfig
except ImportError:  # pragma: no cover - boto3 may not be installed in all environments
    boto3 = None
    BotoCoreError = ClientError = EndpointConnectionError = Exception
    BotoConfig = None

import config


S3_BUCKET = config.CACHE_BUCKET
CACHE_FILE_KEY = "fundamentals_cache.json"

if S3_BUCKET and boto3:
    boto_cfg = BotoConfig(retries={"max_attempts": 3}, connect_timeout=5, read_timeout=5) if BotoConfig else None
    s3_client = boto3.client("s3", config=boto_cfg) if boto_cfg else boto3.client("s3")
else:
    s3_client = None

# In-memory fallback when no S3 client is available
_LOCAL_CACHE: dict[str, dict] = {}


def load_cache_file():
    if not s3_client:
        return _LOCAL_CACHE
    try:
        obj = s3_client.get_object(Bucket=S3_BUCKET, Key=CACHE_FILE_KEY)
        return json.loads(obj["Body"].read())
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") == "NoSuchKey":
            return {}
        logging.warning(f"Failed to load cache file from S3: {e}")
    except (BotoCoreError, EndpointConnectionError, Exception) as e:
        logging.warning(f"Failed to load cache file from S3: {e}")
    return {}

def save_fundamentals_cache(ticker, data):
    cache = load_cache_file()
    cache[ticker] = {
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    }
    if not s3_client:
        return
    try:
        s3_client.put_object(Bucket=S3_BUCKET, Key=CACHE_FILE_KEY, Body=json.dumps(cache, indent=4))
    except (BotoCoreError, ClientError, EndpointConnectionError, Exception) as e:
        logging.warning(f"Failed to save cache to S3 for {ticker}: {e}")

def load_cached_fundamentals(ticker, expiry_minutes=1440):
    cache = load_cache_file()
    if ticker in cache:
        cached_entry = cache[ticker]
        timestamp = datetime.fromisoformat(cached_entry['timestamp'])
        if datetime.utcnow() - timestamp < timedelta(minutes=expiry_minutes):
            return cached_entry['data']
        else:
            return None
    return None

def clear_cached_fundamentals(ticker):
    cache = load_cache_file()
    if ticker in cache:
        del cache[ticker]
        if not s3_client:
            return
        try:
            s3_client.put_object(Bucket=S3_BUCKET, Key=CACHE_FILE_KEY, Body=json.dumps(cache, indent=4))
        except (BotoCoreError, ClientError, EndpointConnectionError, Exception) as e:
            logging.warning(f"Failed to clear cache for {ticker}: {e}")

def clear_all_cache():
    if not s3_client:
        _LOCAL_CACHE.clear()
        return
    try:
        s3_client.delete_object(Bucket=S3_BUCKET, Key=CACHE_FILE_KEY)
    except (BotoCoreError, ClientError, EndpointConnectionError, Exception) as e:
        logging.warning(f"Failed to clear all cache: {e}")
