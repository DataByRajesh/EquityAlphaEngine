"""Utilities for caching fundamental data with an in-memory layer.

The caching layer supports multiple backends controlled by
``config.CACHE_BACKEND``:

* ``local`` – each ticker stored as a JSON file under ``CACHE_DIR``.
* ``redis`` – Redis hash referenced by ``CACHE_REDIS_URL``.
* ``gcs`` – Google Cloud Storage bucket defined by ``CACHE_GCS_BUCKET``.

Entries are kept in an in-memory dictionary for the duration of the session
and only modified tickers are persisted back to the backing store. Remote
backends may raise exceptions (e.g. connection errors). Callers are expected
to handle such failures gracefully.
"""

from __future__ import annotations

import json
import os
import logging
from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Optional

from . import config

# In-memory cache for this process
_CACHE: Dict[str, Dict] = {}
_CACHE_LOCK = Lock()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Backend clients
# ---------------------------------------------------------------------------
if config.CACHE_BACKEND == "redis":
    try:
        import redis  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "Redis backend selected but the 'redis' package is not installed. "
            "Install it with 'pip install redis'."
        ) from exc

    _client = redis.Redis.from_url(config.CACHE_REDIS_URL)
    _key = "fundamentals_cache"  # Redis hash name
elif config.CACHE_BACKEND == "gcs":
    try:
        from google.cloud import storage  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "GCS backend selected but the 'google-cloud-storage' package is not installed. "
            "Install it with 'pip install google-cloud-storage'."
        ) from exc

    _client = storage.Client()
    _bucket = _client.bucket(config.CACHE_GCS_BUCKET)
    _prefix = (
        os.path.join(config.CACHE_GCS_PREFIX, "fundamentals_cache")
        if config.CACHE_GCS_PREFIX
        else "fundamentals_cache"
    )
else:  # local file backend
    _client = None
    _prefix = config.CACHE_DIR


def _redis_key(ticker: str) -> str:
    return ticker


def _gcs_blob_name(ticker: str) -> str:
    return f"{_prefix}/{ticker}.json" if _prefix else f"{ticker}.json"


def _local_path(ticker: str) -> str:
    return os.path.join(_prefix, f"{ticker}.json")


def _load_entry(ticker: str) -> Optional[Dict]:
    """Load ``ticker`` from the backing store into memory."""

    with _CACHE_LOCK:
        if ticker in _CACHE:
            return _CACHE[ticker]

    if config.CACHE_BACKEND == "redis":
        try:
            data = _client.hget(_key, _redis_key(ticker))
        except Exception as e:  # pragma: no cover - network failure
            logger.warning("Failed to load %s from Redis: %s", ticker, e)
            return None
        if data:
            value = json.loads(data)
            with _CACHE_LOCK:
                _CACHE[ticker] = value
                return _CACHE[ticker]
    elif config.CACHE_BACKEND == "gcs":
        from google.api_core.exceptions import NotFound

        blob = _bucket.blob(_gcs_blob_name(ticker))
        try:
            data = blob.download_as_text()
        except NotFound:
            return None
        except Exception as e:  # pragma: no cover - network failure
            logger.warning("Failed to load %s from Cloud Storage: %s", ticker, e)
            return None
        value = json.loads(data)
        with _CACHE_LOCK:
            _CACHE[ticker] = value
            return _CACHE[ticker]
    else:  # local
        path = _local_path(ticker)
        if os.path.exists(path):
            with open(path, "r") as f:
                value = json.load(f)
            with _CACHE_LOCK:
                _CACHE[ticker] = value
                return _CACHE[ticker]
    return None


def _persist_entry(ticker: str) -> None:
    """Persist a single ``ticker`` entry from memory to the backing store."""

    with _CACHE_LOCK:
        entry = _CACHE.get(ticker)
    if entry is None:
        return

    if config.CACHE_BACKEND == "redis":
        try:
            _client.hset(_key, _redis_key(ticker), json.dumps(entry))
        except Exception as e:  # pragma: no cover - network failure
            logger.warning("Failed to persist %s to Redis: %s", ticker, e)
    elif config.CACHE_BACKEND == "gcs":
        blob = _bucket.blob(_gcs_blob_name(ticker))
        try:
            blob.upload_from_string(json.dumps(entry))
        except Exception as e:  # pragma: no cover - network failure
            logger.warning("Failed to persist %s to Cloud Storage: %s", ticker, e)
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

    with _CACHE_LOCK:
        _CACHE[ticker] = {"data": data, "timestamp": datetime.utcnow().isoformat()}
    _persist_entry(ticker)


def clear_cached_fundamentals(ticker: str) -> None:
    """Remove ``ticker`` from the cache and backing store if present."""

    with _CACHE_LOCK:
        _CACHE.pop(ticker, None)
    if config.CACHE_BACKEND == "redis":
        _client.hdel(_key, _redis_key(ticker))
    elif config.CACHE_BACKEND == "gcs":
        blob = _bucket.blob(_gcs_blob_name(ticker))
        try:
            blob.delete()
        except Exception:
            pass
    else:  # local
        path = _local_path(ticker)
        if os.path.exists(path):
            os.remove(path)


def clear_all_cache() -> None:
    """Clear the entire fundamentals cache."""

    with _CACHE_LOCK:
        _CACHE.clear()
    if config.CACHE_BACKEND == "redis":
        _client.delete(_key)
    elif config.CACHE_BACKEND == "gcs":
        try:
            for blob in _client.list_blobs(config.CACHE_GCS_BUCKET, prefix=_prefix):
                try:
                    blob.delete()
                except Exception:
                    pass
        except Exception:  # pragma: no cover - network failure
            logger.warning("Failed to clear Cloud Storage cache")
    else:  # local
        for filename in os.listdir(_prefix):
            if filename.endswith(".json"):
                try:
                    os.remove(os.path.join(_prefix, filename))
                except FileNotFoundError:
                    pass
