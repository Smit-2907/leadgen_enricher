"""
In-memory cache for enrichment results.
Avoids re-scraping the same business within the same session.
TTL is not enforced (ephemeral session cache only).
For persistence, plug in Redis here.
"""
import hashlib
from typing import Optional, Dict, Any

_cache: Dict[str, Any] = {}


def _make_key(business_name: str, city: str) -> str:
    raw = f"{business_name.lower().strip()}|{city.lower().strip()}"
    return hashlib.md5(raw.encode()).hexdigest()


def get(business_name: str, city: str) -> Optional[Any]:
    key = _make_key(business_name, city)
    return _cache.get(key)


def set(business_name: str, city: str, result: Any) -> None:
    key = _make_key(business_name, city)
    _cache[key] = result


def clear():
    _cache.clear()
