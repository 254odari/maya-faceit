"""
cache/cache_exceptions.py

Centralized Exception Hierarchy for the Caching Subsystem.

This module defines all cache-related exceptions used across the caching framework.
Every cache module (MemoryCache, DiskCache, MeshCache, BlendshapeCache, etc.)
should raise exceptions defined here instead of generic exceptions.

This provides:
- Consistent error handling.
- Clear error messages with context.
- Easier debugging and logging.
- Error codes for automation and UI reporting.
- Support for exception chaining.

The module has minimal dependencies and does not import any cache modules
to avoid circular imports.
"""

from __future__ import annotations

import traceback
from typing import Optional, Dict, Any, List

# ---- Part 1: Base Exceptions -------------------------------------------

class FaceitCacheError(Exception):
    """
    Root exception for all cache-related errors.

    All cache exceptions inherit from this class.
    """
    error_code: Optional[str] = None
    """Stable error code for logging and automation (e.g., 'CACHE-1001')."""

    def __init__(self, message: str, *args, **kwargs):
        self.message = message
        self.context: Dict[str, Any] = kwargs.get('context', {})
        super().__init__(message, *args)


# ---- Part 2: Configuration Exceptions ----------------------------------

class CacheConfigurationError(FaceitCacheError):
    """Raised when cache configuration is invalid."""
    error_code = "CACHE-1001"


class CacheInitializationError(FaceitCacheError):
    """Raised when a cache fails to initialize."""
    error_code = "CACHE-1002"


class CacheSettingsError(FaceitCacheError):
    """Raised when cache settings are invalid."""
    error_code = "CACHE-1003"


class CacheRegistrationError(FaceitCacheError):
    """Raised when registering a cache fails (duplicate name, etc.)."""
    error_code = "CACHE-1004"


# ---- Part 3: General Cache Exceptions ----------------------------------

class CacheError(FaceitCacheError):
    """General cache error (base for most cache operations)."""
    error_code = "CACHE-2001"


class CacheNotFoundError(CacheError):
    """Raised when a cache entry is not found."""
    error_code = "CACHE-2002"


class CacheExistsError(CacheError):
    """Raised when attempting to create a cache entry that already exists."""
    error_code = "CACHE-2003"


class CacheKeyError(CacheError):
    """Raised when a cache key is invalid."""
    error_code = "CACHE-2004"


class CacheLookupError(CacheError):
    """Raised when a cache lookup fails."""
    error_code = "CACHE-2005"


class CacheStateError(CacheError):
    """Raised when the cache is in an invalid state for an operation."""
    error_code = "CACHE-2006"


class CacheBusyError(CacheError):
    """Raised when a cache operation cannot proceed because the cache is busy."""
    error_code = "CACHE-2007"


class CacheTimeoutError(CacheError):
    """Raised when a cache operation times out."""
    error_code = "CACHE-2008"


class CacheInvalidatedError(CacheError):
    """Raised when an operation is attempted on an invalidated cache."""
    error_code = "CACHE-2009"


# ---- Part 4: Memory Cache Exceptions -----------------------------------

class MemoryCacheError(CacheError):
    """Base for memory cache errors."""
    error_code = "CACHE-3001"


class MemoryLimitExceededError(MemoryCacheError):
    """Raised when memory usage exceeds configured limit."""
    error_code = "CACHE-3002"


class MemoryAllocationError(MemoryCacheError):
    """Raised when memory allocation fails."""
    error_code = "CACHE-3003"


class MemoryEvictionError(MemoryCacheError):
    """Raised when an eviction operation fails."""
    error_code = "CACHE-3004"


class MemoryExpiredError(MemoryCacheError):
    """Raised when accessing an expired memory cache entry."""
    error_code = "CACHE-3005"


class WeakReferenceError(MemoryCacheError):
    """Raised when a weak reference is dead (object already garbage collected)."""
    error_code = "CACHE-3006"


# ---- Part 5: Disk Cache Exceptions -------------------------------------

class DiskCacheError(CacheError):
    """Base for disk cache errors."""
    error_code = "CACHE-4001"


class CacheFileError(DiskCacheError):
    """Raised for general file-related errors."""
    error_code = "CACHE-4002"


class CacheFileMissingError(DiskCacheError):
    """Raised when a cache file is missing."""
    error_code = "CACHE-4003"


class CacheWriteError(DiskCacheError):
    """Raised when writing to a cache file fails."""
    error_code = "CACHE-4004"


class CacheReadError(DiskCacheError):
    """Raised when reading from a cache file fails."""
    error_code = "CACHE-4005"


class CachePermissionError(DiskCacheError):
    """Raised when file permissions prevent a disk cache operation."""
    error_code = "CACHE-4006"


class CacheCorruptedError(DiskCacheError):
    """Raised when a cache file is corrupted."""
    error_code = "CACHE-4007"


class CacheCompressionError(DiskCacheError):
    """Raised when compression or decompression fails."""
    error_code = "CACHE-4008"


# ---- Part 6: Mesh Cache Exceptions -------------------------------------

class MeshCacheError(CacheError):
    """Base for mesh cache errors."""
    error_code = "CACHE-5001"


class MeshNotCachedError(MeshCacheError):
    """Raised when a mesh is not in the cache."""
    error_code = "CACHE-5002"


class MeshTopologyChangedError(MeshCacheError):
    """Raised when the mesh topology has changed since caching."""
    error_code = "CACHE-5003"


class MeshDeletedError(MeshCacheError):
    """Raised when the mesh has been deleted."""
    error_code = "CACHE-5004"


class MeshUUIDError(MeshCacheError):
    """Raised when a mesh UUID is invalid or not found."""
    error_code = "CACHE-5005"


class MeshValidationError(MeshCacheError):
    """Raised when mesh validation fails."""
    error_code = "CACHE-5006"


# ---- Part 7: Landmark Cache Exceptions --------------------------------

class LandmarkCacheError(CacheError):
    """Base for landmark cache errors."""
    error_code = "CACHE-6001"


class LandmarkNotFoundError(LandmarkCacheError):
    """Raised when a requested landmark is not found."""
    error_code = "CACHE-6002"


class InvalidLandmarkError(LandmarkCacheError):
    """Raised when landmark data is invalid."""
    error_code = "CACHE-6003"


class LandmarkTrackingLostError(LandmarkCacheError):
    """Raised when face tracking is lost."""
    error_code = "CACHE-6004"


class LandmarkMappingError(LandmarkCacheError):
    """Raised when mapping landmarks between different formats fails."""
    error_code = "CACHE-6005"


# ---- Part 8: Blendshape Cache Exceptions ------------------------------

class BlendshapeCacheError(CacheError):
    """Base for blendshape cache errors."""
    error_code = "CACHE-7001"


class BlendshapeMissingError(BlendshapeCacheError):
    """Raised when a blendshape target is missing."""
    error_code = "CACHE-7002"


class BlendshapeTargetError(BlendshapeCacheError):
    """Raised for target-related errors."""
    error_code = "CACHE-7003"


class BlendshapeWeightError(BlendshapeCacheError):
    """Raised for weight-related errors."""
    error_code = "CACHE-7004"


class BlendshapeDriverError(BlendshapeCacheError):
    """Raised for driver-related errors."""
    error_code = "CACHE-7005"


class BlendshapeTopologyError(BlendshapeCacheError):
    """Raised when blendshape topology is incompatible."""
    error_code = "CACHE-7006"


# ---- Part 9: Project Cache Exceptions ----------------------------------

class ProjectCacheError(CacheError):
    """Base for project cache errors."""
    error_code = "CACHE-8001"


class ProjectNotLoadedError(ProjectCacheError):
    """Raised when a project is not loaded."""
    error_code = "CACHE-8002"


class ProjectSaveError(ProjectCacheError):
    """Raised when saving a project cache fails."""
    error_code = "CACHE-8003"


class ProjectRestoreError(ProjectCacheError):
    """Raised when restoring a project cache fails."""
    error_code = "CACHE-8004"


class ProjectVersionError(ProjectCacheError):
    """Raised when the project cache version is incompatible."""
    error_code = "CACHE-8005"


class ProjectSnapshotError(ProjectCacheError):
    """Raised when creating or loading a project snapshot fails."""
    error_code = "CACHE-8006"


# ---- Part 10: Serialization Exceptions --------------------------------

class SerializationError(FaceitCacheError):
    """Raised when serialization fails."""
    error_code = "CACHE-9001"


class DeserializationError(FaceitCacheError):
    """Raised when deserialization fails."""
    error_code = "CACHE-9002"


class JsonSerializationError(SerializationError):
    """Raised when JSON serialization fails."""
    error_code = "CACHE-9003"


class BinarySerializationError(SerializationError):
    """Raised when binary serialization fails."""
    error_code = "CACHE-9004"


class CompressionError(FaceitCacheError):
    """Raised when compression fails."""
    error_code = "CACHE-9005"


class DecompressionError(FaceitCacheError):
    """Raised when decompression fails."""
    error_code = "CACHE-9006"


# ---- Part 11: Validation Exceptions ------------------------------------

class ValidationError(FaceitCacheError):
    """Base for validation errors."""
    error_code = "CACHE-10001"


class InvalidCacheEntryError(ValidationError):
    """Raised when a cache entry is invalid."""
    error_code = "CACHE-10002"


class InvalidCacheKeyError(ValidationError):
    """Raised when a cache key is invalid."""
    error_code = "CACHE-10003"


class InvalidCachePathError(ValidationError):
    """Raised when a cache path is invalid."""
    error_code = "CACHE-10004"


class InvalidChecksumError(ValidationError):
    """Raised when a checksum mismatch occurs."""
    error_code = "CACHE-10005"


class InvalidUUIDError(ValidationError):
    """Raised when a UUID is invalid."""
    error_code = "CACHE-10006"


# ---- Part 12: Version Exceptions ---------------------------------------

class CacheVersionError(FaceitCacheError):
    """Raised when versioning errors occur."""
    error_code = "CACHE-11001"


class SchemaMismatchError(CacheVersionError):
    """Raised when the cache schema version does not match."""
    error_code = "CACHE-11002"


class PluginVersionMismatchError(CacheVersionError):
    """Raised when the plugin version is incompatible."""
    error_code = "CACHE-11003"


class MigrationRequiredError(CacheVersionError):
    """Raised when a cache migration is required."""
    error_code = "CACHE-11004"


# ---- Part 13: File Exceptions -----------------------------------------

class CacheDirectoryError(FaceitCacheError):
    """Raised when directory operations fail."""
    error_code = "CACHE-12001"


class CacheManifestError(FaceitCacheError):
    """Raised when the cache manifest is corrupt or missing."""
    error_code = "CACHE-12002"


class BackupError(FaceitCacheError):
    """Raised when backup operations fail."""
    error_code = "CACHE-12003"


class RestoreError(FaceitCacheError):
    """Raised when restore operations fail."""
    error_code = "CACHE-12004"


class AtomicWriteError(FaceitCacheError):
    """Raised when atomic file write fails."""
    error_code = "CACHE-12005"


# ---- Part 14: Runtime Exceptions ---------------------------------------

class CacheRuntimeError(FaceitCacheError):
    """Base for runtime errors during cache operations."""
    error_code = "CACHE-13001"


class CacheLockError(CacheRuntimeError):
    """Raised when a lock cannot be acquired."""
    error_code = "CACHE-13002"


class CacheDeadlockError(CacheRuntimeError):
    """Raised when a deadlock is detected."""
    error_code = "CACHE-13003"


class CacheThreadError(CacheRuntimeError):
    """Raised when thread-related errors occur."""
    error_code = "CACHE-13004"


class CacheInterruptedError(CacheRuntimeError):
    """Raised when a cache operation is interrupted."""
    error_code = "CACHE-13005"


# ---- Part 15: Utility Functions ---------------------------------------

def format_exception(exc: Exception, include_traceback: bool = False) -> str:
    """
    Format an exception into a human-readable string.

    Args:
        exc: The exception to format.
        include_traceback: Whether to include the full traceback.

    Returns:
        Formatted exception string.
    """
    if include_traceback:
        return ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    else:
        msg = str(exc)
        if hasattr(exc, 'error_code') and exc.error_code:
            msg = f"[{exc.error_code}] {msg}"
        return msg


def exception_to_dict(exc: Exception) -> Dict[str, Any]:
    """
    Convert an exception to a dictionary for logging or JSON serialization.

    Returns:
        Dict with keys: 'type', 'message', 'error_code', 'context', 'traceback'.
    """
    return {
        'type': exc.__class__.__name__,
        'message': str(exc),
        'error_code': getattr(exc, 'error_code', None),
        'context': getattr(exc, 'context', {}),
        'traceback': traceback.format_exc(),
    }


def exception_from_dict(data: Dict[str, Any]) -> Optional[Exception]:
    """
    Reconstruct an exception from a dictionary (inverse of exception_to_dict).
    This is useful for serializing exceptions across processes.

    Returns:
        The reconstructed exception, or None if the type cannot be resolved.
    """
    try:
        exc_type = data.get('type')
        message = data.get('message', '')
        context = data.get('context', {})
        if exc_type in globals():
            cls = globals()[exc_type]
            if issubclass(cls, Exception):
                # Attempt to instantiate with context as kwargs
                return cls(message, context=context)
    except:
        pass
    return None


def error_summary(exc: Exception) -> str:
    """
    Return a short summary of the exception (type + message + code).
    """
    code = f"[{exc.error_code}]" if hasattr(exc, 'error_code') and exc.error_code else ""
    return f"{code} {exc.__class__.__name__}: {str(exc)}"


# ---- Part 16: Public API -----------------------------------------------

__all__ = [
    # Base
    "FaceitCacheError",

    # Configuration
    "CacheConfigurationError",
    "CacheInitializationError",
    "CacheSettingsError",
    "CacheRegistrationError",

    # General
    "CacheError",
    "CacheNotFoundError",
    "CacheExistsError",
    "CacheKeyError",
    "CacheLookupError",
    "CacheStateError",
    "CacheBusyError",
    "CacheTimeoutError",
    "CacheInvalidatedError",

    # Memory
    "MemoryCacheError",
    "MemoryLimitExceededError",
    "MemoryAllocationError",
    "MemoryEvictionError",
    "MemoryExpiredError",
    "WeakReferenceError",

    # Disk
    "DiskCacheError",
    "CacheFileError",
    "CacheFileMissingError",
    "CacheWriteError",
    "CacheReadError",
    "CachePermissionError",
    "CacheCorruptedError",
    "CacheCompressionError",

    # Mesh
    "MeshCacheError",
    "MeshNotCachedError",
    "MeshTopologyChangedError",
    "MeshDeletedError",
    "MeshUUIDError",
    "MeshValidationError",

    # Landmark
    "LandmarkCacheError",
    "LandmarkNotFoundError",
    "InvalidLandmarkError",
    "LandmarkTrackingLostError",
    "LandmarkMappingError",

    # Blendshape
    "BlendshapeCacheError",
    "BlendshapeMissingError",
    "BlendshapeTargetError",
    "BlendshapeWeightError",
    "BlendshapeDriverError",
    "BlendshapeTopologyError",

    # Project
    "ProjectCacheError",
    "ProjectNotLoadedError",
    "ProjectSaveError",
    "ProjectRestoreError",
    "ProjectVersionError",
    "ProjectSnapshotError",

    # Serialization
    "SerializationError",
    "DeserializationError",
    "JsonSerializationError",
    "BinarySerializationError",
    "CompressionError",
    "DecompressionError",

    # Validation
    "ValidationError",
    "InvalidCacheEntryError",
    "InvalidCacheKeyError",
    "InvalidCachePathError",
    "InvalidChecksumError",
    "InvalidUUIDError",

    # Version
    "CacheVersionError",
    "SchemaMismatchError",
    "PluginVersionMismatchError",
    "MigrationRequiredError",

    # File
    "CacheDirectoryError",
    "CacheManifestError",
    "BackupError",
    "RestoreError",
    "AtomicWriteError",

    # Runtime
    "CacheRuntimeError",
    "CacheLockError",
    "CacheDeadlockError",
    "CacheThreadError",
    "CacheInterruptedError",

    # Utilities
    "format_exception",
    "exception_to_dict",
    "exception_from_dict",
    "error_summary",
]