"""
cache/cache_manager.py

Master Controller of the Caching Subsystem for Maya FaceIT.

This module coordinates all specialized caches (mesh, landmark, blendshape, project)
and provides a single interface for the rest of the plugin. It handles initialization,
registration, invalidation, persistence, memory management, statistics, and events.

Responsibilities:
- Initialize and shutdown the caching system.
- Register/unregister cache instances.
- Provide unified API for cache access.
- Manage cache policies (LRU, FIFO, time-based, etc.).
- Invalidate cache entries by key, type, or globally.
- Track memory usage and perform evictions when limits are exceeded.
- Save and load persistent caches (disk backend).
- Collect and report cache statistics.
- Dispatch events for UI and pipeline integration.

Dependencies:
- cache_base.py: CacheEntry, CachePolicy, CacheBase.
- cache_exceptions.py: Custom exceptions.
- memory_cache.py, disk_cache.py: Backends.
- mesh_cache.py, landmark_cache.py, blendshape_cache.py, project_cache.py: Specialized caches.
- cache_statistics.py, cache_utils.py: Statistics and utilities.

The manager uses a Facade + Registry pattern.
"""

from __future__ import annotations

import copy
import logging
import time
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Dict, Any, Set, Tuple, Union, Callable, Type, Iterator

# Import submodules (with fallbacks for development)
try:
    from .cache_base import CacheBase, CacheEntry, CachePolicy
    from .cache_exceptions import (
        CacheError, CacheNotFoundError, CacheCorruptError,
        CacheExpiredError, CacheFullError, CacheBackendError
    )
    from .memory_cache import MemoryCache
    from .disk_cache import DiskCache
    from .mesh_cache import MeshCache
    from .landmark_cache import LandmarkCache
    from .blendshape_cache import BlendshapeCache
    from .project_cache import ProjectCache
    from .cache_statistics import CacheStatistics
    from .cache_utils import get_cache_key, hash_data, validate_cache_key, sanitize_key, is_cacheable
except ImportError:
    # Define minimal fallback classes for development
    class CacheError(Exception): pass
    class CacheNotFoundError(CacheError): pass
    class CacheCorruptError(CacheError): pass
    class CacheExpiredError(CacheError): pass
    class CacheFullError(CacheError): pass
    class CacheBackendError(CacheError): pass

    class CachePolicy(Enum):
        ALWAYS = auto()
        LAZY = auto()
        ON_DEMAND = auto()
        PERSISTENT = auto()
        TEMPORARY = auto()

    class CacheEntry:
        def __init__(self, key, data, cache_type=None, created=None, expires=None, metadata=None):
            self.key = key
            self.data = data
            self.cache_type = cache_type
            self.created = created or time.time()
            self.expires = expires
            self.metadata = metadata or {}
            self.hit_count = 0

    class CacheBase:
        def __init__(self, manager, name, cache_type):
            self.manager = manager
            self.name = name
            self.cache_type = cache_type
            self._data = {}
            self._policy = CachePolicy.ALWAYS
        def get(self, key): return None
        def set(self, key, data, ttl=None): pass
        def delete(self, key): pass
        def clear(self): pass
        def size(self): return 0
        def keys(self): return []

    class MemoryCache(CacheBase):
        pass
    class DiskCache(CacheBase):
        pass
    class MeshCache(CacheBase):
        pass
    class LandmarkCache(CacheBase):
        pass
    class BlendshapeCache(CacheBase):
        pass
    class ProjectCache(CacheBase):
        pass

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

    def get_cache_key(*args, **kwargs):
        import hashlib
        return hashlib.md5(str(args).encode()).hexdigest()
    def hash_data(data):
        import hashlib
        return hashlib.md5(str(data).encode()).hexdigest()
    def validate_cache_key(key):
        return isinstance(key, str) and len(key) > 0
    def sanitize_key(key):
        return key.strip()
    def is_cacheable(data):
        return True

# ---- Part 1: Foundation ------------------------------------------------

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"

logger = logging.getLogger(__name__)

# ---- Part 2: Constants & Enumerations --------------------------------

class CacheType(Enum):
    """Types of caches."""
    MESH = "mesh"
    LANDMARK = "landmark"
    BLENDSHAPE = "blendshape"
    PROJECT = "project"
    MEMORY = "memory"
    DISK = "disk"
    CUSTOM = "custom"


class CacheState(Enum):
    """State of the cache system."""
    EMPTY = "empty"
    READY = "ready"
    LOADED = "loaded"
    DIRTY = "dirty"
    INVALID = "invalid"
    LOCKED = "locked"


class InvalidationReason(Enum):
    """Reason for cache invalidation."""
    MESH_CHANGED = "mesh_changed"
    PROJECT_CHANGED = "project_changed"
    PLUGIN_UPDATED = "plugin_updated"
    USER_REQUEST = "user_request"
    MEMORY_LIMIT = "memory_limit"
    TIMEOUT = "timeout"
    CUSTOM = "custom"


# ---- Part 3: Data Models ----------------------------------------------

@dataclass
class CacheDescriptor:
    """Description of a registered cache."""
    name: str
    cache_type: CacheType
    instance: CacheBase
    policy: CachePolicy
    max_size: Optional[int] = None
    ttl: Optional[int] = None
    persistent: bool = False
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CacheSettings:
    """Global cache settings."""
    default_policy: CachePolicy = CachePolicy.ALWAYS
    default_ttl: int = 3600  # seconds
    max_memory_mb: int = 1024
    max_disk_mb: int = 5120
    persistent_by_default: bool = True
    enable_statistics: bool = True
    enable_events: bool = True
    debug_mode: bool = False


@dataclass
class CacheReport:
    """Diagnostic report for the cache system."""
    success: bool
    registered_caches: int
    cache_entries: int
    memory_usage_mb: float
    disk_usage_mb: float
    hit_rate: float
    invalidation_count: int
    eviction_count: int
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CacheEvent:
    """Event dispatched by the cache system."""
    event_type: str  # e.g., 'before_load', 'after_save', 'invalidated'
    cache_name: str
    cache_type: CacheType
    key: Optional[str] = None
    data: Optional[Any] = None
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---- Part 4: Cache Registry -------------------------------------------

class CacheRegistry:
    """
    Registry for all cache instances.
    """
    def __init__(self):
        self._caches: Dict[str, CacheDescriptor] = {}
        self._by_type: Dict[CacheType, List[str]] = {t: [] for t in CacheType}
        self._lock = threading.RLock()

    def register(self, descriptor: CacheDescriptor) -> None:
        """Register a cache."""
        with self._lock:
            if descriptor.name in self._caches:
                raise CacheError(f"Cache '{descriptor.name}' already registered")
            self._caches[descriptor.name] = descriptor
            self._by_type[descriptor.cache_type].append(descriptor.name)

    def unregister(self, name: str) -> None:
        """Unregister a cache."""
        with self._lock:
            if name not in self._caches:
                raise CacheNotFoundError(f"Cache '{name}' not registered")
            desc = self._caches.pop(name)
            self._by_type[desc.cache_type].remove(name)

    def get(self, name: str) -> Optional[CacheDescriptor]:
        return self._caches.get(name)

    def get_by_type(self, cache_type: CacheType) -> List[CacheDescriptor]:
        return [self._caches[name] for name in self._by_type.get(cache_type, []) if name in self._caches]

    def list_caches(self) -> List[str]:
        return list(self._caches.keys())

    def clear(self) -> None:
        with self._lock:
            self._caches.clear()
            self._by_type = {t: [] for t in CacheType}


# ---- Part 5: Cache Manager -------------------------------------------

class CacheManager:
    """
    Master controller for the caching subsystem.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self._settings = CacheSettings()
        self._registry = CacheRegistry()
        self._statistics = CacheStatistics() if CacheStatistics else None
        self._event_listeners: Dict[str, List[Callable]] = {}
        self._state = CacheState.EMPTY
        self._lock = threading.RLock()
        self._shutdown_called = False

        # Cache instances (lazy creation)
        self._mesh_cache = None
        self._landmark_cache = None
        self._blendshape_cache = None
        self._project_cache = None
        self._memory_cache = None
        self._disk_cache = None

        # Memory tracking
        self._memory_usage = 0.0  # MB
        self._disk_usage = 0.0  # MB
        self._eviction_count = 0
        self._invalidation_count = 0

        logger.debug("CacheManager initialized")

    # ---- Lifecycle ----

    def initialize(self, settings: Optional[CacheSettings] = None) -> None:
        """
        Initialize the cache system with optional settings.
        """
        if self._state == CacheState.READY:
            return

        if settings:
            self._settings = settings

        # Initialize default caches
        self._init_default_caches()

        self._state = CacheState.READY
        logger.info("Cache system initialized")

    def shutdown(self) -> None:
        """
        Shut down the cache system, persisting data if needed.
        """
        if self._shutdown_called:
            return
        self._shutdown_called = True

        # Persist all caches that support persistence
        self._save_all()

        # Clear memory caches
        self._clear_caches(persistent_only=False)

        self._state = CacheState.EMPTY
        logger.info("Cache system shut down")

    def _init_default_caches(self) -> None:
        """Initialize and register default caches."""
        # Memory and Disk backends
        self._memory_cache = MemoryCache(self, "memory", CacheType.MEMORY)
        self._disk_cache = DiskCache(self, "disk", CacheType.DISK)

        # Specialized caches
        self._mesh_cache = MeshCache(self, "mesh", CacheType.MESH)
        self._landmark_cache = LandmarkCache(self, "landmark", CacheType.LANDMARK)
        self._blendshape_cache = BlendshapeCache(self, "blendshape", CacheType.BLENDSHAPE)
        self._project_cache = ProjectCache(self, "project", CacheType.PROJECT)

        # Register them
        self.register_cache(
            name="mesh",
            cache_type=CacheType.MESH,
            instance=self._mesh_cache,
            policy=CachePolicy.ALWAYS,
            persistent=self._settings.persistent_by_default,
            description="Caches mesh data (vertex positions, topology, etc.)"
        )
        self.register_cache(
            name="landmark",
            cache_type=CacheType.LANDMARK,
            instance=self._landmark_cache,
            policy=CachePolicy.ALWAYS,
            persistent=self._settings.persistent_by_default,
            description="Caches facial landmark data"
        )
        self.register_cache(
            name="blendshape",
            cache_type=CacheType.BLENDSHAPE,
            instance=self._blendshape_cache,
            policy=CachePolicy.ALWAYS,
            persistent=self._settings.persistent_by_default,
            description="Caches blendshape data (deltas, weights, etc.)"
        )
        self.register_cache(
            name="project",
            cache_type=CacheType.PROJECT,
            instance=self._project_cache,
            policy=CachePolicy.PERSISTENT,
            persistent=True,
            description="Caches project-level data"
        )
        self.register_cache(
            name="memory",
            cache_type=CacheType.MEMORY,
            instance=self._memory_cache,
            policy=CachePolicy.LAZY,
            persistent=False,
            description="In-memory cache backend"
        )
        self.register_cache(
            name="disk",
            cache_type=CacheType.DISK,
            instance=self._disk_cache,
            policy=CachePolicy.PERSISTENT,
            persistent=True,
            description="Disk-based persistent cache backend"
        )

    # ---- Registry Management ----

    def register_cache(
        self,
        name: str,
        cache_type: CacheType,
        instance: CacheBase,
        policy: CachePolicy = CachePolicy.ALWAYS,
        max_size: Optional[int] = None,
        ttl: Optional[int] = None,
        persistent: bool = False,
        description: str = ""
    ) -> None:
        """
        Register a cache instance.
        """
        if self._registry.get(name):
            raise CacheError(f"Cache '{name}' already registered")

        descriptor = CacheDescriptor(
            name=name,
            cache_type=cache_type,
            instance=instance,
            policy=policy,
            max_size=max_size,
            ttl=ttl if ttl is not None else self._settings.default_ttl,
            persistent=persistent,
            description=description
        )
        self._registry.register(descriptor)

        # Set cache's manager reference
        if hasattr(instance, 'set_manager'):
            instance.set_manager(self)

        logger.debug(f"Registered cache: {name} ({cache_type.value})")

    def unregister_cache(self, name: str) -> None:
        """
        Unregister a cache.
        """
        self._registry.unregister(name)
        logger.debug(f"Unregistered cache: {name}")

    def get_cache(self, name: str) -> Optional[CacheBase]:
        """
        Get a cache instance by name.
        """
        desc = self._registry.get(name)
        return desc.instance if desc else None

    def list_caches(self) -> List[str]:
        """
        List all registered cache names.
        """
        return self._registry.list_caches()

    # ---- Core Operations ----

    def get(self, cache_name: str, key: str, default: Any = None) -> Any:
        """
        Get a value from a specific cache.
        """
        cache = self.get_cache(cache_name)
        if not cache:
            raise CacheNotFoundError(f"Cache '{cache_name}' not found")
        return cache.get(key, default)

    def set(self, cache_name: str, key: str, data: Any, ttl: Optional[int] = None) -> None:
        """
        Set a value in a specific cache.
        """
        cache = self.get_cache(cache_name)
        if not cache:
            raise CacheNotFoundError(f"Cache '{cache_name}' not found")
        cache.set(key, data, ttl)

    def delete(self, cache_name: str, key: str) -> None:
        """
        Delete a value from a specific cache.
        """
        cache = self.get_cache(cache_name)
        if not cache:
            raise CacheNotFoundError(f"Cache '{cache_name}' not found")
        cache.delete(key)

    def clear(self, cache_name: Optional[str] = None) -> None:
        """
        Clear a specific cache or all caches.
        """
        if cache_name:
            cache = self.get_cache(cache_name)
            if cache:
                cache.clear()
                logger.debug(f"Cleared cache: {cache_name}")
        else:
            self._clear_caches(persistent_only=False)

    def invalidate(
        self,
        key: Optional[str] = None,
        cache_type: Optional[CacheType] = None,
        reason: InvalidationReason = InvalidationReason.CUSTOM,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Invalidate cache entries.

        - If key is provided, invalidate that specific entry across all caches.
        - If cache_type is provided, invalidate all entries of that cache type.
        - If neither, invalidate all caches.
        """
        self._dispatch_event('before_invalidate', cache_type=cache_type, key=key, metadata=metadata)
        self._invalidation_count += 1

        with self._lock:
            if key is not None:
                # Invalidate a specific key across all caches
                for desc in self._registry.list_caches():
                    cache = self.get_cache(desc)
                    if cache:
                        cache.delete(key)
            elif cache_type is not None:
                # Invalidate all caches of a specific type
                for desc in self._registry.get_by_type(cache_type):
                    cache = desc.instance
                    if cache:
                        cache.clear()
                        logger.debug(f"Invalidated cache of type {cache_type.value}: {desc.name}")
            else:
                # Invalidate all caches
                self._clear_caches(persistent_only=False)

        self._dispatch_event('after_invalidate', cache_type=cache_type, key=key, metadata=metadata)

    def invalidate_all(self) -> None:
        """Invalidate all caches (convenience)."""
        self.invalidate(reason=InvalidationReason.USER_REQUEST)

    def invalidate_mesh(self, mesh_id: str) -> None:
        """Invalidate mesh cache entries related to a specific mesh."""
        # This is a convenience method
        self.invalidate(key=mesh_id, cache_type=CacheType.MESH, reason=InvalidationReason.MESH_CHANGED)

    def invalidate_project(self, project_id: str) -> None:
        """Invalidate project cache entries."""
        self.invalidate(key=project_id, cache_type=CacheType.PROJECT, reason=InvalidationReason.PROJECT_CHANGED)

    # ---- Persistence ----

    def save_all(self) -> None:
        """Save all persistent caches."""
        self._save_all()

    def load_all(self) -> None:
        """Load all persistent caches."""
        self._load_all()

    def _save_all(self) -> None:
        self._dispatch_event('before_save_all')
        for desc in self._registry.list_caches():
            cache = self.get_cache(desc)
            if cache and hasattr(cache, 'save'):
                try:
                    cache.save()
                except Exception as e:
                    logger.error(f"Failed to save cache {desc}: {e}")
        self._dispatch_event('after_save_all')

    def _load_all(self) -> None:
        self._dispatch_event('before_load_all')
        for desc in self._registry.list_caches():
            cache = self.get_cache(desc)
            if cache and hasattr(cache, 'load'):
                try:
                    cache.load()
                except Exception as e:
                    logger.error(f"Failed to load cache {desc}: {e}")
        self._dispatch_event('after_load_all')

    def _clear_caches(self, persistent_only: bool = False) -> None:
        """Clear caches (optionally only persistent ones)."""
        with self._lock:
            for desc in self._registry.list_caches():
                cache = self.get_cache(desc)
                if cache:
                    if persistent_only and not desc.persistent:
                        continue
                    cache.clear()
                    logger.debug(f"Cleared cache: {desc}")

    # ---- Memory Management ----

    def get_memory_usage(self) -> float:
        """Return current memory usage in MB."""
        # This would aggregate memory usage from all caches
        total = 0.0
        for desc in self._registry.list_caches():
            cache = self.get_cache(desc)
            if cache and hasattr(cache, 'memory_usage'):
                total += cache.memory_usage()
        self._memory_usage = total
        return total

    def get_disk_usage(self) -> float:
        """Return current disk usage in MB."""
        total = 0.0
        for desc in self._registry.list_caches():
            cache = self.get_cache(desc)
            if cache and hasattr(cache, 'disk_usage'):
                total += cache.disk_usage()
        self._disk_usage = total
        return total

    def evict(self, amount_mb: Optional[float] = None) -> None:
        """Evict cache entries to reduce memory usage."""
        if amount_mb is None:
            # Evict until memory usage is below limit
            current = self.get_memory_usage()
            limit = self._settings.max_memory_mb
            if current > limit:
                amount_mb = current - limit
            else:
                return

        self._dispatch_event('before_evict', metadata={'amount_mb': amount_mb})
        self._eviction_count += 1

        # Evict from caches based on policy
        # For simplicity, evict from memory cache first
        memory_cache = self.get_cache('memory')
        if memory_cache and hasattr(memory_cache, 'evict'):
            memory_cache.evict(amount_mb)

        self._dispatch_event('after_evict', metadata={'amount_mb': amount_mb})

    # ---- Statistics ----

    def get_statistics(self) -> CacheStatistics:
        """
        Return aggregated cache statistics.
        """
        if not self._statistics:
            return CacheStatistics()

        stats = copy.deepcopy(self._statistics)
        # Aggregate from all caches
        total_hits = 0
        total_misses = 0
        total_entries = 0
        by_type = {}
        for desc in self._registry.list_caches():
            cache = self.get_cache(desc)
            if cache and hasattr(cache, 'statistics'):
                cstats = cache.statistics()
                total_hits += getattr(cstats, 'hits', 0)
                total_misses += getattr(cstats, 'misses', 0)
                total_entries += getattr(cstats, 'total_entries', 0)
                # Aggregate by type
                tname = desc.cache_type.value
                by_type[tname] = by_type.get(tname, 0) + getattr(cstats, 'total_entries', 0)

        stats.hits = total_hits
        stats.misses = total_misses
        stats.total_entries = total_entries
        stats.by_type = by_type
        if total_hits + total_misses > 0:
            stats.hit_rate = total_hits / (total_hits + total_misses)
        else:
            stats.hit_rate = 0.0
        stats.memory_usage_mb = self.get_memory_usage()
        stats.disk_usage_mb = self.get_disk_usage()
        stats.invalidations = self._invalidation_count
        stats.evictions = self._eviction_count
        return stats

    # ---- Diagnostics ----

    def diagnose(self) -> CacheReport:
        """
        Generate a diagnostic report.
        """
        report = CacheReport(
            success=True,
            registered_caches=len(self._registry.list_caches()),
            cache_entries=self._count_entries(),
            memory_usage_mb=self.get_memory_usage(),
            disk_usage_mb=self.get_disk_usage(),
            hit_rate=self.get_statistics().hit_rate,
            invalidation_count=self._invalidation_count,
            eviction_count=self._eviction_count,
            details={}
        )
        # Collect warnings from caches
        for desc in self._registry.list_caches():
            cache = self.get_cache(desc)
            if cache and hasattr(cache, 'diagnose'):
                try:
                    diag = cache.diagnose()
                    if not diag.get('success', True):
                        report.warnings.extend(diag.get('warnings', []))
                        report.errors.extend(diag.get('errors', []))
                        report.success = False
                except Exception as e:
                    report.errors.append(f"Cache {desc} diagnosis failed: {e}")
                    report.success = False
        return report

    def _count_entries(self) -> int:
        total = 0
        for desc in self._registry.list_caches():
            cache = self.get_cache(desc)
            if cache:
                total += cache.size()
        return total

    # ---- Event System ----

    def register_event_listener(self, event_type: str, callback: Callable) -> None:
        """
        Register a callback for a specific event type.
        """
        if event_type not in self._event_listeners:
            self._event_listeners[event_type] = []
        self._event_listeners[event_type].append(callback)

    def unregister_event_listener(self, event_type: str, callback: Callable) -> None:
        """
        Unregister a callback.
        """
        if event_type in self._event_listeners:
            try:
                self._event_listeners[event_type].remove(callback)
            except ValueError:
                pass

    def _dispatch_event(self, event_type: str, **kwargs) -> None:
        """Dispatch an event to all registered listeners."""
        if not self._settings.enable_events:
            return
        event = CacheEvent(
            event_type=event_type,
            cache_name=kwargs.get('cache_name', ''),
            cache_type=kwargs.get('cache_type', CacheType.CUSTOM),
            key=kwargs.get('key'),
            data=kwargs.get('data'),
            metadata=kwargs.get('metadata', {})
        )
        for cb in self._event_listeners.get(event_type, []):
            try:
                cb(event)
            except Exception as e:
                logger.warning(f"Event callback failed: {e}")

    # ---- Utilities ----

    def set_settings(self, settings: CacheSettings) -> None:
        """Update cache settings."""
        self._settings = settings
        # Apply to all caches
        for desc in self._registry.list_caches():
            cache = self.get_cache(desc)
            if cache and hasattr(cache, 'set_policy'):
                cache.set_policy(self._settings.default_policy)

    def get_settings(self) -> CacheSettings:
        return self._settings

    def get_state(self) -> CacheState:
        return self._state

    def reset(self) -> None:
        """Reset the cache system (clear all caches and reset statistics)."""
        self._clear_caches(persistent_only=False)
        self._statistics = CacheStatistics()
        self._invalidation_count = 0
        self._eviction_count = 0
        self._memory_usage = 0.0
        self._disk_usage = 0.0

    # ---- Debug ----

    def debug_info(self) -> Dict[str, Any]:
        """Return debug information about the cache system."""
        return {
            "state": self._state.value,
            "settings": {
                "default_policy": self._settings.default_policy.value,
                "default_ttl": self._settings.default_ttl,
                "max_memory_mb": self._settings.max_memory_mb,
                "max_disk_mb": self._settings.max_disk_mb,
                "persistent_by_default": self._settings.persistent_by_default,
            },
            "registered_caches": self._registry.list_caches(),
            "memory_usage_mb": self._memory_usage,
            "disk_usage_mb": self._disk_usage,
            "invalidations": self._invalidation_count,
            "evictions": self._eviction_count,
            "statistics": self.get_statistics().__dict__ if self._statistics else None,
        }


# ---- Part 14: Public API -----------------------------------------------

__all__ = [
    "CacheManager",
    "CacheSettings",
    "CacheReport",
    "CacheEvent",
    "CacheState",
    "CacheType",
    "InvalidationReason",
    "CacheRegistry",
    "CacheDescriptor",
]