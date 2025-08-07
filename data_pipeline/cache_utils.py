
import json
import os
from datetime import datetime, timedelta

import config


CACHE_FILE = os.path.join(config.CACHE_DIR, "fundamentals_cache.json")

def load_cache_file():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_fundamentals_cache(ticker, data):
    cache = load_cache_file()
    cache[ticker] = {
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    }
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=4)

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
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache, f, indent=4)

def clear_all_cache():
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)
