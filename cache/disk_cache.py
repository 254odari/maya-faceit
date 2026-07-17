
"""
cache/disk_cache.py

Persistent Storage Layer for Maya FaceIT.

This module provides the persistent cache backend, storing serialized cache
data on disk between Maya sessions. It supports serialization (JSON, pickle,
binary), compression (ZIP, GZIP, LZMA), versioning, integrity verification,
atomic writes, cleanup, backup, and recovery.

Responsibilities:
- Save, load, and delete cache entries from disk.
- Manage cache directories and file structure.
- Serialize and deserialize cache data (JSON, pickle, binary).
- Compress and decompress cache files (ZIP, GZIP, LZMA).
- Track plugin and schema versions for cache compatibility.
- Verify file integrity using checksums (SHA256, CRC32).
- Cleanup old or expired cache files.
- Backup and restore cache state.
- Provide diagnostics and statistics.

Dependencies:
- cache_base.py, cache_utils.py, cache_statistics.py.
- pathlib, shutil, tempfile, hashlib, json, pickle, gzip, zipfile, lzma, threading, time, typing.
- Maya: no direct Maya dependency (generic).

The module is generic and does not know about meshes, blendshapes, or projects.
"""

from __future__ import annotations

import base64
import gc
import hashlib
import json
import logging
import os
import pickle
import shutil
import tempfile
import threading
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import (
    Any, Dict, List, Optional, Set, Tuple, Union, Callable, Iterator,
    TypeVar, Generic, cast, overload, Iterable, BinaryIO
)

# Optional compression libraries
try:
    import lzma
    HAS_LZMA = True
except ImportError:
    HAS_LZMA = False

try:
    import zstandard
    HAS_ZSTD = True
except ImportError:
    HAS_ZSTD = False

# Optional MessagePack for faster serialization
try:
    import msgpack
    HAS_MSGPACK = True
except ImportError:
    HAS_MSGPACK = False

# Base cache imports (with fallback)
try:
    from .cache_base import BaseCache, CacheSettings, CacheEntry, CacheMetadata, CacheStatus
    from .cache_utils import get_cache_key, hash_data, validate_cache_key, sanitize_key
    from .cache_statistics import CacheStatistics
except ImportError:
    # Minimal fallback
    class BaseCache:
        def __init__(self, name, cache_type, settings=None):
            self.name = name
            self.cache_type = cache_type
            self._storage = {}
            self._lock = threading.RLock()
            self._statistics = None
        def store(self, key, value): pass
        def get(self, key): return None
        def delete(self, key): pass
        def clear(self): pass
        def contains(self, key): return False
        def size(self): return 0
        def statistics(self): return CacheStatistics()
        def memory_usage(self): return 0.0
        def export_data(self): return {}
        def import_data(self, data): pass
    class CacheSettings:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
    class CacheEntry: pass
    class CacheMetadata: pass
    class CacheStatus(Enum):
        EMPTY = "empty"
        READY = "ready"
    def get_cache_key(*args, **kwargs): return str(args)
    def hash_data(data): return str(hash(str(data)))
    def validate_cache_key(key): return isinstance(key, str) and len(key) > 0
    def sanitize_key(key): return key.strip()
    class CacheStatistics:
        def __init__(self):
            self.hits = 0
            self.misses = 0
            self.hit_rate = 0.0
            self.memory_usage_mb = 0.0
            self.total_entries = 0
            self.by_type = {}
            self.invalidations = 0
            self.evictions = 0

logger = logging.getLogger(__name__)

# ---- Part 2: Constants & Enumerations --------------------------------

class DiskCacheState(Enum):
    """State of the disk cache."""
    READY = "ready"
    LOADING = "loading"
    WRITING = "writing"
    CLEANING = "cleaning"
    CORRUPTED = "corrupted"
    OFFLINE = "offline"


class CompressionType(Enum):
    """Compression algorithms."""
    NONE = "none"
    ZIP = "zip"
    GZIP = "gzip"
    LZMA = "lzma"
    ZSTD = "zstd"


class SerializationType(Enum):
    """Serialization formats."""
    JSON = "json"
    PICKLE = "pickle"
    MSGPACK = "msgpack"
    BINARY = "binary"
    CUSTOM = "custom"


class CacheScope(Enum):
    """Scope of the cache."""
    GLOBAL = "global"      # Shared across all projects
    PROJECT = "project"    # Per-project cache
    SCENE = "scene"        # Per-scene cache
    USER = "user"          # Per-user cache
    SESSION = "session"    # Temporary, cleared on session end


# ---- Part 3: Data Models ----------------------------------------------

@dataclass
class CacheManifest:
    """Manifest entry for a cached file."""
    key: str
    filename: str
    size_bytes: int
    compressed_size: int
    checksum: str
    created: float
    modified: float
    version: str          # plugin version
    schema_version: int
    serialization_type: str
    compression_type: str
    scope: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DiskCacheEntry:
    """Complete entry representing a cached object on disk."""
    key: str
    data: Any               # deserialized object
    manifest: CacheManifest


@dataclass
class DiskStatistics:
    """Statistics for disk cache."""
    total_entries: int = 0
    total_size_bytes: int = 0
    total_compressed_size: int = 0
    compression_ratio: float = 1.0
    hit_count: int = 0
    miss_count: int = 0
    write_count: int = 0
    delete_count: int = 0
    cleanups: int = 0
    backups: int = 0
    restores: int = 0


@dataclass
class DiskReport:
    """Diagnostic report."""
    success: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    statistics: Optional[DiskStatistics] = None
    details: Dict[str, Any] = field(default_factory=dict)


# ---- Part 4: Disk Cache Manager --------------------------------------

class DiskCache(BaseCache):
    """
    Persistent cache on disk with serialization, compression, and integrity.
    """

    def __init__(
        self,
        name: str = "disk_cache",
        cache_root: Optional[Union[str, Path]] = None,
        scope: CacheScope = CacheScope.PROJECT,
        serialization_type: SerializationType = SerializationType.JSON,
        compression_type: CompressionType = CompressionType.GZIP,
        plugin_version: str = "1.0.0",
        schema_version: int = 1,
        max_cache_size_mb: Optional[float] = None,
        max_age_days: Optional[int] = None,
        settings: Optional[CacheSettings] = None,
    ):
        """
        Initialize disk cache.

        Args:
            name: Cache name.
            cache_root: Root directory for cache files. If None, uses default.
            scope: Cache scope (global, project, scene, user, session).
            serialization_type: Serialization format.
            compression_type: Compression algorithm.
            plugin_version: Plugin version for compatibility.
            schema_version: Schema version for compatibility.
            max_cache_size_mb: Maximum total cache size in MB (optional).
            max_age_days: Maximum age of cache files in days (optional).
            settings: Additional cache settings.
        """
        super().__init__(name=name, cache_type="disk", settings=settings)
        self._scope = scope
        self._serialization_type = serialization_type
        self._compression_type = compression_type
        self._plugin_version = plugin_version
        self._schema_version = schema_version
        self._max_cache_size_mb = max_cache_size_mb
        self._max_age_days = max_age_days

        # Directory setup
        self._cache_root = Path(cache_root) if cache_root else self._default_cache_root()
        self._cache_dir = self._cache_root / name
        self._temp_dir = self._cache_dir / "temp"
        self._backup_dir = self._cache_dir / "backup"

        # Internal state
        self._manifest: Dict[str, CacheManifest] = {}  # key -> manifest
        self._statistics = DiskStatistics()
        self._state = DiskCacheState.READY
        self._lock = threading.RLock()

        # Ensure directories exist
        self._init_directories()

        # Load existing manifest
        self._load_manifest()

        logger.info(f"DiskCache '{name}' initialized at {self._cache_dir}")

    # ---- Directory Management ----

    def _default_cache_root(self) -> Path:
        """Return default cache root directory."""
        # Use user's app data directory
        home = Path.home()
        if os.name == 'nt':  # Windows
            appdata = home / 'AppData' / 'Local'
        else:
            appdata = home / '.cache'
        return appdata / 'maya_faceit' / 'cache'

    def _init_directories(self) -> None:
        """Create required directories."""
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._temp_dir.mkdir(exist_ok=True)
        self._backup_dir.mkdir(exist_ok=True)

    def get_cache_path(self, key: str) -> Path:
        """Return the file path for a given cache key."""
        # Use a safe filename: hash the key to avoid filesystem issues
        safe_key = hashlib.sha256(key.encode('utf-8')).hexdigest()
        ext = self._get_file_extension()
        return self._cache_dir / f"{safe_key}.{ext}"

    def _get_file_extension(self) -> str:
        """Return file extension based on serialization/compression."""
        ext = {
            SerializationType.JSON: "json",
            SerializationType.PICKLE: "pkl",
            SerializationType.MSGPACK: "msgpack",
            SerializationType.BINARY: "bin",
        }.get(self._serialization_type, "dat")
        if self._compression_type == CompressionType.GZIP:
            ext += ".gz"
        elif self._compression_type == CompressionType.ZIP:
            ext += ".zip"
        elif self._compression_type == CompressionType.LZMA:
            ext += ".xz"
        elif self._compression_type == CompressionType.ZSTD:
            ext += ".zst"
        return ext

    # ---- Manifest Management ----

    def _manifest_file(self) -> Path:
        """Return path to the manifest file."""
        return self._cache_dir / "manifest.json"

    def _load_manifest(self) -> None:
        """Load manifest from disk."""
        manifest_path = self._manifest_file()
        if not manifest_path.exists():
            self._manifest = {}
            return
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self._manifest = {k: CacheManifest(**v) for k, v in data.items()}
            logger.debug(f"Loaded manifest with {len(self._manifest)} entries")
        except Exception as e:
            logger.warning(f"Failed to load manifest: {e}")
            self._manifest = {}
            self._state = DiskCacheState.CORRUPTED

    def _save_manifest(self) -> None:
        """Save manifest to disk."""
        manifest_path = self._manifest_file()
        try:
            # Atomic write: write to temp then rename
            temp_path = manifest_path.with_suffix(".tmp")
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump({k: v.__dict__ for k, v in self._manifest.items()}, f, indent=2)
            temp_path.rename(manifest_path)
        except Exception as e:
            logger.error(f"Failed to save manifest: {e}")
            raise IOError(f"Failed to save manifest: {e}")

    def _update_manifest(self, key: str, manifest: CacheManifest) -> None:
        """Add or update a manifest entry."""
        with self._lock:
            self._manifest[key] = manifest
            self._save_manifest()

    def _remove_manifest(self, key: str) -> None:
        """Remove a manifest entry."""
        with self._lock:
            if key in self._manifest:
                del self._manifest[key]
                self._save_manifest()

    # ---- Serialization ----

    def _serialize(self, data: Any) -> bytes:
        """Serialize data to bytes."""
        if self._serialization_type == SerializationType.JSON:
            # Convert data to JSON if not already string-like
            if isinstance(data, (dict, list)):
                return json.dumps(data, default=str).encode('utf-8')
            else:
                return json.dumps({"data": data}, default=str).encode('utf-8')
        elif self._serialization_type == SerializationType.PICKLE:
            return pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)
        elif self._serialization_type == SerializationType.MSGPACK:
            if HAS_MSGPACK:
                return msgpack.packb(data, default=self._msgpack_default)
            else:
                logger.warning("msgpack not available, falling back to JSON")
                return json.dumps(data, default=str).encode('utf-8')
        elif self._serialization_type == SerializationType.BINARY:
            # Use pickle for arbitrary Python objects
            return pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)
        else:
            # Fallback to JSON
            return json.dumps(data, default=str).encode('utf-8')

    def _deserialize(self, data: bytes) -> Any:
        """Deserialize bytes to Python object."""
        if self._serialization_type == SerializationType.JSON:
            try:
                return json.loads(data.decode('utf-8'))
            except json.JSONDecodeError:
                # Try as JSON with data wrapper
                return json.loads(data.decode('utf-8'))
        elif self._serialization_type == SerializationType.PICKLE:
            try:
                return pickle.loads(data)
            except Exception as e:
                logger.error(f"Pickle deserialization failed: {e}")
                raise
        elif self._serialization_type == SerializationType.MSGPACK:
            if HAS_MSGPACK:
                try:
                    return msgpack.unpackb(data, raw=False, object_hook=self._msgpack_hook)
                except Exception as e:
                    logger.error(f"msgpack deserialization failed: {e}")
                    raise
            else:
                return json.loads(data.decode('utf-8'))
        elif self._serialization_type == SerializationType.BINARY:
            try:
                return pickle.loads(data)
            except Exception as e:
                logger.error(f"Binary deserialization failed: {e}")
                raise
        else:
            return json.loads(data.decode('utf-8'))

    def _msgpack_default(self, obj: Any) -> Any:
        """Default serialization for msgpack."""
        if isinstance(obj, (set, frozenset)):
            return list(obj)
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        return str(obj)

    def _msgpack_hook(self, obj: Any) -> Any:
        """Hook for msgpack deserialization."""
        return obj

    # ---- Compression ----

    def _compress(self, data: bytes) -> bytes:
        """Compress data bytes."""
        if self._compression_type == CompressionType.NONE:
            return data
        elif self._compression_type == CompressionType.GZIP:
            import gzip
            return gzip.compress(data)
        elif self._compression_type == CompressionType.ZIP:
            import zipfile
            import io
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('data', data)
            return buffer.getvalue()
        elif self._compression_type == CompressionType.LZMA:
            if HAS_LZMA:
                return lzma.compress(data)
            else:
                logger.warning("LZMA not available, using no compression")
                return data
        elif self._compression_type == CompressionType.ZSTD:
            if HAS_ZSTD:
                cctx = zstandard.ZstdCompressor()
                return cctx.compress(data)
            else:
                logger.warning("ZSTD not available, using no compression")
                return data
        else:
            return data

    def _decompress(self, data: bytes) -> bytes:
        """Decompress data bytes."""
        if self._compression_type == CompressionType.NONE:
            return data
        elif self._compression_type == CompressionType.GZIP:
            import gzip
            try:
                return gzip.decompress(data)
            except Exception as e:
                logger.error(f"GZIP decompression failed: {e}")
                raise
        elif self._compression_type == CompressionType.ZIP:
            import zipfile
            import io
            try:
                with zipfile.ZipFile(io.BytesIO(data)) as zf:
                    return zf.read('data')
            except Exception as e:
                logger.error(f"ZIP decompression failed: {e}")
                raise
        elif self._compression_type == CompressionType.LZMA:
            if HAS_LZMA:
                try:
                    return lzma.decompress(data)
                except Exception as e:
                    logger.error(f"LZMA decompression failed: {e}")
                    raise
            else:
                return data
        elif self._compression_type == CompressionType.ZSTD:
            if HAS_ZSTD:
                dctx = zstandard.ZstdDecompressor()
                try:
                    return dctx.decompress(data)
                except Exception as e:
                    logger.error(f"ZSTD decompression failed: {e}")
                    raise
            else:
                return data
        else:
            return data

    # ---- Integrity Verification ----

    def _compute_checksum(self, data: bytes) -> str:
        """Compute SHA256 checksum of data."""
        return hashlib.sha256(data).hexdigest()

    def _verify_checksum(self, data: bytes, expected: str) -> bool:
        """Verify checksum of data."""
        actual = self._compute_checksum(data)
        return actual == expected

    # ---- Core Operations ----

    def save(self, key: str, data: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Save data to disk cache.

        Args:
            key: Cache key.
            data: Data to cache.
            metadata: Additional metadata for manifest.
        """
        if not validate_cache_key(key):
            raise ValueError(f"Invalid cache key: {key}")

        with self._lock:
            # Serialize
            try:
                serialized = self._serialize(data)
            except Exception as e:
                raise IOError(f"Serialization failed: {e}")

            # Compress
            try:
                compressed = self._compress(serialized)
            except Exception as e:
                raise IOError(f"Compression failed: {e}")

            # Compute checksum
            checksum = self._compute_checksum(compressed)

            # Atomic write
            file_path = self.get_cache_path(key)
            temp_path = self._temp_dir / f"{file_path.name}.tmp"
            try:
                with open(temp_path, 'wb') as f:
                    f.write(compressed)
                temp_path.rename(file_path)
            except Exception as e:
                raise IOError(f"Failed to write cache file: {e}")

            # Update manifest
            manifest = CacheManifest(
                key=key,
                filename=file_path.name,
                size_bytes=len(serialized),
                compressed_size=len(compressed),
                checksum=checksum,
                created=time.time(),
                modified=time.time(),
                version=self._plugin_version,
                schema_version=self._schema_version,
                serialization_type=self._serialization_type.value,
                compression_type=self._compression_type.value,
                scope=self._scope.value,
                metadata=metadata or {}
            )
            self._update_manifest(key, manifest)
            self._statistics.write_count += 1

            # Update total size
            self._update_total_size()

            # Enforce size limit if set
            if self._max_cache_size_mb is not None:
                self._enforce_size_limit()

            logger.debug(f"Saved cache entry: {key} ({file_path})")

    def load(self, key: str, default: Any = None) -> Any:
        """
        Load data from disk cache.

        Args:
            key: Cache key.
            default: Value to return if not found.

        Returns:
            Cached data or default.
        """
        if not validate_cache_key(key):
            raise ValueError(f"Invalid cache key: {key}")

        with self._lock:
            # Check manifest
            manifest = self._manifest.get(key)
            if not manifest:
                self._statistics.miss_count += 1
                return default

            # Check expiration (by age)
            if self._max_age_days is not None:
                age_days = (time.time() - manifest.created) / (24 * 3600)
                if age_days > self._max_age_days:
                    self.delete(key)
                    self._statistics.miss_count += 1
                    return default

            # Check version compatibility
            if manifest.version != self._plugin_version or manifest.schema_version != self._schema_version:
                # Incompatible version: delete and treat as miss
                self.delete(key)
                self._statistics.miss_count += 1
                return default

            # Read file
            file_path = self.get_cache_path(key)
            if not file_path.exists():
                # Remove stale manifest entry
                self._remove_manifest(key)
                self._statistics.miss_count += 1
                return default

            try:
                with open(file_path, 'rb') as f:
                    raw_data = f.read()
            except Exception as e:
                logger.error(f"Failed to read cache file: {e}")
                self._statistics.miss_count += 1
                return default

            # Verify checksum
            if not self._verify_checksum(raw_data, manifest.checksum):
                logger.error(f"Checksum mismatch for {key}, deleting entry")
                self.delete(key)
                self._statistics.miss_count += 1
                return default

            # Decompress
            try:
                serialized = self._decompress(raw_data)
            except Exception as e:
                logger.error(f"Decompression failed for {key}: {e}")
                self.delete(key)
                self._statistics.miss_count += 1
                return default

            # Deserialize
            try:
                data = self._deserialize(serialized)
            except Exception as e:
                logger.error(f"Deserialization failed for {key}: {e}")
                self.delete(key)
                self._statistics.miss_count += 1
                return default

            # Update hit count
            self._statistics.hit_count += 1
            logger.debug(f"Loaded cache entry: {key}")
            return data

    def delete(self, key: str) -> bool:
        """
        Delete a cache entry from disk.

        Args:
            key: Cache key.

        Returns:
            True if deleted, False if not found.
        """
        if not validate_cache_key(key):
            return False

        with self._lock:
            if key not in self._manifest:
                return False

            # Remove file
            file_path = self.get_cache_path(key)
            if file_path.exists():
                try:
                    file_path.unlink()
                except Exception as e:
                    logger.warning(f"Failed to delete cache file {file_path}: {e}")

            # Remove manifest
            self._remove_manifest(key)
            self._statistics.delete_count += 1
            self._update_total_size()
            logger.debug(f"Deleted cache entry: {key}")
            return True

    def exists(self, key: str) -> bool:
        """Check if a cache entry exists and is valid."""
        if not validate_cache_key(key):
            return False
        with self._lock:
            manifest = self._manifest.get(key)
            if not manifest:
                return False
            # Check age
            if self._max_age_days is not None:
                age_days = (time.time() - manifest.created) / (24 * 3600)
                if age_days > self._max_age_days:
                    return False
            # Check version
            if manifest.version != self._plugin_version or manifest.schema_version != self._schema_version:
                return False
            # Check file existence
            file_path = self.get_cache_path(key)
            if not file_path.exists():
                return False
            return True

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            # Remove all files
            for key in list(self._manifest.keys()):
                self.delete(key)
            # Also remove any orphan files
            self._clean_orphan_files()
            self._statistics = DiskStatistics()
            self._manifest.clear()
            self._save_manifest()
            logger.info(f"Cache '{self.name}' cleared")

    def size(self) -> int:
        """Return number of cache entries."""
        with self._lock:
            return len(self._manifest)

    # ---- Size and Age Management ----

    def _update_total_size(self) -> None:
        """Recalculate total cache size."""
        total = 0
        for manifest in self._manifest.values():
            total += manifest.compressed_size
        self._statistics.total_size_bytes = total

    def get_total_size_mb(self) -> float:
        """Return total cache size in MB."""
        with self._lock:
            return self._statistics.total_size_bytes / (1024.0 * 1024.0)

    def _enforce_size_limit(self) -> None:
        """Evict entries until total size is within limit."""
        if self._max_cache_size_mb is None:
            return
        limit_bytes = int(self._max_cache_size_mb * 1024 * 1024)
        while self._statistics.total_size_bytes > limit_bytes and self._manifest:
            # Find oldest entry (by created time)
            oldest = min(self._manifest.values(), key=lambda m: m.created)
            self.delete(oldest.key)
            self._statistics.cleanups += 1

    def _clean_orphan_files(self) -> None:
        """Remove files not in manifest."""
        existing_files = set(self._cache_dir.glob("*"))
        manifest_files = {self._cache_dir / m.filename for m in self._manifest.values()}
        for f in existing_files:
            if f.is_file() and f.name != "manifest.json" and f.suffix != ".tmp":
                if f not in manifest_files:
                    try:
                        f.unlink()
                        logger.debug(f"Removed orphan file: {f}")
                    except Exception as e:
                        logger.warning(f"Failed to remove orphan file {f}: {e}")

    def cleanup(self, max_age_days: Optional[int] = None) -> int:
        """
        Remove old cache entries based on age.

        Args:
            max_age_days: Age limit in days (overrides class setting).

        Returns:
            Number of entries removed.
        """
        age_limit = max_age_days if max_age_days is not None else self._max_age_days
        if age_limit is None:
            return 0

        with self._lock:
            removed = 0
            now = time.time()
            for key, manifest in list(self._manifest.items()):
                age_days = (now - manifest.created) / (24 * 3600)
                if age_days > age_limit:
                    self.delete(key)
                    removed += 1
            self._statistics.cleanups += removed
            self._clean_orphan_files()
            return removed

    def vacuum(self) -> int:
        """
        Remove orphaned files and compact manifest.

        Returns:
            Number of orphan files removed.
        """
        with self._lock:
            before = len(self._manifest)
            self._clean_orphan_files()
            # Remove manifest entries for missing files
            for key, manifest in list(self._manifest.items()):
                if not (self._cache_dir / manifest.filename).exists():
                    self._remove_manifest(key)
            after = len(self._manifest)
            return before - after

    # ---- Backup and Recovery ----

    def backup(self, backup_path: Optional[Union[str, Path]] = None) -> Path:
        """
        Create a backup of the entire cache directory.

        Args:
            backup_path: Optional custom backup path.

        Returns:
            Path to the backup archive.
        """
        if backup_path is None:
            # Use backup directory with timestamp
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            backup_path = self._backup_dir / f"cache_backup_{timestamp}.zip"
        else:
            backup_path = Path(backup_path)

        # Ensure the backup directory exists
        backup_path.parent.mkdir(parents=True, exist_ok=True)

        # Save manifest first to ensure consistency
        self._save_manifest()

        # Create a zip archive of the cache directory
        import zipfile
        try:
            with zipfile.ZipFile(backup_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                for item in self._cache_dir.rglob('*'):
                    if item.is_file() and item.suffix != '.tmp':
                        zf.write(item, item.relative_to(self._cache_dir))
            self._statistics.backups += 1
            logger.info(f"Backup created at {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            raise

    def restore_backup(self, backup_path: Union[str, Path]) -> bool:
        """
        Restore cache from a backup archive.

        Args:
            backup_path: Path to backup archive.

        Returns:
            True if restore succeeded, False otherwise.
        """
        backup_path = Path(backup_path)
        if not backup_path.exists():
            logger.error(f"Backup file not found: {backup_path}")
            return False

        import zipfile
        try:
            # Clear current cache
            self.clear()
            # Extract backup
            with zipfile.ZipFile(backup_path, 'r') as zf:
                zf.extractall(self._cache_dir)
            # Reload manifest
            self._load_manifest()
            self._statistics.restores += 1
            logger.info(f"Restored backup from {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to restore backup: {e}")
            return False

    # ---- Statistics ----

    def statistics(self) -> CacheStatistics:
        """Return aggregated statistics."""
        stats = super().statistics()
        with self._lock:
            stats.total_entries = len(self._manifest)
            stats.memory_usage_mb = self.get_total_size_mb()
            stats.by_type["disk_hits"] = self._statistics.hit_count
            stats.by_type["disk_misses"] = self._statistics.miss_count
            stats.by_type["disk_writes"] = self._statistics.write_count
            stats.by_type["disk_deletes"] = self._statistics.delete_count
            stats.by_type["disk_cleanups"] = self._statistics.cleanups
            stats.by_type["disk_backups"] = self._statistics.backups
            stats.by_type["disk_restores"] = self._statistics.restores
        return stats

    def get_disk_statistics(self) -> DiskStatistics:
        """Return detailed disk statistics."""
        with self._lock:
            return self._statistics

    # ---- Diagnostics ----

    def validate(self) -> DiskReport:
        """Validate cache integrity."""
        report = DiskReport(success=True)
        with self._lock:
            for key, manifest in self._manifest.items():
                file_path = self._cache_dir / manifest.filename
                if not file_path.exists():
                    report.errors.append(f"Manifest entry '{key}' references missing file '{manifest.filename}'")
                    report.success = False
                else:
                    try:
                        with open(file_path, 'rb') as f:
                            data = f.read()
                        if not self._verify_checksum(data, manifest.checksum):
                            report.errors.append(f"Checksum mismatch for '{key}'")
                            report.success = False
                    except Exception as e:
                        report.errors.append(f"Error reading file for '{key}': {e}")
                        report.success = False
            # Check orphan files
            orphan_files = []
            for f in self._cache_dir.glob('*'):
                if f.is_file() and f.name not in ['manifest.json'] and f.suffix != '.tmp':
                    if not any(m.filename == f.name for m in self._manifest.values()):
                        orphan_files.append(f.name)
            if orphan_files:
                report.warnings.append(f"Found orphan files: {orphan_files}")
            # Check manifest integrity
            manifest_path = self._manifest_file()
            if not manifest_path.exists():
                report.errors.append("Manifest file missing")
                report.success = False
            # Statistics
            report.statistics = self._statistics
        return report

    # ---- Utility Methods ----

    def get_cache_directory(self) -> Path:
        """Return the cache directory path."""
        return self._cache_dir

    def get_backup_directory(self) -> Path:
        """Return the backup directory path."""
        return self._backup_dir

    def get_manifest(self) -> Dict[str, CacheManifest]:
        """Return a copy of the manifest."""
        with self._lock:
            return dict(self._manifest)

    # ---- Override BaseCache Methods ----

    def store(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Alias for save."""
        self.save(key, value, metadata={"ttl": ttl} if ttl else None)

    def get(self, key: str, default: Any = None) -> Any:
        """Alias for load."""
        return self.load(key, default)


# ---- Part 15: Utilities ----------------------------------------------

def create_disk_cache(
    name: str = "disk_cache",
    cache_root: Optional[Union[str, Path]] = None,
    scope: CacheScope = CacheScope.PROJECT,
    serialization: SerializationType = SerializationType.JSON,
    compression: CompressionType = CompressionType.GZIP,
    max_size_mb: Optional[float] = 512.0,
    max_age_days: Optional[int] = 30,
) -> DiskCache:
    """
    Factory function to create a DiskCache with common settings.

    Args:
        name: Cache name.
        cache_root: Root directory for cache.
        scope: Cache scope.
        serialization: Serialization format.
        compression: Compression algorithm.
        max_size_mb: Maximum total cache size in MB.
        max_age_days: Maximum age of cache files in days.

    Returns:
        Configured DiskCache instance.
    """
    return DiskCache(
        name=name,
        cache_root=cache_root,
        scope=scope,
        serialization_type=serialization,
        compression_type=compression,
        max_cache_size_mb=max_size_mb,
        max_age_days=max_age_days,
    )


# ---- Part 16: Public API -----------------------------------------------

__all__ = [
    "DiskCache",
    "DiskCacheEntry",
    "CacheManifest",
    "DiskStatistics",
    "DiskReport",
    "DiskCacheState",
    "CompressionType",
    "SerializationType",
    "CacheScope",
    "create_disk_cache",
]
