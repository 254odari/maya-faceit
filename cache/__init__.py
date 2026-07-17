"""
cache/__init__.py

Cache System for Maya FaceIT.

This package provides a comprehensive caching system with multiple layers:
- MemoryCache: high-speed RAM-based cache with LRU/FIFO/LFU eviction.
- DiskCache: persistent cache on disk with compression and serialization.
- MeshCache: specialized cache for mesh data (vertices, topology, symmetry).
- LandmarkCache: specialized cache for facial landmarks and tracking data.
- BlendshapeCache: specialized cache for blendshape nodes, targets, weights, deltas.
- ProjectCache: high-level cache capturing the entire Faceit project state.
- CacheManager: orchestrates all caches and provides a unified interface.
- CacheStatisticsManager: collects and reports cache performance metrics.

The package also provides utilities, exceptions, and base classes.

All public APIs are re‑exported from this module for convenient access.
"""

from __future__ import annotations

import logging
from typing import Dict, Any

# ---- Part 1: Version & Metadata -----------------------------------------

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"
__license__ = "MIT"

PACKAGE_NAME = "maya_faceit.cache"
VERSION = __version__
AUTHOR = __author__
LICENSE = __license__

# ---- Part 2: Configure Logging ------------------------------------------

logger = logging.getLogger(__name__)

# ---- Part 3: Public Imports ---------------------------------------------

# 3.1 Exceptions (must be imported first)
from .cache_exceptions import (
    FaceitCacheError,
    CacheConfigurationError,
    CacheInitializationError,
    CacheSettingsError,
    CacheRegistrationError,
    CacheError,
    CacheNotFoundError,
    CacheExistsError,
    CacheKeyError,
    CacheLookupError,
    CacheStateError,
    CacheBusyError,
    CacheTimeoutError,
    CacheInvalidatedError,
    MemoryCacheError,
    MemoryLimitExceededError,
    MemoryAllocationError,
    MemoryEvictionError,
    MemoryExpiredError,
    WeakReferenceError,
    DiskCacheError,
    CacheFileError,
    CacheFileMissingError,
    CacheWriteError,
    CacheReadError,
    CachePermissionError,
    CacheCorruptedError,
    CacheCompressionError,
    MeshCacheError,
    MeshNotCachedError,
    MeshTopologyChangedError,
    MeshDeletedError,
    MeshUUIDError,
    MeshValidationError,
    LandmarkCacheError,
    LandmarkNotFoundError,
    InvalidLandmarkError,
    LandmarkTrackingLostError,
    LandmarkMappingError,
    BlendshapeCacheError,
    BlendshapeMissingError,
    BlendshapeTargetError,
    BlendshapeWeightError,
    BlendshapeDriverError,
    BlendshapeTopologyError,
    ProjectCacheError,
    ProjectNotLoadedError,
    ProjectSaveError,
    ProjectRestoreError,
    ProjectVersionError,
    ProjectSnapshotError,
    SerializationError,
    DeserializationError,
    JsonSerializationError,
    BinarySerializationError,
    CompressionError,
    DecompressionError,
    ValidationError,
    InvalidCacheEntryError,
    InvalidCacheKeyError,
    InvalidCachePathError,
    InvalidChecksumError,
    InvalidUUIDError,
    CacheVersionError,
    SchemaMismatchError,
    PluginVersionMismatchError,
    MigrationRequiredError,
    CacheDirectoryError,
    CacheManifestError,
    BackupError,
    RestoreError,
    AtomicWriteError,
    CacheRuntimeError,
    CacheLockError,
    CacheDeadlockError,
    CacheThreadError,
    CacheInterruptedError,
    format_exception,
    exception_to_dict,
    exception_from_dict,
    error_summary,
)

# 3.2 Base Classes
from .cache_base import (
    BaseCache,
    CacheEntry,
    CacheMetadata,
    CacheSettings,
    CacheStatus,
    CacheAction,
    ExpirationPolicy,
)

# 3.3 Backends
from .memory_cache import (
    MemoryCache,
    MemoryEntry,
    MemoryLimits,
    EvictionRecord,
    MemoryEvent,
    MemoryState,
    EvictionPolicy,
    CachePriority,
    create_memory_cache,
)

from .disk_cache import (
    DiskCache,
    DiskCacheEntry,
    CacheManifest,
    DiskStatistics,
    DiskReport,
    DiskCacheState,
    CompressionType,
    SerializationType,
    CacheScope,
    create_disk_cache,
)

# 3.4 Specialized Caches
from .mesh_cache import (
    MeshCache,
    MeshCacheEntry,
    BoundingBoxInfo,
    SymmetryInfo,
    TopologyInfo,
    MeshDataType,
    CoordinateSpace,
    get_mesh_topology_hash,
)

from .landmark_cache import (
    LandmarkCache,
    LandmarkFrame,
    LandmarkPoint,
    LandmarkStatistics,
    LandmarkReport,
    HeadPoseData,
    FacialRegionData,
    TrackingHistory,
    LandmarkSource,
    LandmarkSpace,
    TrackingState,
    FacialRegion,
    convert_landmark_space,
    interpolate_landmarks,
)

from .blendshape_cache import (
    BlendshapeCache,
    BlendshapeNodeInfo,
    TargetInfo,
    WeightInfo,
    DeltaInfo,
    CorrectiveInfo,
    InbetweenInfo,
    ARKitInfo,
    PoseInfo,
    RuntimeInfo,
    BlendshapeStatistics,
    BlendshapeReport,
    BlendshapeDataType,
    EvaluationMode,
    BlendshapeState,
    get_blendshape_cache,
    invalidate_blendshape_cache,
    get_cached_weight,
    set_cached_weight,
)

from .project_cache import (
    ProjectCache,
    ProjectCacheEntry,
    ProjectMetadata,
    CharacterData,
    RigData,
    AnimationData,
    PreferencesData,
    UIStateData,
    VersionInfo,
    ProjectState,
    SaveMode,
    CacheVersionState,
    get_project_cache,
)

# 3.5 Manager
from .cache_manager import (
    CacheManager,
    CacheSettings as ManagerCacheSettings,
    CacheState as ManagerCacheState,
    CacheType,
    InvalidationReason,
    CacheRegistry,
    CacheDescriptor,
    CacheReport,
)

# 3.6 Statistics
from .cache_statistics import (
    CacheStatisticsManager,
    CacheMetrics,
    AggregatedStatistics,
    StatisticType,
    MetricCategory,
    ReportFormat,
    format_percentage,
    format_size_mb,
    format_time_ms,
)

# 3.7 Utilities
from .cache_utils import (
    # Constants
    DEFAULT_HASH,
    DEFAULT_ENCODING,
    DEFAULT_CACHE_EXTENSION,
    DEFAULT_TIMEOUT,
    DEFAULT_RETRY_COUNT,
    DEFAULT_RETRY_DELAY,
    MAX_FILENAME_LENGTH,

    # Key Utilities
    generate_key,
    normalize_key,
    sanitize_key,
    join_key,
    split_key,
    random_key,

    # UUID Utilities
    new_uuid,
    validate_uuid,
    short_uuid,
    uuid_to_string,
    string_to_uuid,

    # Hash Utilities
    sha256,
    sha1,
    md5,
    crc32,
    hash_file,
    hash_object,
    hash_string,
    hash_bytes,

    # Serialization Helpers
    serialize_json,
    deserialize_json,
    serialize_pickle,
    deserialize_pickle,
    serialize_binary,
    deserialize_binary,
    deep_copy,
    clone,
    is_serializable,

    # Compression Helpers
    compress_gzip,
    decompress_gzip,
    compress_zlib,
    decompress_zlib,
    compress_lzma,
    decompress_lzma,
    compress_zstd,
    decompress_zstd,
    compress,
    decompress,
    compression_ratio,
    zip_folder,
    unzip_folder,

    # Time & Date Helpers
    now,
    utc_now,
    timestamp,
    utc_timestamp,
    elapsed,
    format_duration,
    is_expired,
    iso_to_timestamp,
    timestamp_to_iso,

    # Path Utilities
    ensure_directory,
    safe_filename,
    normalize_path,
    relative_path,
    absolute_path,
    temporary_file,
    temporary_directory,
    cache_directory,

    # Memory Utilities
    object_size,
    recursive_size,
    estimate_cache_size,
    memory_usage,

    # Validation Helpers
    is_valid_key,
    is_valid_path,
    is_valid_uuid,
    is_serializable,
    is_compressed,
    is_json,

    # Retry & Lock Helpers
    retry,
    with_lock,
    atomic_write,
    safe_remove,
    safe_move,
    safe_open,

    # Formatting Helpers
    format_bytes,
    format_time,
    format_percentage,
    format_rate,
    format_number,
    truncate_string,

    # Diagnostics Helpers
    system_info,
    python_version,
    maya_version,
    cache_environment,
    plugin_version,
)

# ---- Part 4: Factory Functions -----------------------------------------

def create_cache_manager(
    backend: str = "memory",
    max_size: int = 100,
    ttl: int = 3600,
    persistent: bool = False,
    cache_dir: str = "",
) -> CacheManager:
    """
    Create a new CacheManager with the specified backend.

    Args:
        backend: "memory" or "disk".
        max_size: Maximum number of entries (or memory limit in MB for disk).
        ttl: Time-to-live in seconds.
        persistent: For disk backend, whether to persist across sessions.
        cache_dir: Directory for disk backend.

    Returns:
        CacheManager instance.
    """
    return CacheManager(backend=backend, max_size=max_size, ttl=ttl,
                        persistent=persistent, cache_dir=cache_dir)

def create_stats_manager() -> CacheStatisticsManager:
    """Create a new CacheStatisticsManager instance."""
    return CacheStatisticsManager()

def get_default_cache_root() -> str:
    """Return the default cache root directory."""
    from .cache_utils import cache_directory
    return str(cache_directory(""))


# ---- Part 5: Package Information ---------------------------------------

def package_info() -> Dict[str, Any]:
    """
    Return package metadata and environment information.
    """
    return {
        "package": PACKAGE_NAME,
        "version": VERSION,
        "author": AUTHOR,
        "license": LICENSE,
        "submodules": [
            "cache_base",
            "cache_manager",
            "memory_cache",
            "disk_cache",
            "mesh_cache",
            "landmark_cache",
            "blendshape_cache",
            "project_cache",
            "cache_statistics",
            "cache_utils",
            "cache_exceptions",
        ],
    }


# ---- Part 6: Public API (__all__) ---------------------------------------

__all__ = [
    # ---- Metadata ----
    "PACKAGE_NAME",
    "VERSION",
    "AUTHOR",
    "LICENSE",

    # ---- Exceptions ----
    "FaceitCacheError",
    "CacheConfigurationError",
    "CacheInitializationError",
    "CacheSettingsError",
    "CacheRegistrationError",
    "CacheError",
    "CacheNotFoundError",
    "CacheExistsError",
    "CacheKeyError",
    "CacheLookupError",
    "CacheStateError",
    "CacheBusyError",
    "CacheTimeoutError",
    "CacheInvalidatedError",
    "MemoryCacheError",
    "MemoryLimitExceededError",
    "MemoryAllocationError",
    "MemoryEvictionError",
    "MemoryExpiredError",
    "WeakReferenceError",
    "DiskCacheError",
    "CacheFileError",
    "CacheFileMissingError",
    "CacheWriteError",
    "CacheReadError",
    "CachePermissionError",
    "CacheCorruptedError",
    "CacheCompressionError",
    "MeshCacheError",
    "MeshNotCachedError",
    "MeshTopologyChangedError",
    "MeshDeletedError",
    "MeshUUIDError",
    "MeshValidationError",
    "LandmarkCacheError",
    "LandmarkNotFoundError",
    "InvalidLandmarkError",
    "LandmarkTrackingLostError",
    "LandmarkMappingError",
    "BlendshapeCacheError",
    "BlendshapeMissingError",
    "BlendshapeTargetError",
    "BlendshapeWeightError",
    "BlendshapeDriverError",
    "BlendshapeTopologyError",
    "ProjectCacheError",
    "ProjectNotLoadedError",
    "ProjectSaveError",
    "ProjectRestoreError",
    "ProjectVersionError",
    "ProjectSnapshotError",
    "SerializationError",
    "DeserializationError",
    "JsonSerializationError",
    "BinarySerializationError",
    "CompressionError",
    "DecompressionError",
    "ValidationError",
    "InvalidCacheEntryError",
    "InvalidCacheKeyError",
    "InvalidCachePathError",
    "InvalidChecksumError",
    "InvalidUUIDError",
    "CacheVersionError",
    "SchemaMismatchError",
    "PluginVersionMismatchError",
    "MigrationRequiredError",
    "CacheDirectoryError",
    "CacheManifestError",
    "BackupError",
    "RestoreError",
    "AtomicWriteError",
    "CacheRuntimeError",
    "CacheLockError",
    "CacheDeadlockError",
    "CacheThreadError",
    "CacheInterruptedError",
    "format_exception",
    "exception_to_dict",
    "exception_from_dict",
    "error_summary",

    # ---- Base ----
    "BaseCache",
    "CacheEntry",
    "CacheMetadata",
    "CacheSettings",
    "CacheStatus",
    "CacheAction",
    "ExpirationPolicy",

    # ---- Memory ----
    "MemoryCache",
    "MemoryEntry",
    "MemoryLimits",
    "EvictionRecord",
    "MemoryEvent",
    "MemoryState",
    "EvictionPolicy",
    "CachePriority",
    "create_memory_cache",

    # ---- Disk ----
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

    # ---- Mesh ----
    "MeshCache",
    "MeshCacheEntry",
    "BoundingBoxInfo",
    "SymmetryInfo",
    "TopologyInfo",
    "MeshDataType",
    "CoordinateSpace",
    "get_mesh_topology_hash",

    # ---- Landmark ----
    "LandmarkCache",
    "LandmarkFrame",
    "LandmarkPoint",
    "LandmarkStatistics",
    "LandmarkReport",
    "HeadPoseData",
    "FacialRegionData",
    "TrackingHistory",
    "LandmarkSource",
    "LandmarkSpace",
    "TrackingState",
    "FacialRegion",
    "convert_landmark_space",
    "interpolate_landmarks",

    # ---- Blendshape ----
    "BlendshapeCache",
    "BlendshapeNodeInfo",
    "TargetInfo",
    "WeightInfo",
    "DeltaInfo",
    "CorrectiveInfo",
    "InbetweenInfo",
    "ARKitInfo",
    "PoseInfo",
    "RuntimeInfo",
    "BlendshapeStatistics",
    "BlendshapeReport",
    "BlendshapeDataType",
    "EvaluationMode",
    "BlendshapeState",
    "get_blendshape_cache",
    "invalidate_blendshape_cache",
    "get_cached_weight",
    "set_cached_weight",

    # ---- Project ----
    "ProjectCache",
    "ProjectCacheEntry",
    "ProjectMetadata",
    "CharacterData",
    "RigData",
    "AnimationData",
    "PreferencesData",
    "UIStateData",
    "VersionInfo",
    "ProjectState",
    "SaveMode",
    "CacheVersionState",
    "get_project_cache",

    # ---- Manager ----
    "CacheManager",
    "ManagerCacheSettings",
    "ManagerCacheState",
    "CacheType",
    "InvalidationReason",
    "CacheRegistry",
    "CacheDescriptor",
    "CacheReport",

    # ---- Statistics ----
    "CacheStatisticsManager",
    "CacheMetrics",
    "AggregatedStatistics",
    "StatisticType",
    "MetricCategory",
    "ReportFormat",
    "format_percentage",
    "format_size_mb",
    "format_time_ms",

    # ---- Utils ----
    "DEFAULT_HASH",
    "DEFAULT_ENCODING",
    "DEFAULT_CACHE_EXTENSION",
    "DEFAULT_TIMEOUT",
    "DEFAULT_RETRY_COUNT",
    "DEFAULT_RETRY_DELAY",
    "MAX_FILENAME_LENGTH",
    "generate_key",
    "normalize_key",
    "sanitize_key",
    "join_key",
    "split_key",
    "random_key",
    "new_uuid",
    "validate_uuid",
    "short_uuid",
    "uuid_to_string",
    "string_to_uuid",
    "sha256",
    "sha1",
    "md5",
    "crc32",
    "hash_file",
    "hash_object",
    "hash_string",
    "hash_bytes",
    "serialize_json",
    "deserialize_json",
    "serialize_pickle",
    "deserialize_pickle",
    "serialize_binary",
    "deserialize_binary",
    "deep_copy",
    "clone",
    "is_serializable",
    "compress_gzip",
    "decompress_gzip",
    "compress_zlib",
    "decompress_zlib",
    "compress_lzma",
    "decompress_lzma",
    "compress_zstd",
    "decompress_zstd",
    "compress",
    "decompress",
    "compression_ratio",
    "zip_folder",
    "unzip_folder",
    "now",
    "utc_now",
    "timestamp",
    "utc_timestamp",
    "elapsed",
    "format_duration",
    "is_expired",
    "iso_to_timestamp",
    "timestamp_to_iso",
    "ensure_directory",
    "safe_filename",
    "normalize_path",
    "relative_path",
    "absolute_path",
    "temporary_file",
    "temporary_directory",
    "cache_directory",
    "object_size",
    "recursive_size",
    "estimate_cache_size",
    "memory_usage",
    "is_valid_key",
    "is_valid_path",
    "is_valid_uuid",
    "is_serializable",
    "is_compressed",
    "is_json",
    "retry",
    "with_lock",
    "atomic_write",
    "safe_remove",
    "safe_move",
    "safe_open",
    "format_bytes",
    "format_time",
    "format_percentage",
    "format_rate",
    "format_number",
    "truncate_string",
    "system_info",
    "python_version",
    "maya_version",
    "cache_environment",
    "plugin_version",

    # ---- Factory Functions ----
    "create_cache_manager",
    "create_stats_manager",
    "get_default_cache_root",

    # ---- Package Info ----
    "package_info",
]