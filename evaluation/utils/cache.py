from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

@dataclass
class CacheEntry:
    value: Any
    expiry: datetime

class EvaluationCache:
    """Simple in-memory cache with TTL support."""

    def __init__(self, ttl: float = 3600.0) -> None:
        self.ttl = ttl
        self._store: Dict[str, CacheEntry] = {}
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry and entry.expiry > datetime.now():
            self.hits += 1
            return entry.value
        if entry:
            del self._store[key]
        self.misses += 1
        return None

    def set(self, key: str, value: Any) -> None:
        self._store[key] = CacheEntry(value=value, expiry=datetime.now() + timedelta(seconds=self.ttl))

    def stats(self) -> Dict[str, int]:
        return {"hits": self.hits, "misses": self.misses, "size": len(self._store)}

    def clear(self) -> None:
        self._store.clear()
        self.hits = 0
        self.misses = 0
