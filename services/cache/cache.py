"""
maya_faceit/services/cache/cache.py

In‑memory and disk cache service for blendshape data, meshes, deltas, etc.
"""

import logging
import time
import json
import os
from typing import Any, Optional, Dict, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """An item stored in the cache."""
    key: str
    value: Any
    created: float = field(default_factory=time.time)
    ttl: Optional[float] = None  # seconds until expiry; None = never expires


class CacheService:
    """Central cache manager for the application."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self._memory_cache: Dict[str, CacheEntry] = {}
        self._disk_cache_dir: Optional[str] = None
        self._max_memory_items = 1000
        logger.debug("CacheService initialized")

    # ---------- Memory Cache ----------

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Store a value in the memory cache."""
        if len(self._memory_cache) >= self._max_memory_items:
            self._evict_oldest()
        self._memory_cache[key] = CacheEntry(key=key, value=value, ttl=ttl)

    def get(self, key: str) -> Optional[Any]:
        """Retrieve a value from the memory cache. Returns None if expired or not found."""
        entry = self._memory_cache.get(key)
        if entry is None:
            return None
        if entry.ttl is not None and (time.time() - entry.created) > entry.ttl:
            del self._memory_cache[key]
            return None
        return entry.value

    def delete(self, key: str) -> None:
        """Remove a key from the memory cache."""
        if key in self._memory_cache:
            del self._memory_cache[key]

    def clear(self) -> None:
        """Clear the entire memory cache."""
        self._memory_cache.clear()

    def _evict_oldest(self) -> None:
        """Remove the oldest entry from the memory cache."""
        if not self._memory_cache:
            return
        oldest = min(self._memory_cache.values(), key=lambda e: e.created)
        del self._memory_cache[oldest.key]

    # ---------- Disk Cache ----------

    def set_disk_cache_dir(self, path: str) -> None:
        """Set the directory for disk cache (persistent storage)."""
        self._disk_cache_dir = path
        os.makedirs(path, exist_ok=True)

    def store_disk(self, key: str, data: Any) -> bool:
        """Store data to disk as JSON (must be JSON‑serializable)."""
        if not self._disk_cache_dir:
            logger.warning("Disk cache directory not set.")
            return False
        filepath = os.path.join(self._disk_cache_dir, f"{key}.json")
        try:
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to write disk cache {key}: {e}")
            return False

    def load_disk(self, key: str) -> Optional[Any]:
        """Load data from disk cache."""
        if not self._disk_cache_dir:
            return None
        filepath = os.path.join(self._disk_cache_dir, f"{key}.json")
        if not os.path.exists(filepath):
            return None
        try:
            with open(filepath, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read disk cache {key}: {e}")
            return None

    def clear_disk(self) -> None:
        """Delete all disk cache files."""
        if not self._disk_cache_dir or not os.path.exists(self._disk_cache_dir):
            return
        for fname in os.listdir(self._disk_cache_dir):
            if fname.endswith(".json"):
                try:
                    os.remove(os.path.join(self._disk_cache_dir, fname))
                except Exception as e:
                    logger.warning(f"Failed to delete cache file {fname}: {e}")

    # ---------- Statistics ----------

    def get_statistics(self) -> Dict[str, int]:
        return {
            "memory_items": len(self._memory_cache),
            "disk_items": self._count_disk_items(),
        }

    def _count_disk_items(self) -> int:
        if not self._disk_cache_dir or not os.path.exists(self._disk_cache_dir):
            return 0
        return len([f for f in os.listdir(self._disk_cache_dir) if f.endswith(".json")])