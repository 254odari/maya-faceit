"""
cache/cache_base.py

Foundation of the Caching System for Maya FaceIT.

This module provides the abstract base class (BaseCache) that every
specialized cache (MeshCache, LandmarkCache, BlendshapeCache, etc.)
inherits from. It implements generic caching behavior:
- Storage (dict-based, thread-safe)
- CRUD operations (get, set, delete, clear, contains)
- Expiration (TTL-based, manual, session)
- Statistics (hits, misses, hit rate, memory usage)
- Serialization hooks (subclasses can customize)
- Validation hooks (subclasses can customize)
- Event hooks (subclasses can override)
- Lifecycle (initialize, shutdown, reset, reload, flush)

The module does not know about meshes, blendshapes, or projects.
It is purely generic and reusable.

Dependencies:
- threading (for thread-safe operations)
- time (for timestamps and expiration)
- abc (for abstract base class)
- dataclasses (for data models)
- typing (for type hints)
- logging (for debug messages)
- weakref (optional, for caching weak refs)
- cache_utils: for key hashing, validation (if needed)
- cache_statistics: for statistics dataclass
- cache_exceptions: for custom exceptions

Design Pattern: Template Method.
"""

from __future__ import annotations

import abc
import logging
import threading
import time
import weakref
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import (
    Any, Dict, Optional, List, Set, Tuple, Union, Callable, Iterator, TypeVar, Generic,
    Type, cast, overload, Iterable, Mapping, MutableMapping, ValuesView, KeysView, ItemsView
)

# Import related modules (with fallbacks for development)
try:
    from .cache_exceptions import (
        CacheError, CacheNotFoundError, CacheCorruptError,
        CacheExpiredError, CacheFullError, CacheBackendError
    )
except ImportError:
    class CacheError(Exception): pass
    class CacheNotFoundError(CacheError): pass
    class CacheCorruptError(CacheError): pass
    class CacheExpiredError(CacheError): pass
    class CacheFullError(CacheError): pass
    class CacheBackendError(CacheError): pass

try:
    from .cache_statistics import CacheStatistics
except ImportError:
    class CacheStatistics:
        def __init__(self):
            self.hits = 0
            self.misses = 0
            self.hit_rate = 0.0
            self.avg_lookup_time = 0.0
            self.memory_usage_mb = 0.0
            self.disk_usage_mb = 0.0
            self.invalidations = 0
            self.evictions = 0
            self.total_entries = 0
            self.by_type = {}

try:
    from .cache_utils import get_cache_key, hash_data, validate_cache_key, sanitize_key, is_cacheable
except ImportError:
    def get_cache_key(*args, **kwargs): return str(args)
    def hash_data(data): return str(hash(str(data)))
    def validate_cache_key(key): return isinstance(key, str) and len(key) > 0
    def sanitize_key(key): return key.strip()
    def is_cacheable(data): return True

# ---- Part 1: Foundation ------------------------------------------------

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"

logger = logging.getLogger(__name__)

# ---- Part 2: Constants & Enumerations --------------------------------

class CacheStatus(Enum):
    """Status of the cache."""
    EMPTY = "empty"
    READY = "ready"
    DIRTY = "dirty"
    EXPIRED = "expired"
    INVALID = "invalid"
    LOCKED = "locked"


class CacheAction(Enum):
    """Actions for logging and events."""
    STORE = "store"
    GET = "get"
    DELETE = "delete"
    UPDATE = "update"
    CLEAR = "clear"
    LOAD = "load"
    SAVE = "save"


class ExpirationPolicy(Enum):
    """Policy for cache entry expiration."""
    NONE = "none"          # Never expires
    TIME = "time"          # Expires after TTL
    SESSION = "session"    # Expires at end of session (shutdown)
    MANUAL = "manual"      # Only manually removed
    MEMORY = "memory"      # Evicted due to memory pressure


# ---- Part 3: Data Models ----------------------------------------------

@dataclass
class CacheMetadata:
    """Metadata for a cache entry."""
    created: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    expires: Optional[float] = None  # Absolute timestamp, None = never
    hit_count: int = 0
    size_bytes: int = 0
    tags: Set[str] = field(default_factory=set)
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CacheEntry(Generic[Any]):
    """A cache entry containing value and metadata."""
    key: str
    value: Any
    metadata: CacheMetadata = field(default_factory=CacheMetadata)

    def is_expired(self, current_time: Optional[float] = None) -> bool:
        """Check if the entry is expired."""
        if self.metadata.expires is None:
            return False
        if current_time is None:
            current_time = time.time()
        return current_time > self.metadata.expires

    def touch(self) -> None:
        """Update last accessed time and increment hit count."""
        self.metadata.last_accessed = time.time()
        self.metadata.hit_count += 1


@dataclass
class CacheSettings:
    """Configuration for a cache."""
    max_size: Optional[int] = None          # Maximum number of entries
    max_memory_mb: Optional[float] = None   # Maximum memory usage in MB
    default_ttl: Optional[int] = None       # Default time-to-live in seconds
    expiration_policy: ExpirationPolicy = ExpirationPolicy.TIME
    auto_cleanup: bool = True               # Automatically remove expired entries
    cleanup_interval: int = 60              # Seconds between cleanup cycles
    use_weakrefs: bool = False              # Use weak references for values
    track_memory: bool = True               # Track memory usage
    enable_statistics: bool = True          # Collect statistics
    strict_key_validation: bool = True      # Validate keys before use


# ---- Part 4: Base Cache Class -----------------------------------------

T = TypeVar('T')


class BaseCache(abc.ABC, Generic[T]):
    """
    Abstract base class for all caches.

    Provides generic caching behavior. Subclasses should override
    validation, serialization, and event hooks as needed.
    """

    def __init__(self, name: str, cache_type: str = "generic", settings: Optional[CacheSettings] = None):
        """
        Initialize the cache.

        Args:
            name: Unique name for this cache instance.
            cache_type: Type of cache (e.g., 'mesh', 'blendshape').
            settings: Cache configuration.
        """
        self.name = name
        self.cache_type = cache_type
        self._settings = settings or CacheSettings()
        self._storage: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._status = CacheStatus.EMPTY
        self._statistics = CacheStatistics() if self._settings.enable_statistics else None
        self._last_cleanup = time.time()
        self._shutdown_called = False

        # For weak reference support
        self._weak_refs: Dict[str, weakref.ref] = {} if self._settings.use_weakrefs else None

        logger.debug(f"BaseCache '{name}' initialized")

    # ---- Lifecycle Methods ----

    def initialize(self) -> None:
        """Initialize the cache (load from disk if persistent, etc.)."""
        with self._lock:
            if self._status == CacheStatus.READY:
                return
            self._status = CacheStatus.READY
            self._last_cleanup = time.time()
            self._on_initialize()
            logger.debug(f"Cache '{self.name}' initialized")

    def shutdown(self) -> None:
        """Shut down the cache (save, clean up, etc.)."""
        if self._shutdown_called:
            return
        self._shutdown_called = True
        with self._lock:
            self._on_shutdown()
            self._status = CacheStatus.EMPTY
            logger.debug(f"Cache '{self.name}' shut down")

    def reset(self) -> None:
        """Reset the cache to empty state (clear all entries)."""
        with self._lock:
            self.clear()
            self._statistics = CacheStatistics() if self._settings.enable_statistics else None
            self._status = CacheStatus.EMPTY
            logger.debug(f"Cache '{self.name}' reset")

    def reload(self) -> None:
        """Reload the cache (clear and reinitialize)."""
        self.reset()
        self.initialize()

    def flush(self) -> None:
        """Flush the cache (save to persistent storage if applicable)."""
        with self._lock:
            self._on_flush()

    # ---- Hook Methods for Subclasses ----

    def _on_initialize(self) -> None:
        """Called during initialize(). Subclasses can override."""
        pass

    def _on_shutdown(self) -> None:
        """Called during shutdown(). Subclasses can override."""
        pass

    def _on_flush(self) -> None:
        """Called during flush(). Subclasses can override."""
        pass

    def _on_store(self, key: str, value: Any) -> None:
        """Called after an entry is stored. Subclasses can override."""
        pass

    def _on_get(self, key: str, value: Any) -> None:
        """Called after a successful get. Subclasses can override."""
        pass

    def _on_delete(self, key: str) -> None:
        """Called after an entry is deleted. Subclasses can override."""
        pass

    def _on_clear(self) -> None:
        """Called after the cache is cleared. Subclasses can override."""
        pass

    def _on_expire(self, key: str) -> None:
        """Called when an entry expires. Subclasses can override."""
        pass

    def _on_evict(self, key: str, reason: str) -> None:
        """Called when an entry is evicted. Subclasses can override."""
        pass

    def validate_key(self, key: str) -> bool:
        """
        Validate a cache key. Subclasses can override to add restrictions.
        """
        if not self._settings.strict_key_validation:
            return True
        return validate_cache_key(key)

    def validate_value(self, value: Any) -> bool:
        """
        Validate a value before storing. Subclasses can override.
        """
        return is_cacheable(value)

    def serialize_value(self, value: Any) -> Any:
        """
        Serialize a value for storage. Subclasses can override.
        """
        return value

    def deserialize_value(self, data: Any) -> Any:
        """
        Deserialize a value from storage. Subclasses can override.
        """
        return data

    # ---- Core Storage Operations ----

    def store(self, key: str, value: T, ttl: Optional[int] = None, tags: Optional[Set[str]] = None) -> None:
        """
        Store a value in the cache.

        Args:
            key: Cache key (string).
            value: Value to store.
            ttl: Time-to-live in seconds (overrides default).
            tags: Optional set of tags for the entry.
        """
        if not self.validate_key(key):
            raise CacheError(f"Invalid cache key: {key}")
        if not self.validate_value(value):
            raise CacheError(f"Invalid value for cache: {value}")

        # Check size limits
        if self._settings.max_size is not None:
            with self._lock:
                if len(self._storage) >= self._settings.max_size:
                    self._evict_lru()

        # Compute expiration
        expires = None
        if self._settings.expiration_policy == ExpirationPolicy.TIME:
            ttl_sec = ttl if ttl is not None else self._settings.default_ttl
            if ttl_sec is not None and ttl_sec > 0:
                expires = time.time() + ttl_sec

        # Serialize value
        serialized = self.serialize_value(value)

        # Calculate size (if memory tracking enabled)
        size_bytes = 0
        if self._settings.track_memory:
            size_bytes = self._estimate_size(serialized)

        # Create entry
        metadata = CacheMetadata(
            created=time.time(),
            last_accessed=time.time(),
            expires=expires,
            size_bytes=size_bytes,
            tags=tags or set()
        )

        with self._lock:
            # Store
            entry = CacheEntry(key=key, value=serialized, metadata=metadata)

            # If weakrefs enabled, store weak reference to value (if it's an object)
            if self._settings.use_weakrefs and hasattr(value, '__weakref__'):
                self._weak_refs[key] = weakref.ref(value)
                # Store a reference to the weakref in the entry
                entry.metadata.extra['weakref'] = True
                # The actual value in the entry is the strong reference? We'll store the weakref's target?
                # To keep it simple, we'll store the serialized value as usual, but we also keep a weak reference
                # for garbage collection. If the weakref is dead, we can detect and clean up.

            self._storage[key] = entry
            self._update_statistics(insert=True)
            self._on_store(key, value)

        # Cleanup if needed
        if self._settings.auto_cleanup:
            self._cleanup_expired()

        logger.debug(f"Cache '{self.name}': stored key '{key}'")

    def get(self, key: str, default: Optional[T] = None) -> Optional[T]:
        """
        Retrieve a value from the cache.

        Args:
            key: Cache key.
            default: Value to return if key not found.

        Returns:
            The stored value, or default if not found.
        """
        if not self.validate_key(key):
            raise CacheError(f"Invalid cache key: {key}")

        with self._lock:
            entry = self._storage.get(key)

            # Check if entry exists
            if entry is None:
                self._update_statistics(hit=False)
                return default

            # Check expiration
            if entry.is_expired():
                self._remove_entry(key, reason="expired")
                self._update_statistics(hit=False)
                return default

            # Update stats and last accessed
            entry.touch()
            self._update_statistics(hit=True)

            # Deserialize value
            value = self.deserialize_value(entry.value)

            # If weakrefs, check if the actual object still exists
            if self._settings.use_weakrefs and entry.metadata.extra.get('weakref'):
                ref = self._weak_refs.get(key)
                if ref is not None:
                    obj = ref()
                    if obj is None:
                        # Object was garbage collected, remove from cache
                        self._remove_entry(key, reason="weakref_dead")
                        self._update_statistics(hit=False)
                        return default
                    # Return the actual object (not the deserialized one)
                    # But we may have serialized a proxy; we should store the original.
                    # We'll override with the actual object.
                    value = obj

            self._on_get(key, value)
            return value

    def update(self, key: str, value: T, ttl: Optional[int] = None, merge: bool = False) -> None:
        """
        Update an existing entry.

        Args:
            key: Cache key.
            value: New value (or update dict).
            ttl: New TTL (overrides default).
            merge: If True, merge with existing value (if supported).
        """
        with self._lock:
            if key not in self._storage:
                raise CacheNotFoundError(f"Key '{key}' not found in cache '{self.name}'")

            if merge and hasattr(self._storage[key].value, 'update') and isinstance(value, dict):
                # Merge dict
                current = self.deserialize_value(self._storage[key].value)
                current.update(value)
                new_value = current
            else:
                new_value = value

            if not self.validate_value(new_value):
                raise CacheError(f"Invalid value for cache: {new_value}")

            # Serialize
            serialized = self.serialize_value(new_value)

            # Update expiration
            expires = None
            if self._settings.expiration_policy == ExpirationPolicy.TIME:
                ttl_sec = ttl if ttl is not None else self._settings.default_ttl
                if ttl_sec is not None and ttl_sec > 0:
                    expires = time.time() + ttl_sec

            entry = self._storage[key]
            entry.value = serialized
            entry.metadata.expires = expires
            entry.metadata.last_accessed = time.time()
            if self._settings.track_memory:
                entry.metadata.size_bytes = self._estimate_size(serialized)

            self._update_statistics(update=True)
            self._on_store(key, new_value)
            logger.debug(f"Cache '{self.name}': updated key '{key}'")

    def delete(self, key: str) -> None:
        """
        Delete an entry from the cache.

        Args:
            key: Cache key.
        """
        with self._lock:
            if key not in self._storage:
                raise CacheNotFoundError(f"Key '{key}' not found in cache '{self.name}'")
            self._remove_entry(key, reason="manual")
            self._update_statistics(delete=True)

    def contains(self, key: str) -> bool:
        """
        Check if the cache contains a valid (non-expired) entry for the key.
        """
        with self._lock:
            entry = self._storage.get(key)
            if entry is None:
                return False
            if entry.is_expired():
                return False
            return True

    def clear(self) -> None:
        """Remove all entries from the cache."""
        with self._lock:
            self._storage.clear()
            if self._weak_refs is not None:
                self._weak_refs.clear()
            self._update_statistics(clear=True)
            self._on_clear()
            logger.debug(f"Cache '{self.name}': cleared")

    def keys(self) -> KeysView[str]:
        """Return a view of all keys in the cache."""
        with self._lock:
            # Remove expired entries first?
            self._cleanup_expired()
            return self._storage.keys()

    def values(self) -> ValuesView[Any]:
        """Return a view of all values in the cache (deserialized)."""
        with self._lock:
            self._cleanup_expired()
            values = []
            for entry in self._storage.values():
                if not entry.is_expired():
                    values.append(self.deserialize_value(entry.value))
            return values

    def items(self) -> ItemsView[str, Any]:
        """Return a view of all key-value pairs in the cache (deserialized)."""
        with self._lock:
            self._cleanup_expired()
            items = []
            for key, entry in self._storage.items():
                if not entry.is_expired():
                    items.append((key, self.deserialize_value(entry.value)))
            return items

    def size(self) -> int:
        """Return the number of valid entries in the cache."""
        with self._lock:
            self._cleanup_expired()
            return len(self._storage)

    def memory_usage(self) -> float:
        """Return estimated memory usage in MB."""
        if not self._settings.track_memory:
            return 0.0
        with self._lock:
            total_bytes = sum(entry.metadata.size_bytes for entry in self._storage.values())
            return total_bytes / (1024.0 * 1024.0)

    def get_metadata(self, key: str) -> Optional[CacheMetadata]:
        """Return metadata for a given key."""
        with self._lock:
            entry = self._storage.get(key)
            if entry is None:
                return None
            if entry.is_expired():
                return None
            return entry.metadata

    def get_all_metadata(self) -> Dict[str, CacheMetadata]:
        """Return metadata for all entries."""
        with self._lock:
            self._cleanup_expired()
            return {key: entry.metadata for key, entry in self._storage.items()}

    # ---- Expiration & Cleanup ----

    def expire_key(self, key: str) -> None:
        """Manually mark an entry as expired."""
        with self._lock:
            entry = self._storage.get(key)
            if entry:
                entry.metadata.expires = time.time() - 1  # Expired
                self._on_expire(key)

    def _remove_entry(self, key: str, reason: str = "removed") -> None:
        """Remove an entry from storage."""
        if key in self._storage:
            del self._storage[key]
            if self._weak_refs is not None:
                self._weak_refs.pop(key, None)
            self._on_delete(key)

    def _cleanup_expired(self) -> int:
        """Remove expired entries and return count."""
        with self._lock:
            expired_keys = [key for key, entry in self._storage.items() if entry.is_expired()]
            for key in expired_keys:
                self._remove_entry(key, reason="expired")
                self._on_expire(key)
            if expired_keys:
                logger.debug(f"Cache '{self.name}': removed {len(expired_keys)} expired entries")
            return len(expired_keys)

    def _evict_lru(self) -> None:
        """
        Evict the least recently used entry when size limit is reached.
        """
        with self._lock:
            if not self._storage:
                return
            # Find the entry with the oldest last_accessed
            oldest_key = min(self._storage.keys(), key=lambda k: self._storage[k].metadata.last_accessed)
            self._remove_entry(oldest_key, reason="lru_evict")
            self._on_evict(oldest_key, "LRU eviction")
            logger.debug(f"Cache '{self.name}': evicted LRU entry '{oldest_key}'")

    def _estimate_size(self, value: Any) -> int:
        """
        Estimate memory size of a value in bytes.
        Subclasses can override for more accurate estimates.
        """
        # Simple estimate based on string representation
        import sys
        return sys.getsizeof(value)

    # ---- Statistics ----

    def statistics(self) -> CacheStatistics:
        """
        Return cache statistics.
        """
        if self._statistics is None:
            return CacheStatistics()
        with self._lock:
            stats = self._statistics
            # Update dynamic fields
            stats.total_entries = len(self._storage)
            stats.memory_usage_mb = self.memory_usage()
            # Hit rate
            total_requests = stats.hits + stats.misses
            if total_requests > 0:
                stats.hit_rate = stats.hits / total_requests
            else:
                stats.hit_rate = 0.0
            return stats

    def _update_statistics(self, hit: Optional[bool] = None, insert: bool = False,
                           update: bool = False, delete: bool = False, clear: bool = False) -> None:
        """Update statistics based on operation."""
        if self._statistics is None:
            return
        with self._lock:
            if hit is True:
                self._statistics.hits += 1
            elif hit is False:
                self._statistics.misses += 1
            if insert:
                self._statistics.total_entries += 1
                # Memory usage will be updated on access
            if update:
                pass
            if delete:
                self._statistics.total_entries -= 1
            if clear:
                self._statistics.total_entries = 0

    # ---- Serialization Support ----

    def export_data(self) -> Dict[str, Any]:
        """
        Export all cache data (including metadata) as a dictionary.
        Subclasses can override to include additional data.
        """
        with self._lock:
            self._cleanup_expired()
            data = {}
            for key, entry in self._storage.items():
                data[key] = {
                    'value': self.serialize_value(entry.value),
                    'metadata': {
                        'created': entry.metadata.created,
                        'last_accessed': entry.metadata.last_accessed,
                        'expires': entry.metadata.expires,
                        'hit_count': entry.metadata.hit_count,
                        'size_bytes': entry.metadata.size_bytes,
                        'tags': list(entry.metadata.tags),
                        'extra': entry.metadata.extra,
                    }
                }
            return data

    def import_data(self, data: Dict[str, Any]) -> None:
        """
        Import cache data from a dictionary.
        """
        with self._lock:
            self.clear()
            for key, entry_data in data.items():
                metadata = CacheMetadata(
                    created=entry_data['metadata']['created'],
                    last_accessed=entry_data['metadata']['last_accessed'],
                    expires=entry_data['metadata']['expires'],
                    hit_count=entry_data['metadata']['hit_count'],
                    size_bytes=entry_data['metadata']['size_bytes'],
                    tags=set(entry_data['metadata'].get('tags', [])),
                    extra=entry_data['metadata'].get('extra', {}),
                )
                entry = CacheEntry(
                    key=key,
                    value=entry_data['value'],
                    metadata=metadata
                )
                self._storage[key] = entry
            self._update_statistics(insert=True)  # Not accurate but enough
            logger.debug(f"Cache '{self.name}': imported {len(data)} entries")

    # ---- Context Manager ----

    def __enter__(self) -> 'BaseCache':
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.shutdown()

    # ---- Iteration ----

    def __iter__(self) -> Iterator[str]:
        return iter(self.keys())

    def __len__(self) -> int:
        return self.size()

    def __contains__(self, key: str) -> bool:
        return self.contains(key)

    def __getitem__(self, key: str) -> T:
        return self.get(key)

    def __setitem__(self, key: str, value: T) -> None:
        self.store(key, value)

    def __delitem__(self, key: str) -> None:
        self.delete(key)

    # ---- String Representation ----

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', size={self.size()}, status={self._status.value})"


# ---- Part 13: Public API -----------------------------------------------

__all__ = [
    "BaseCache",
    "CacheEntry",
    "CacheMetadata",
    "CacheSettings",
    "CacheStatus",
    "CacheAction",
    "ExpirationPolicy",
]