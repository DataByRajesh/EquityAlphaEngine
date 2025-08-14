"""Utilities for caching fundamental data.

The caching layer supports multiple backends controlled by
``config.CACHE_BACKEND``:

* ``local`` – JSON file stored under ``CACHE_DIR``.
* ``redis`` – Redis instance referenced by ``CACHE_REDIS_URL``.
* ``s3`` – Amazon S3 bucket defined by ``CACHE_S3_BUCKET``.

Remote backends may raise exceptions (e.g. connection errors).  Callers are
expected to handle such failures gracefully.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict

import config


CACHE_FILE = os.path.join(config.CACHE_DIR, "fundamentals_cache.json")

# ---------------------------------------------------------------------------
# Backend clients
# ---------------------------------------------------------------------------
if config.CACHE_BACKEND == "redis":
    import redis  # type: ignore

    _client = redis.Redis.from_url(config.CACHE_REDIS_URL)
    _key = "fundamentals_cache"
elif config.CACHE_BACKEND == "s3":
    import boto3  # type: ignore

    _client = boto3.client("s3")
    _key = (
        os.path.join(config.CACHE_S3_PREFIX, "fundamentals_cache.json")
        if config.CACHE_S3_PREFIX
        else "fundamentals_cache.json"
    )
else:  # local file backend
    _client = None
    _key = CACHE_FILE


def _load_cache() -> Dict:
    """Load the full cache from the configured backend."""

    if config.CACHE_BACKEND == "redis":
        data = _client.get(_key)
        return json.loads(data) if data else {}
    if config.CACHE_BACKEND == "s3":
        try:
            obj = _client.get_object(Bucket=config.CACHE_S3_BUCKET, Key=_key)
            return json.loads(obj["Body"].read().decode("utf-8"))
        except _client.exceptions.NoSuchKey:
            return {}
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}


def _save_cache(cache: Dict) -> None:
    """Persist the full cache to the configured backend."""

    if config.CACHE_BACKEND == "redis":
        _client.set(_key, json.dumps(cache))
    elif config.CACHE_BACKEND == "s3":
        _client.put_object(
            Bucket=config.CACHE_S3_BUCKET,
            Key=_key,
            Body=json.dumps(cache).encode("utf-8"),
        )
    else:
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f, indent=4)


def load_cached_fundamentals(ticker: str, expiry_minutes: int = config.CACHE_EXPIRY_MINUTES):
    """Return cached fundamentals for ``ticker`` if present and fresh."""

    cache = _load_cache()
    cached_entry = cache.get(ticker)
    if cached_entry:
        timestamp = datetime.fromisoformat(cached_entry["timestamp"])
        if datetime.utcnow() - timestamp < timedelta(minutes=expiry_minutes):
            return cached_entry["data"]
    return None


def save_fundamentals_cache(ticker: str, data) -> None:
    """Store ``data`` for ``ticker`` in the cache."""

    cache = _load_cache()
    cache[ticker] = {"data": data, "timestamp": datetime.utcnow().isoformat()}
    _save_cache(cache)


def clear_cached_fundamentals(ticker: str) -> None:
    """Remove ``ticker`` from the cache if present."""

    cache = _load_cache()
    if ticker in cache:
        del cache[ticker]
        _save_cache(cache)


def clear_all_cache() -> None:
    """Clear the entire fundamentals cache."""

    if config.CACHE_BACKEND == "redis":
        _client.delete(_key)
    elif config.CACHE_BACKEND == "s3":
        _client.delete_object(Bucket=config.CACHE_S3_BUCKET, Key=_key)
    else:
        if os.path.exists(CACHE_FILE):
            os.remove(CACHE_FILE)

