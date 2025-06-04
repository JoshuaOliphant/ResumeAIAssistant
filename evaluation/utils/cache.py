from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from collections import OrderedDict
import threading

@dataclass
class CacheEntry:
    value: Any
    expiry: datetime
    last_accessed: datetime = None
    
    def __post_init__(self):
        if self.last_accessed is None:
            self.last_accessed = datetime.now()

class EvaluationCache:
    """Thread-safe in-memory cache with TTL and LRU support."""

    def __init__(self, ttl: float = 3600.0, max_size: int = 1000) -> None:
        if ttl < 0:
            raise ValueError("ttl must be non-negative")
        if max_size < 1:
            raise ValueError("max_size must be positive")
            
        self.ttl = ttl
        self.max_size = max_size
        self._store: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            try:
                entry = self._store.get(key)
                if entry and entry.expiry > datetime.now():
                    # Update last accessed time and move to end (most recently used)
                    entry.last_accessed = datetime.now()
                    self._store.move_to_end(key)
                    self.hits += 1
                    return entry.value
                if entry:
                    del self._store[key]
                self.misses += 1
                return None
            except Exception:
                # If there's any error with datetime operations, treat as miss
                self.misses += 1
                return None

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            try:
                # Check if we need to evict entries
                self._evict_if_needed()
                
                # Add new entry
                expiry = datetime.now() + timedelta(seconds=self.ttl)
                self._store[key] = CacheEntry(value=value, expiry=expiry)
                
                # Move to end (most recently used)
                self._store.move_to_end(key)
            except Exception:
                # If there's any error, don't crash - just skip caching
                pass

    def _evict_if_needed(self) -> None:
        """Evict expired and LRU entries if needed."""
        now = datetime.now()
        
        # First, remove expired entries
        expired_keys = [
            key for key, entry in self._store.items() 
            if entry.expiry <= now
        ]
        for key in expired_keys:
            del self._store[key]
        
        # Then, if still over limit, remove LRU entries
        while len(self._store) >= self.max_size:
            # Remove least recently used (first item in OrderedDict)
            self._store.popitem(last=False)

    def stats(self) -> Dict[str, int]:
        with self._lock:
            return {
                "hits": self.hits, 
                "misses": self.misses, 
                "size": len(self._store),
                "max_size": self.max_size
            }

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self.hits = 0
            self.misses = 0
