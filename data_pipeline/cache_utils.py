"""Cache fundamentals with in-memory + GCS backing.

Requires:
  - config.CACHE_GCS_BUCKET (str)
  - optional config.CACHE_GCS_PREFIX (str)
  - optional config.CACHE_EXPIRY_MINUTES (int)
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any, Dict, Optional

from google.api_core.exceptions import NotFound
from google.cloud import storage

# Updated local imports to use fallback mechanism
try:
    from . import config
except ImportError:
    import data_pipeline.config as config

logger = config.get_file_logger(__name__)

# ---------------- In-memory state ----------------
_CACHE: Dict[str, Dict[str, Any]] = {}
_CACHE_LOCK = Lock()

# ---------------- Lazy GCS handles ----------------
_client: Optional[storage.Client] = None
_bucket = None


def _ensure_gcs():
    global _client, _bucket
    bucket_name = getattr(config, "CACHE_GCS_BUCKET", None)
    logger.debug("Ensuring GCS setup for bucket: %s", bucket_name)
    if not bucket_name:
        logger.warning(
            "CACHE_GCS_BUCKET not set; falling back to in-memory cache only.")
        return False
    if _client is None:
        logger.debug("Initializing GCS client")
        _client = storage.Client()
    if _bucket is None:
        logger.debug("Accessing GCS bucket '%s'", bucket_name)
        _bucket = _client.bucket(bucket_name)
        try:
            _bucket.reload()  # Check if bucket exists
            logger.debug("GCS bucket '%s' exists and is accessible", bucket_name)
        except NotFound:
            logger.debug("GCS bucket '%s' not found, attempting to create", bucket_name)
            try:
                _bucket = _client.create_bucket(bucket_name)
                logger.info("Created GCS bucket '%s'", bucket_name)
            except Exception as e:
                logger.warning(
                    "Failed to create GCS bucket '%s': %s; falling back to in-memory cache only.",
                    bucket_name,
                    e,
                )
                return False
        except Exception as e:
            logger.warning(
                "Failed to access GCS bucket '%s': %s; falling back to in-memory cache only.",
                bucket_name,
                e,
            )
            return False
    logger.debug("GCS setup complete for bucket '%s'", bucket_name)
    return True


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
            logger.debug("Loaded %s from in-memory cache", ticker)
            return _CACHE[ticker]

    if not _ensure_gcs():
        logger.debug("GCS not available, skipping load for %s", ticker)
        return None  # GCS not available, rely on in-memory only

    blob = _bucket.blob(_blob_name(ticker))
    try:
        data = blob.download_as_text()
        logger.debug("Downloaded %s from GCS", ticker)
    except NotFound:
        logger.debug("Blob for %s not found in GCS", ticker)
        return None
    except Exception as e:  # network/permission/transient
        logger.warning("Load from GCS failed for %s: %s",
                       ticker, e, exc_info=True)
        return None

    try:
        value = json.loads(data)
        logger.debug("Parsed JSON for %s from GCS", ticker)
    except Exception as e:
        logger.warning("Invalid JSON for %s in GCS: %s",
                       ticker, e, exc_info=True)
        return None

    with _CACHE_LOCK:
        _CACHE[ticker] = value
        logger.debug("Cached %s in memory", ticker)
        return value


def _persist_entry(ticker: str) -> None:
    """Persist a single ticker entry from memory to GCS."""
    with _CACHE_LOCK:
        entry = _CACHE.get(ticker)
    if entry is None:
        logger.debug("No entry in memory for %s, skipping persist", ticker)
        return

    if not _ensure_gcs():
        logger.debug("GCS not available, skipping persist for %s", ticker)
        return  # GCS not available, skip persisting

    blob = _bucket.blob(_blob_name(ticker))
    try:
        payload = json.dumps(entry, separators=(",", ":"), ensure_ascii=False)
        blob.upload_from_string(payload, content_type="application/json")
        logger.debug("Persisted %s to GCS", ticker)
    except NotFound:
        logger.warning("GCS bucket '%s' not found; skipping persist for %s",
                       config.CACHE_GCS_BUCKET, ticker)
    except Exception as e:
        logger.warning("Persist to GCS failed for %s: %s",
                       ticker, e, exc_info=True)


def load_cached_fundamentals(
    ticker: str,
    expiry_minutes: int = getattr(config, "CACHE_EXPIRY_MINUTES", 60),
) -> Optional[Any]:
    """Return cached fundamentals for ticker if present and fresh."""
    logger.debug("Loading cached fundamentals for %s with expiry %d minutes", ticker, expiry_minutes)
    entry = _load_entry(ticker)
    if not entry:
        logger.debug("No cached entry found for %s", ticker)
        return None

    ts_raw = entry.get("timestamp")
    try:
        ts = datetime.fromisoformat(ts_raw)
        if ts.tzinfo is None:  # legacy records
            ts = ts.replace(tzinfo=timezone.utc)
    except Exception:
        logger.debug("Invalid timestamp for %s, skipping", ticker)
        return None

    age = _now_utc() - ts
    if age < timedelta(minutes=expiry_minutes):
        logger.debug("Cache hit for %s, age: %s", ticker, age)
        return entry.get("data")
    logger.debug("Cache expired for %s, age: %s", ticker, age)
    return None


def save_fundamentals_cache(ticker: str, data: Any) -> None:
    """Store data for ticker and persist it."""
    logger.debug("Saving fundamentals cache for %s", ticker)
    with _CACHE_LOCK:
        _CACHE[ticker] = {"data": data, "timestamp": _now_utc().isoformat()}
    _persist_entry(ticker)


def clear_cached_fundamentals(ticker: str) -> None:
    """Remove ticker from cache and GCS if present."""
    logger.debug("Clearing cached fundamentals for %s", ticker)
    with _CACHE_LOCK:
        _CACHE.pop(ticker, None)

    if not _ensure_gcs():
        return  # GCS not available, skip

    try:
        _bucket.blob(_blob_name(ticker)).delete()
        logger.debug("Deleted %s from GCS", ticker)
    except NotFound:
        logger.debug("Blob for %s not found in GCS, nothing to delete", ticker)
        pass
    except Exception:
        logger.warning("Failed to delete %s from GCS", ticker, exc_info=True)


def clear_all_cache() -> None:
    """Clear entire fundamentals cache."""
    logger.debug("Clearing all fundamentals cache")
    with _CACHE_LOCK:
        _CACHE.clear()
    if not _ensure_gcs():
        return  # GCS not available, skip

    try:
        blobs = list(_client.list_blobs(config.CACHE_GCS_BUCKET, prefix=_prefix()))
        logger.debug("Found %d blobs to delete in GCS", len(blobs))
        for blob in blobs:
            try:
                blob.delete()
                logger.debug("Deleted blob %s from GCS", blob.name)
            except Exception:
                logger.warning("Failed deleting blob %s",
                               blob.name, exc_info=True)
    except Exception:
        logger.warning("Failed to clear GCS cache listing", exc_info=True)
