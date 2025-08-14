"""Utilities for caching fundamental data with an in-memory layer.

The caching layer supports multiple backends controlled by
``config.CACHE_BACKEND``:

* ``local`` – each ticker stored as a JSON file under ``CACHE_DIR``.
* ``redis`` – Redis hash referenced by ``CACHE_REDIS_URL``.
* ``s3`` – Amazon S3 bucket defined by ``CACHE_S3_BUCKET``.

Entries are kept in an in-memory dictionary for the duration of the session
and only modified tickers are persisted back to the backing store. Remote
backends may raise exceptions (e.g. connection errors). Callers are expected
to handle such failures gracefully.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from typing import Dict, Optional

from . import config

# In-memory cache for this process
_CACHE: Dict[str, Dict] = {}

# ---------------------------------------------------------------------------
# Backend clients
# ---------------------------------------------------------------------------
if config.CACHE_BACKEND == "redis":
    import redis  # type: ignore

    _client = redis.Redis.from_url(config.CACHE_REDIS_URL)
    _key = "fundamentals_cache"  # Redis hash name
elif config.CACHE_BACKEND == "s3":
    import boto3  # type: ignore

    _client = boto3.client("s3")
    _prefix = (
        os.path.join(config.CACHE_S3_PREFIX, "fundamentals_cache")
        if config.CACHE_S3_PREFIX
        else "fundamentals_cache"
    )
else:  # local file backend
    _client = None
    _prefix = config.CACHE_DIR


def _redis_key(ticker: str) -> str:
    return ticker


def _s3_key(ticker: str) -> str:
    return f"{_prefix}/{ticker}.json" if _prefix else f"{ticker}.json"


def _local_path(ticker: str) -> str:
    return os.path.join(_prefix, f"{ticker}.json")


def _load_entry(ticker: str) -> Optional[Dict]:
    """Load ``ticker`` from the backing store into memory."""

    if ticker in _CACHE:
        return _CACHE[ticker]

    if config.CACHE_BACKEND == "redis":
        data = _client.hget(_key, _redis_key(ticker))
        if data:
            _CACHE[ticker] = json.loads(data)
            return _CACHE[ticker]
    elif config.CACHE_BACKEND == "s3":
        try:
            obj = _client.get_object(
                Bucket=config.CACHE_S3_BUCKET, Key=_s3_key(ticker)
            )
            _CACHE[ticker] = json.loads(obj["Body"].read().decode("utf-8"))
            return _CACHE[ticker]
        except _client.exceptions.NoSuchKey:
            return None
    else:  # local
        path = _local_path(ticker)
        if os.path.exists(path):
            with open(path, "r") as f:
                _CACHE[ticker] = json.load(f)
                return _CACHE[ticker]
    return None


def _persist_entry(ticker: str) -> None:
    """Persist a single ``ticker`` entry from memory to the backing store."""

    entry = _CACHE.get(ticker)
    if entry is None:
        return

    if config.CACHE_BACKEND == "redis":
        _client.hset(_key, _redis_key(ticker), json.dumps(entry))
    elif config.CACHE_BACKEND == "s3":
        _client.put_object(
            Bucket=config.CACHE_S3_BUCKET,
            Key=_s3_key(ticker),
            Body=json.dumps(entry).encode("utf-8"),
        )
    else:  # local
        path = _local_path(ticker)
        with open(path, "w") as f:
            json.dump(entry, f, indent=4)


def load_cached_fundamentals(
    ticker: str, expiry_minutes: int = config.CACHE_EXPIRY_MINUTES
):
    """Return cached fundamentals for ``ticker`` if present and fresh."""

    cached_entry = _load_entry(ticker)
    if cached_entry:
        timestamp = datetime.fromisoformat(cached_entry["timestamp"])
        if datetime.utcnow() - timestamp < timedelta(minutes=expiry_minutes):
            return cached_entry["data"]
    return None


def save_fundamentals_cache(ticker: str, data) -> None:
    """Store ``data`` for ``ticker`` in the cache and persist it."""

    _CACHE[ticker] = {"data": data, "timestamp": datetime.utcnow().isoformat()}
    _persist_entry(ticker)


def clear_cached_fundamentals(ticker: str) -> None:
    """Remove ``ticker`` from the cache and backing store if present."""

    _CACHE.pop(ticker, None)
    if config.CACHE_BACKEND == "redis":
        _client.hdel(_key, _redis_key(ticker))
    elif config.CACHE_BACKEND == "s3":
        try:
            _client.delete_object(Bucket=config.CACHE_S3_BUCKET, Key=_s3_key(ticker))
        except _client.exceptions.NoSuchKey:
            pass
    else:  # local
        path = _local_path(ticker)
        if os.path.exists(path):
            os.remove(path)


def clear_all_cache() -> None:
    """Clear the entire fundamentals cache."""

    _CACHE.clear()
    if config.CACHE_BACKEND == "redis":
        _client.delete(_key)
    elif config.CACHE_BACKEND == "s3":
        continuation_token = None
        kwargs = {
            "Bucket": config.CACHE_S3_BUCKET,
            "Prefix": _prefix,
        }
        while True:
            if continuation_token:
                kwargs["ContinuationToken"] = continuation_token
            resp = _client.list_objects_v2(**kwargs)
            for obj in resp.get("Contents", []):
                _client.delete_object(Bucket=config.CACHE_S3_BUCKET, Key=obj["Key"])
            if not resp.get("IsTruncated"):
                break
            continuation_token = resp.get("NextContinuationToken")
    else:  # local
        for filename in os.listdir(_prefix):
            if filename.endswith(".json"):
                try:
                    os.remove(os.path.join(_prefix, filename))
                except FileNotFoundError:
                    pass
