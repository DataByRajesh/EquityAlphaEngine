
"""Cache fundamentals with in-memory + GCS backing.

Requires:
  - config.CACHE_GCS_BUCKET (str)
  - optional config.CACHE_GCS_PREFIX (str)
  - optional config.CACHE_EXPIRY_MINUTES (int)
"""

from __future__ import annotations

import json
import logging
import os
from datetime import timedelta
from threading import Lock
from typing import Dict, Optional, Any
from datetime import datetime, timezone

from google.cloud import storage
from google.api_core.exceptions import NotFound

from . import config

logger = config.get_file_logger(__name__)

# ---------------- In-memory state ----------------
_CACHE: Dict[str, Dict[str, Any]] = {}
_CACHE_LOCK = Lock()

# ---------------- Lazy GCS handles ----------------
_client: Optional[storage.Client] = None
_bucket = None

def _ensure_gcs():
    global _client, _bucket
    if not getattr(config, "CACHE_GCS_BUCKET", None):
        raise RuntimeError("CACHE_GCS_BUCKET is required for GCS cache backend.")
    if _client is None:
        _client = storage.Client()
    if _bucket is None:
        _bucket = _client.bucket(config.CACHE_GCS_BUCKET)

def _prefix() -> str:
    base = getattr(config, "CACHE_GCS_PREFIX", "") or ""
    base = base.strip("/")

    return f"{base}/fundamentals_cache" if base else "fundamentals_cache"

def _blob_name(ticker: str) -> str:
    return f"{_prefix()}/{ticker}.json"

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)

def _load_entry(ticker: str) -> Optional[Dict[str, Any]]:
    """Load ticker from GCS into memory (if present)."""
    with _CACHE_LOCK:
        if ticker in _CACHE:
            return _CACHE[ticker]

    _ensure_gcs()
    blob = _bucket.blob(_blob_name(ticker))
    try:
        data = blob.download_as_text()
    except NotFound:
        return None
    except Exception as e:  # network/permission/transient
        logger.warning("Load from GCS failed for %s: %s", ticker, e, exc_info=True)
        return None

    try:
        value = json.loads(data)
    except Exception as e:
        logger.warning("Invalid JSON for %s in GCS: %s", ticker, e, exc_info=True)
        return None

    with _CACHE_LOCK:
        _CACHE[ticker] = value
        return value

def _persist_entry(ticker: str) -> None:
    """Persist a single ticker entry from memory to GCS."""
    with _CACHE_LOCK:
        entry = _CACHE.get(ticker)
    if entry is None:
        return

    _ensure_gcs()
    blob = _bucket.blob(_blob_name(ticker))
    try:
        payload = json.dumps(entry, separators=(",", ":"), ensure_ascii=False)
        blob.upload_from_string(payload, content_type="application/json")
    except Exception as e:
        logger.warning("Persist to GCS failed for %s: %s", ticker, e, exc_info=True)

def load_cached_fundamentals(
    ticker: str,
    expiry_minutes: int = getattr(config, "CACHE_EXPIRY_MINUTES", 60),
) -> Optional[Any]:
    """Return cached fundamentals for ticker if present and fresh."""
    entry = _load_entry(ticker)
    if not entry:
        return None

    ts_raw = entry.get("timestamp")
    try:
        ts = datetime.fromisoformat(ts_raw)
        if ts.tzinfo is None:  # legacy records
            ts = ts.replace(tzinfo=timezone.utc)
    except Exception:
        return None

    if _now_utc() - ts < timedelta(minutes=expiry_minutes):
        return entry.get("data")
    return None

def save_fundamentals_cache(ticker: str, data: Any) -> None:
    """Store data for ticker and persist it."""
    with _CACHE_LOCK:
        _CACHE[ticker] = {"data": data, "timestamp": _now_utc().isoformat()}
    _persist_entry(ticker)

def clear_cached_fundamentals(ticker: str) -> None:
    """Remove ticker from cache and GCS if present."""
    with _CACHE_LOCK:
        _CACHE.pop(ticker, None)

    try:
        _ensure_gcs()
        _bucket.blob(_blob_name(ticker)).delete()
    except NotFound:
        pass
    except Exception:
        logger.warning("Failed to delete %s from GCS", ticker, exc_info=True)

def clear_all_cache() -> None:
    """Clear entire fundamentals cache."""
    with _CACHE_LOCK:
        _CACHE.clear()
    try:
        _ensure_gcs()
        for blob in _client.list_blobs(config.CACHE_GCS_BUCKET, prefix=_prefix()):
            try:
                blob.delete()
            except Exception:
                logger.warning("Failed deleting blob %s", blob.name, exc_info=True)
    except Exception:
        logger.warning("Failed to clear GCS cache listing", exc_info=True)
