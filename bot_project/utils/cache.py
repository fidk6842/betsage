"""Thread-safe cache implementation with TTL support"""
import threading
import time
from datetime import datetime
from typing import Any, Optional, Dict

class SimpleCache:
    def __init__(self, ttl: int = 300):
        self._cache: Dict[str, tuple[Any, float]] = {}
        self._ttl = ttl
        self._lock = threading.Lock()
        self._cleanup_interval = 60  # Seconds between cleanups
        self._schedule_cleanup()

    def _schedule_cleanup(self):
        """Periodic cache maintenance"""
        timer = threading.Timer(self._cleanup_interval, self._schedule_cleanup)
        timer.daemon = True
        timer.start()
        self.cleanup()

    def cleanup(self):
        """Remove expired entries"""
        now = time.time()
        with self._lock:
            expired = [k for k, (_, exp) in self._cache.items() if exp < now]
            for key in expired:
                del self._cache[key]

    def get(self, key: str) -> Optional[Any]:
        """Retrieve cached value if exists and valid"""
        with self._lock:
            entry = self._cache.get(key)
            return entry[0] if entry and entry[1] > time.time() else None

    def set(self, key: str, value: Any):
        """Store value with expiration timestamp"""
        expires = time.time() + self._ttl
        with self._lock:
            self._cache[key] = (value, expires)