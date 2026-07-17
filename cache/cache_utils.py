"""
cache/cache_utils.py

Shared Utility Library for the Caching Framework.

This module provides reusable helper functions that every cache module
(MemoryCache, DiskCache, MeshCache, BlendshapeCache, etc.) depends on.
It is stateless, generic, and dependency-light, containing only pure
utility functions and helpers.

Responsibilities:
- Key generation, normalization, sanitization.
- UUID generation and validation.
- Hashing (SHA256, MD5, CRC32, file hashing, object hashing).
- Serialization helpers (JSON, pickle, binary, deep copy).
- Compression helpers (gzip, zip, lzma, zstd).
- Time and date utilities (timestamps, expiration, duration formatting).
- Path utilities (normalization, safe file operations, temporary files).
- Memory estimation (object size, recursive size).
- Validation helpers (key validation, UUID validation, serializability).
- Retry and lock helpers (retry decorator, atomic write, safe file ops).
- Formatting helpers (bytes, time, percentage, rate).
- Diagnostics helpers (system info, Python version, Maya version).

Dependencies:
- hashlib, uuid, pathlib, tempfile, shutil, json, pickle, gzip, zipfile, lzma, zlib.
- threading, functools, os, sys, time, datetime, typing, dataclasses.
- May optionally use zstandard if available.
- No Maya-specific dependencies (except for maya_version helper).

The module does not import any cache modules to avoid circular dependencies.
"""

from __future__ import annotations

import base64
import contextlib
import csv
import datetime
import functools
import gc
import hashlib
import io
import json
import logging
import os
import pickle
import re
import shutil
import sys
import tempfile
import threading
import time
import uuid
import zlib
import zipfile
from dataclasses import dataclass, field, is_dataclass, asdict
from pathlib import Path
from typing import (
    Any, Dict, List, Optional, Set, Tuple, Union, Callable, Iterator,
    TypeVar, Generic, cast, overload, Iterable, BinaryIO, TextIO
)

# Optional dependencies
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

# ---- Part 2: Constants ------------------------------------------------

DEFAULT_HASH = "sha256"
DEFAULT_ENCODING = "utf-8"
DEFAULT_CACHE_EXTENSION = ".cache"
DEFAULT_TIMEOUT = 30
DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_DELAY = 0.1
MAX_FILENAME_LENGTH = 255

# ---- Part 3: Key Utilities --------------------------------------------

def generate_key(*args: Any, separator: str = "_") -> str:
    """
    Generate a cache key from multiple arguments.

    Args:
        *args: Values to include in the key.
        separator: Separator between parts.

    Returns:
        A normalized cache key string.
    """
    parts = []
    for arg in args:
        if arg is None:
            parts.append("none")
        elif isinstance(arg, (int, float, bool, str)):
            parts.append(str(arg))
        elif isinstance(arg, (list, tuple)):
            parts.append("_".join(str(a) for a in arg))
        elif isinstance(arg, dict):
            # Sort for deterministic order
            items = sorted(arg.items())
            parts.append("_".join(f"{k}:{v}" for k, v in items if v is not None))
        elif hasattr(arg, '__dict__'):
            # Try to use object's string representation
            parts.append(str(arg))
        else:
            parts.append(str(arg))
    return sanitize_key(separator.join(parts))


def normalize_key(key: str) -> str:
    """
    Normalize a cache key to a consistent format.

    - Converts to lowercase.
    - Replaces spaces and special characters with underscores.
    - Collapses multiple underscores.
    """
    if not isinstance(key, str):
        key = str(key)
    # Convert to lowercase
    key = key.lower()
    # Replace non-alphanumeric with underscores (allow underscores and hyphens)
    key = re.sub(r'[^a-z0-9_\-]', '_', key)
    # Collapse multiple underscores
    key = re.sub(r'_+', '_', key)
    # Remove leading/trailing underscores
    key = key.strip('_')
    return key


def sanitize_key(key: str) -> str:
    """
    Sanitize a key for safe use in filenames and cache lookups.

    - Ensures key is a string.
    - Normalizes and removes unsafe characters.
    - Limits length to a reasonable maximum.
    """
    if not isinstance(key, str):
        key = str(key)
    # Normalize first
    key = normalize_key(key)
    # Limit length (cryptographic keys may be long)
    if len(key) > 256:
        key = key[:256]
    return key


def join_key(*parts: Any, separator: str = "_") -> str:
    """Join multiple key parts with a separator."""
    return sanitize_key(separator.join(str(p) for p in parts if p is not None))


def split_key(key: str, separator: str = "_") -> List[str]:
    """Split a key into parts."""
    return [p for p in key.split(separator) if p]


def random_key(length: int = 16) -> str:
    """Generate a random cache key."""
    return base64.urlsafe_b64encode(os.urandom(length)).decode('utf-8').rstrip('=')


# ---- Part 4: UUID Utilities -------------------------------------------

def new_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


def validate_uuid(uuid_str: str) -> bool:
    """Validate a UUID string."""
    try:
        uuid.UUID(uuid_str)
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def short_uuid() -> str:
    """Generate a short UUID (first 8 characters)."""
    return new_uuid().split('-')[0]


def uuid_to_string(uuid_obj: uuid.UUID) -> str:
    """Convert a UUID object to a string."""
    return str(uuid_obj)


def string_to_uuid(uuid_str: str) -> Optional[uuid.UUID]:
    """Convert a string to a UUID object."""
    try:
        return uuid.UUID(uuid_str)
    except (ValueError, AttributeError, TypeError):
        return None


# ---- Part 5: Hash Utilities -------------------------------------------

def sha256(data: Union[bytes, str]) -> str:
    """Compute SHA256 hash of data."""
    if isinstance(data, str):
        data = data.encode(DEFAULT_ENCODING)
    return hashlib.sha256(data).hexdigest()


def sha1(data: Union[bytes, str]) -> str:
    """Compute SHA1 hash of data."""
    if isinstance(data, str):
        data = data.encode(DEFAULT_ENCODING)
    return hashlib.sha1(data).hexdigest()


def md5(data: Union[bytes, str]) -> str:
    """Compute MD5 hash of data."""
    if isinstance(data, str):
        data = data.encode(DEFAULT_ENCODING)
    return hashlib.md5(data).hexdigest()


def crc32(data: Union[bytes, str]) -> int:
    """Compute CRC32 checksum of data."""
    if isinstance(data, str):
        data = data.encode(DEFAULT_ENCODING)
    return zlib.crc32(data) & 0xFFFFFFFF


def hash_file(filepath: Union[str, Path], algorithm: str = "sha256") -> str:
    """
    Compute the hash of a file's contents.

    Args:
        filepath: Path to the file.
        algorithm: Hash algorithm ('sha256', 'sha1', 'md5').

    Returns:
        Hex digest of the file hash.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    hash_func = getattr(hashlib, algorithm, None)
    if hash_func is None:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")

    hasher = hash_func()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def hash_object(obj: Any, algorithm: str = "sha256") -> str:
    """
    Compute a deterministic hash of any Python object.

    Args:
        obj: The object to hash.
        algorithm: Hash algorithm.

    Returns:
        Hex digest of the object hash.
    """
    # Serialize to JSON with sorted keys for determinism
    if is_dataclass(obj):
        obj = asdict(obj)
    # Handle common types
    if isinstance(obj, dict):
        obj = {str(k): v for k, v in obj.items()}
        # Sort keys for determinism
        obj = dict(sorted(obj.items()))
    elif isinstance(obj, (list, tuple)):
        obj = [hash_object(item) for item in obj]
    elif isinstance(obj, set):
        obj = sorted([hash_object(item) for item in obj])
    # Convert to JSON
    json_str = json.dumps(obj, default=str, sort_keys=True)
    return sha256(json_str)


def hash_string(value: str, algorithm: str = "sha256") -> str:
    """Compute hash of a string."""
    hash_func = getattr(hashlib, algorithm, None)
    if hash_func is None:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")
    return hash_func(value.encode(DEFAULT_ENCODING)).hexdigest()


def hash_bytes(data: bytes, algorithm: str = "sha256") -> str:
    """Compute hash of bytes."""
    hash_func = getattr(hashlib, algorithm, None)
    if hash_func is None:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")
    return hash_func(data).hexdigest()


# ---- Part 6: Serialization Helpers ------------------------------------

def serialize_json(data: Any, indent: Optional[int] = None) -> str:
    """Serialize data to JSON string."""
    return json.dumps(data, default=str, indent=indent, sort_keys=True)


def deserialize_json(json_str: str) -> Any:
    """Deserialize JSON string to Python object."""
    return json.loads(json_str)


def serialize_pickle(data: Any, protocol: int = pickle.HIGHEST_PROTOCOL) -> bytes:
    """Serialize data using pickle."""
    return pickle.dumps(data, protocol=protocol)


def deserialize_pickle(data: bytes) -> Any:
    """Deserialize pickle data."""
    return pickle.loads(data)


def serialize_binary(data: Any) -> bytes:
    """Serialize data to binary using pickle (fallback)."""
    return serialize_pickle(data)


def deserialize_binary(data: bytes) -> Any:
    """Deserialize binary data using pickle (fallback)."""
    return deserialize_pickle(data)


def deep_copy(obj: Any) -> Any:
    """Create a deep copy of an object."""
    # Try pickle-based copy first (fast for many objects)
    try:
        return pickle.loads(pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL))
    except (pickle.PickleError, TypeError, AttributeError):
        # Fallback to Python's deepcopy
        import copy
        return copy.deepcopy(obj)


def clone(obj: Any) -> Any:
    """Alias for deep_copy."""
    return deep_copy(obj)


def is_serializable(obj: Any) -> bool:
    """Check if an object is JSON-serializable."""
    try:
        json.dumps(obj, default=str)
        return True
    except (TypeError, ValueError):
        return False


# ---- Part 7: Compression Helpers -------------------------------------

def compress_gzip(data: bytes, level: int = 6) -> bytes:
    """Compress data using gzip."""
    import gzip
    return gzip.compress(data, compresslevel=level)


def decompress_gzip(data: bytes) -> bytes:
    """Decompress gzip data."""
    import gzip
    return gzip.decompress(data)


def compress_zlib(data: bytes, level: int = 6) -> bytes:
    """Compress data using zlib."""
    return zlib.compress(data, level)


def decompress_zlib(data: bytes) -> bytes:
    """Decompress zlib data."""
    return zlib.decompress(data)


def compress_lzma(data: bytes) -> bytes:
    """Compress data using LZMA (if available)."""
    if HAS_LZMA:
        return lzma.compress(data)
    raise RuntimeError("LZMA not available")


def decompress_lzma(data: bytes) -> bytes:
    """Decompress LZMA data (if available)."""
    if HAS_LZMA:
        return lzma.decompress(data)
    raise RuntimeError("LZMA not available")


def compress_zstd(data: bytes, level: int = 3) -> bytes:
    """Compress data using Zstandard (if available)."""
    if HAS_ZSTD:
        cctx = zstandard.ZstdCompressor(level=level)
        return cctx.compress(data)
    raise RuntimeError("Zstandard not available")


def decompress_zstd(data: bytes) -> bytes:
    """Decompress Zstandard data (if available)."""
    if HAS_ZSTD:
        dctx = zstandard.ZstdDecompressor()
        return dctx.decompress(data)
    raise RuntimeError("Zstandard not available")


def compress(
    data: bytes,
    method: str = "gzip",
    level: int = 6
) -> bytes:
    """
    Compress data using the specified method.

    Args:
        data: Bytes to compress.
        method: 'gzip', 'zlib', 'lzma', 'zstd'.
        level: Compression level (method-dependent).

    Returns:
        Compressed bytes.
    """
    if method == "gzip":
        return compress_gzip(data, level)
    elif method == "zlib":
        return compress_zlib(data, level)
    elif method == "lzma":
        return compress_lzma(data)
    elif method == "zstd":
        return compress_zstd(data, level)
    else:
        raise ValueError(f"Unsupported compression method: {method}")


def decompress(data: bytes, method: str = "gzip") -> bytes:
    """
    Decompress data using the specified method.

    Args:
        data: Compressed bytes.
        method: 'gzip', 'zlib', 'lzma', 'zstd'.

    Returns:
        Decompressed bytes.
    """
    if method == "gzip":
        return decompress_gzip(data)
    elif method == "zlib":
        return decompress_zlib(data)
    elif method == "lzma":
        return decompress_lzma(data)
    elif method == "zstd":
        return decompress_zstd(data)
    else:
        raise ValueError(f"Unsupported compression method: {method}")


def compression_ratio(original: bytes, compressed: bytes) -> float:
    """Calculate the compression ratio (compressed / original)."""
    if not original:
        return 1.0
    return len(compressed) / len(original)


def zip_folder(
    folder_path: Union[str, Path],
    output_path: Union[str, Path],
    compression: int = zipfile.ZIP_DEFLATED
) -> int:
    """
    Zip a folder and return the number of files archived.

    Args:
        folder_path: Source folder.
        output_path: Output zip file path.
        compression: Compression method.

    Returns:
        Number of files archived.
    """
    import zipfile
    folder = Path(folder_path)
    output = Path(output_path)
    count = 0
    with zipfile.ZipFile(output, 'w', compression=compression) as zf:
        for file_path in folder.rglob('*'):
            if file_path.is_file():
                zf.write(file_path, file_path.relative_to(folder))
                count += 1
    return count


def unzip_folder(
    zip_path: Union[str, Path],
    output_dir: Union[str, Path],
    overwrite: bool = True
) -> int:
    """
    Unzip a zip file to a folder.

    Args:
        zip_path: Path to zip file.
        output_dir: Output directory.
        overwrite: Whether to overwrite existing files.

    Returns:
        Number of files extracted.
    """
    import zipfile
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    count = 0
    with zipfile.ZipFile(zip_path, 'r') as zf:
        for member in zf.namelist():
            target = output / member
            if overwrite or not target.exists():
                zf.extract(member, output)
                count += 1
    return count


# ---- Part 8: Time & Date Helpers --------------------------------------

def now() -> float:
    """Return the current timestamp in seconds."""
    return time.time()


def utc_now() -> float:
    """Return the current UTC timestamp."""
    return time.time()


def timestamp() -> str:
    """Return a formatted timestamp string."""
    return datetime.datetime.now().isoformat()


def utc_timestamp() -> str:
    """Return a formatted UTC timestamp string."""
    return datetime.datetime.utcnow().isoformat()


def elapsed(start_time: float) -> float:
    """Calculate elapsed time since start_time."""
    return time.time() - start_time


def format_duration(seconds: float) -> str:
    """Format a duration in seconds to a human-readable string."""
    if seconds < 60:
        return f"{seconds:.2f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.2f}m"
    elif seconds < 86400:
        hours = seconds / 3600
        return f"{hours:.2f}h"
    else:
        days = seconds / 86400
        return f"{days:.2f}d"


def is_expired(timestamp: float, ttl: Optional[float]) -> bool:
    """
    Check if a timestamp has expired relative to TTL.

    Args:
        timestamp: Creation timestamp.
        ttl: Time-to-live in seconds (None means never expires).

    Returns:
        True if expired, False otherwise.
    """
    if ttl is None:
        return False
    if ttl <= 0:
        return True
    return time.time() - timestamp > ttl


def iso_to_timestamp(iso_str: str) -> float:
    """Convert ISO timestamp string to Unix timestamp."""
    dt = datetime.datetime.fromisoformat(iso_str)
    return dt.timestamp()


def timestamp_to_iso(timestamp: float) -> str:
    """Convert Unix timestamp to ISO string."""
    dt = datetime.datetime.fromtimestamp(timestamp)
    return dt.isoformat()


# ---- Part 9: Path Utilities -------------------------------------------

def ensure_directory(path: Union[str, Path]) -> Path:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        path: Directory path.

    Returns:
        The resolved Path object.
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_filename(name: str, max_length: int = MAX_FILENAME_LENGTH) -> str:
    """
    Convert a string to a safe filename.

    - Removes or replaces unsafe characters.
    - Truncates to max_length.
    """
    # Remove unsafe characters
    safe = re.sub(r'[<>:"/\\|?*]', '_', name)
    # Remove leading/trailing spaces and dots
    safe = safe.strip(' .')
    # Collapse multiple underscores
    safe = re.sub(r'_+', '_', safe)
    # Truncate
    if len(safe) > max_length:
        safe = safe[:max_length]
    return safe


def normalize_path(path: Union[str, Path]) -> Path:
    """Normalize a path (resolve, expand user, make absolute)."""
    return Path(path).expanduser().resolve()


def relative_path(path: Union[str, Path], base: Union[str, Path]) -> Path:
    """Get the relative path from base to path."""
    p = Path(path).resolve()
    b = Path(base).resolve()
    try:
        return p.relative_to(b)
    except ValueError:
        return p


def absolute_path(path: Union[str, Path]) -> Path:
    """Get the absolute path."""
    return Path(path).resolve()


def temporary_file(suffix: str = "", prefix: str = "tmp_") -> Path:
    """
    Create a temporary file and return its path.

    Args:
        suffix: File suffix (e.g., '.tmp').
        prefix: File prefix.

    Returns:
        Path to the temporary file.
    """
    fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix)
    os.close(fd)
    return Path(path)


def temporary_directory() -> Path:
    """Create a temporary directory and return its path."""
    return Path(tempfile.mkdtemp())


def cache_directory(name: str, root: Optional[Union[str, Path]] = None) -> Path:
    """
    Get a cache directory for a specific cache.

    Args:
        name: Cache name.
        root: Root cache directory (optional).

    Returns:
        Path to the cache directory.
    """
    if root is None:
        # Use default cache location
        if os.name == 'nt':
            base = Path(os.environ.get('APPDATA', os.path.expanduser('~')))
        else:
            base = Path(os.path.expanduser('~/.cache'))
        root = base / 'maya_faceit'
    root = Path(root)
    return root / name


# ---- Part 10: Memory Utilities ----------------------------------------

def object_size(obj: Any) -> int:
    """
    Estimate the memory size of a Python object.

    Args:
        obj: The object to measure.

    Returns:
        Size in bytes.
    """
    try:
        return sys.getsizeof(obj)
    except (TypeError, AttributeError):
        return 0


def recursive_size(obj: Any) -> int:
    """
    Calculate the recursive memory size of an object.

    This traverses containers (lists, dicts, sets, tuples) to estimate total
    memory usage, including contained objects.
    """
    seen = set()

    def _size(o: Any) -> int:
        if id(o) in seen:
            return 0
        seen.add(id(o))
        total = object_size(o)
        if isinstance(o, dict):
            for k, v in o.items():
                total += _size(k) + _size(v)
        elif isinstance(o, (list, tuple, set, frozenset)):
            for item in o:
                total += _size(item)
        elif isinstance(o, (str, bytes, bytearray)):
            # Already counted by sys.getsizeof
            pass
        elif hasattr(o, '__dict__'):
            total += _size(o.__dict__)
        return total

    return _size(obj)


def estimate_cache_size(cache_data: Dict[str, Any]) -> int:
    """Estimate the total memory size of a cache dictionary."""
    return recursive_size(cache_data)


def memory_usage() -> float:
    """
    Return the current memory usage of the process in MB.

    Returns:
        Memory usage in megabytes.
    """
    import psutil
    try:
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / (1024 * 1024)
    except (ImportError, AttributeError, psutil.NoSuchProcess):
        # Fallback: use resource module if available
        try:
            import resource
            return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
        except (ImportError, AttributeError):
            return 0.0


# ---- Part 11: Validation Helpers -------------------------------------

def is_valid_key(key: Any) -> bool:
    """Check if a key is valid for cache use."""
    if key is None:
        return False
    if not isinstance(key, str):
        try:
            key = str(key)
        except:
            return False
    return len(key) > 0


def is_valid_path(path: Any) -> bool:
    """Check if a path is valid."""
    try:
        Path(path)
        return True
    except (TypeError, ValueError):
        return False


def is_valid_uuid(uuid_str: Any) -> bool:
    """Check if a string is a valid UUID."""
    return validate_uuid(uuid_str) if isinstance(uuid_str, str) else False


def is_serializable(obj: Any) -> bool:
    """Check if an object is JSON-serializable."""
    try:
        json.dumps(obj, default=str)
        return True
    except (TypeError, ValueError):
        return False


def is_compressed(data: bytes) -> bool:
    """
    Check if data appears to be compressed (by checking magic bytes).

    Detects gzip, zlib, lzma, and zstd.
    """
    if not isinstance(data, bytes) or len(data) < 4:
        return False
    # gzip: 1F 8B
    if data[:2] == b'\x1f\x8b':
        return True
    # zlib: 78 01, 78 9C, 78 DA
    if data[:2] == b'\x78\x01' or data[:2] == b'\x78\x9c' or data[:2] == b'\x78\xda':
        return True
    # lzma: FD 37 7A 58 5A 00
    if len(data) >= 6 and data[:6] == b'\xfd\x37\x7a\x58\x5a\x00':
        return True
    # zstd: 28 B5 2F FD
    if len(data) >= 4 and data[:4] == b'\x28\xb5\x2f\xfd':
        return True
    return False


def is_json(data: Union[bytes, str]) -> bool:
    """Check if data is valid JSON."""
    if isinstance(data, bytes):
        try:
            data = data.decode(DEFAULT_ENCODING)
        except UnicodeDecodeError:
            return False
    if not isinstance(data, str):
        return False
    try:
        json.loads(data)
        return True
    except json.JSONDecodeError:
        return False


# ---- Part 12: Retry & Lock Helpers ------------------------------------

def retry(
    max_attempts: int = DEFAULT_RETRY_COUNT,
    delay: float = DEFAULT_RETRY_DELAY,
    exceptions: Tuple[type, ...] = (Exception,)
) -> Callable:
    """
    Decorator to retry a function on failure.

    Args:
        max_attempts: Maximum number of attempts.
        delay: Delay between attempts in seconds.
        exceptions: Tuple of exception types to retry on.

    Returns:
        Decorated function.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        time.sleep(delay * (2 ** attempt))  # Exponential backoff
            raise last_exception
        return wrapper
    return decorator


@contextlib.contextmanager
def with_lock(lock: threading.Lock) -> Iterator[None]:
    """
    Context manager for acquiring and releasing a lock.

    Args:
        lock: A threading.Lock or threading.RLock.

    Yields:
        None (lock is acquired).
    """
    acquired = lock.acquire()
    try:
        yield
    finally:
        if acquired:
            lock.release()


def atomic_write(
    filepath: Union[str, Path],
    data: Union[bytes, str],
    mode: str = 'wb',
    encoding: Optional[str] = None,
    overwrite: bool = True
) -> None:
    """
    Write data to a file atomically using a temporary file.

    Args:
        filepath: Target file path.
        data: Data to write.
        mode: File mode ('wb' or 'w').
        encoding: Encoding for text mode.
        overwrite: Whether to overwrite existing file.
    """
    path = Path(filepath)
    if not overwrite and path.exists():
        return

    # Ensure directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write to temporary file
    temp_path = path.with_suffix(path.suffix + '.tmp')
    try:
        if 'b' in mode:
            if isinstance(data, str):
                data = data.encode(encoding or DEFAULT_ENCODING)
            with open(temp_path, mode) as f:
                f.write(data)
        else:
            if isinstance(data, bytes):
                data = data.decode(encoding or DEFAULT_ENCODING)
            with open(temp_path, mode, encoding=encoding or DEFAULT_ENCODING) as f:
                f.write(data)
        # Atomically rename
        temp_path.rename(path)
    except Exception:
        # Clean up temporary file on failure
        if temp_path.exists():
            temp_path.unlink()
        raise


def safe_remove(path: Union[str, Path]) -> bool:
    """
    Safely remove a file or directory.

    Args:
        path: Path to remove.

    Returns:
        True if removed, False if not found.
    """
    p = Path(path)
    if not p.exists():
        return False
    try:
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()
        return True
    except (OSError, PermissionError):
        return False


def safe_move(src: Union[str, Path], dst: Union[str, Path]) -> bool:
    """
    Safely move a file or directory.

    Args:
        src: Source path.
        dst: Destination path.

    Returns:
        True if moved, False if failed.
    """
    try:
        shutil.move(str(src), str(dst))
        return True
    except (OSError, shutil.Error):
        return False


@contextlib.contextmanager
def safe_open(
    filepath: Union[str, Path],
    mode: str = 'r',
    encoding: Optional[str] = None
) -> Iterator[Any]:
    """
    Context manager for safely opening a file with error handling.

    Args:
        filepath: Path to file.
        mode: File open mode.
        encoding: Text encoding.

    Yields:
        File object.
    """
    path = Path(filepath)
    try:
        if 'b' in mode:
            with open(path, mode) as f:
                yield f
        else:
            with open(path, mode, encoding=encoding or DEFAULT_ENCODING) as f:
                yield f
    except (OSError, IOError) as e:
        raise IOError(f"Failed to open {path}: {e}")


# ---- Part 13: Formatting Helpers -------------------------------------

def format_bytes(size: int, decimals: int = 2) -> str:
    """
    Format a size in bytes to a human-readable string.

    Args:
        size: Size in bytes.
        decimals: Number of decimal places.

    Returns:
        Formatted string (e.g., "1.5 MB").
    """
    if size < 0:
        return "0 B"
    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    index = 0
    while size >= 1024 and index < len(units) - 1:
        size /= 1024.0
        index += 1
    return f"{size:.{decimals}f} {units[index]}"


def format_time(seconds: float, decimals: int = 3) -> str:
    """
    Format a time in seconds to a human-readable string.

    Args:
        seconds: Time in seconds.
        decimals: Number of decimal places.

    Returns:
        Formatted string with appropriate units.
    """
    if seconds < 0:
        return "0s"
    if seconds < 1e-6:
        return f"{seconds * 1e9:.{decimals}f} ns"
    elif seconds < 1e-3:
        return f"{seconds * 1e6:.{decimals}f} µs"
    elif seconds < 1:
        return f"{seconds * 1000:.{decimals}f} ms"
    elif seconds < 60:
        return f"{seconds:.{decimals}f} s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.{decimals}f} m"
    else:
        hours = seconds / 3600
        return f"{hours:.{decimals}f} h"


def format_percentage(value: float, decimals: int = 2) -> str:
    """Format a value as a percentage."""
    return f"{value * 100:.{decimals}f}%"


def format_rate(rate: float, decimals: int = 2) -> str:
    """Format a rate (items per second)."""
    return f"{rate:.{decimals}f} ops/s"


def format_number(value: float, decimals: int = 2) -> str:
    """Format a number with thousands separators."""
    return f"{value:,.{decimals}f}"


def truncate_string(value: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate a string to max_length."""
    if len(value) <= max_length:
        return value
    return value[:max_length - len(suffix)] + suffix


# ---- Part 14: Diagnostics Helpers ------------------------------------

def system_info() -> Dict[str, Any]:
    """Get system information."""
    info = {
        "os": os.name,
        "platform": sys.platform,
        "python_version": sys.version,
        "python_executable": sys.executable,
        "cpu_count": os.cpu_count(),
        "pid": os.getpid(),
    }
    try:
        import psutil
        info["memory_total_mb"] = psutil.virtual_memory().total / (1024 * 1024)
        info["memory_available_mb"] = psutil.virtual_memory().available / (1024 * 1024)
    except (ImportError, AttributeError):
        pass
    return info


def python_version() -> str:
    """Return the Python version string."""
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def maya_version() -> str:
    """Return the Maya version if available."""
    try:
        import maya.cmds as cmds
        return cmds.about(version=True)
    except (ImportError, AttributeError):
        return "Maya not available"


def cache_environment() -> Dict[str, Any]:
    """Get the cache environment information."""
    env = {
        "python_version": python_version(),
        "maya_version": maya_version(),
        "system_info": system_info(),
        "has_lzma": HAS_LZMA,
        "has_zstd": HAS_ZSTD,
        "cache_version": "1.0.0",
    }
    return env


def plugin_version() -> str:
    """Return the plugin version (from package metadata)."""
    try:
        from maya_faceit import __version__
        return __version__
    except (ImportError, AttributeError):
        return "1.0.0"


# ---- Part 15: Public API -----------------------------------------------

__all__ = [
    # Constants
    "DEFAULT_HASH",
    "DEFAULT_ENCODING",
    "DEFAULT_CACHE_EXTENSION",
    "DEFAULT_TIMEOUT",
    "DEFAULT_RETRY_COUNT",
    "DEFAULT_RETRY_DELAY",
    "MAX_FILENAME_LENGTH",

    # Key Utilities
    "generate_key",
    "normalize_key",
    "sanitize_key",
    "join_key",
    "split_key",
    "random_key",

    # UUID Utilities
    "new_uuid",
    "validate_uuid",
    "short_uuid",
    "uuid_to_string",
    "string_to_uuid",

    # Hash Utilities
    "sha256",
    "sha1",
    "md5",
    "crc32",
    "hash_file",
    "hash_object",
    "hash_string",
    "hash_bytes",

    # Serialization Helpers
    "serialize_json",
    "deserialize_json",
    "serialize_pickle",
    "deserialize_pickle",
    "serialize_binary",
    "deserialize_binary",
    "deep_copy",
    "clone",
    "is_serializable",

    # Compression Helpers
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

    # Time & Date Helpers
    "now",
    "utc_now",
    "timestamp",
    "utc_timestamp",
    "elapsed",
    "format_duration",
    "is_expired",
    "iso_to_timestamp",
    "timestamp_to_iso",

    # Path Utilities
    "ensure_directory",
    "safe_filename",
    "normalize_path",
    "relative_path",
    "absolute_path",
    "temporary_file",
    "temporary_directory",
    "cache_directory",

    # Memory Utilities
    "object_size",
    "recursive_size",
    "estimate_cache_size",
    "memory_usage",

    # Validation Helpers
    "is_valid_key",
    "is_valid_path",
    "is_valid_uuid",
    "is_serializable",
    "is_compressed",
    "is_json",

    # Retry & Lock Helpers
    "retry",
    "with_lock",
    "atomic_write",
    "safe_remove",
    "safe_move",
    "safe_open",

    # Formatting Helpers
    "format_bytes",
    "format_time",
    "format_percentage",
    "format_rate",
    "format_number",
    "truncate_string",

    # Diagnostics Helpers
    "system_info",
    "python_version",
    "maya_version",
    "cache_environment",
    "plugin_version",
]