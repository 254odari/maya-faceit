"""
io.py

Centralized Input / Output subsystem for the ARKit Mapper.

This module is responsible for all persistence operations,
including loading and saving mappings, presets, runtime
snapshots, statistics, projects, backups, and configuration
files.

Supported formats:

    • JSON
    • YAML
    • CSV
    • Binary (pickle)
    • Compressed archives

All file operations should pass through IOManager to ensure
validation, atomic writes, version compatibility, and error
handling.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import os
import pickle
import shutil
import tempfile
import threading
import time
import zipfile

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    BinaryIO,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
)

try:
    import yaml
except ImportError:
    yaml = None

from .exceptions import (
    ARKitMapperError,
    FileFormatError,
    FileIOError,
    SerializationError,
)

# ============================================================
# Module Constants
# ============================================================

IO_VERSION = "1.0.0"

DEFAULT_ENCODING = "utf-8"

DEFAULT_INDENT = 4

DEFAULT_BACKUP_SUFFIX = ".bak"

DEFAULT_PROJECT_EXTENSION = ".arkit"

DEFAULT_MAPPING_EXTENSION = ".mapping"

DEFAULT_PRESET_EXTENSION = ".preset"

DEFAULT_STATS_EXTENSION = ".stats"

DEFAULT_RUNTIME_EXTENSION = ".runtime"

DEFAULT_JSON_EXTENSION = ".json"

DEFAULT_YAML_EXTENSION = ".yaml"

DEFAULT_CSV_EXTENSION = ".csv"

DEFAULT_BINARY_EXTENSION = ".bin"

DEFAULT_COMPRESSED_EXTENSION = ".zip"

DEFAULT_TEMP_EXTENSION = ".tmp"

DEFAULT_TIMEOUT = 10.0

DEFAULT_BUFFER_SIZE = 8192


# ============================================================
# Enumerations
# ============================================================

class FileFormat(Enum):
    """Supported serialization formats."""

    JSON = "json"

    YAML = "yaml"

    CSV = "csv"

    BINARY = "binary"

    PICKLE = "pickle"

    ZIP = "zip"

    UNKNOWN = "unknown"


class CompressionType(Enum):
    """Compression algorithms."""

    NONE = "none"

    ZIP = "zip"

    GZIP = "gzip"


class BackupMode(Enum):
    """Backup behaviour."""

    NEVER = "never"

    BEFORE_SAVE = "before_save"

    ALWAYS = "always"


class MigrationStrategy(Enum):
    """Version migration behaviour."""

    NONE = "none"

    SAFE = "safe"

    FORCE = "force"


class ChecksumAlgorithm(Enum):
    """Supported checksum algorithms."""

    MD5 = "md5"

    SHA1 = "sha1"

    SHA256 = "sha256"

    SHA512 = "sha512"


class IOStatus(Enum):
    """Status returned from IO operations."""

    SUCCESS = "success"

    FAILED = "failed"

    CANCELLED = "cancelled"

    WARNING = "warning"


# ============================================================
# Dataclasses
# ============================================================

@dataclass(slots=True)
class IOConfig:
    """
    Configuration for IOManager.
    """

    encoding: str = DEFAULT_ENCODING

    indent: int = DEFAULT_INDENT

    backup_mode: BackupMode = BackupMode.BEFORE_SAVE

    compression: CompressionType = CompressionType.NONE

    checksum_algorithm: ChecksumAlgorithm = (
        ChecksumAlgorithm.SHA256
    )

    migration_strategy: MigrationStrategy = (
        MigrationStrategy.SAFE
    )

    overwrite_existing: bool = True

    create_directories: bool = True

    validate_before_save: bool = True

    atomic_writes: bool = True

    auto_backup: bool = True

    timeout: float = DEFAULT_TIMEOUT


@dataclass(slots=True)
class IOResult:
    """
    Result returned by IO operations.
    """

    status: IOStatus

    success: bool

    path: Optional[Path] = None

    format: Optional[FileFormat] = None

    message: str = ""

    data: Any = None

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    elapsed_time: float = 0.0


@dataclass(slots=True)
class FileMetadata:
    """
    Metadata describing a file.
    """

    path: Path

    format: FileFormat

    size: int = 0

    created: Optional[datetime] = None

    modified: Optional[datetime] = None

    checksum: Optional[str] = None

    version: str = IO_VERSION


@dataclass(slots=True)
class BackupInfo:
    """
    Information about a backup.
    """

    original: Path

    backup: Path

    created: datetime = field(
        default_factory=datetime.now
    )

    size: int = 0


@dataclass(slots=True)
class ProjectSnapshot:
    """
    Serializable project snapshot.
    """

    version: str = IO_VERSION

    created: datetime = field(
        default_factory=datetime.now
    )

    mappings: Dict[str, Any] = field(
        default_factory=dict
    )

    presets: Dict[str, Any] = field(
        default_factory=dict
    )

    statistics: Dict[str, Any] = field(
        default_factory=dict
    )

    runtime: Dict[str, Any] = field(
        default_factory=dict
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )


# ============================================================
# IO Manager
# ============================================================

class IOManager:
    """
    Centralized Input / Output manager.

    Every file operation performed by the ARKit Mapper
    should go through this class.
    """

    def __init__(
        self,
        config: Optional[IOConfig] = None,
    ) -> None:

        self.config = config or IOConfig()

        self._lock = threading.RLock()

        #
        # Registered serializers
        #

        self._serializers: Dict[
            FileFormat,
            Callable,
        ] = {}

        #
        # Registered deserializers
        #

        self._deserializers: Dict[
            FileFormat,
            Callable,
        ] = {}

        #
        # Operation history
        #

        self._history: List[IOResult] = []

        #
        # Statistics
        #

        self._successful_operations = 0

        self._failed_operations = 0

        self._start_time = time.time()

        #
        # Register built-in formats
        #

        self._register_builtin_formats()

    # =======================================================
    # Properties
    # =======================================================

    @property
    def uptime(self) -> float:
        """Manager uptime in seconds."""
        return time.time() - self._start_time

    @property
    def history(self) -> List[IOResult]:
        """Operation history."""
        return list(self._history)

    @property
    def successful_operations(self) -> int:
        """Successful IO operations."""
        return self._successful_operations

    @property
    def failed_operations(self) -> int:
        """Failed IO operations."""
        return self._failed_operations

    @property
    def total_operations(self) -> int:
        """Total IO operations."""
        return (
            self._successful_operations
            + self._failed_operations
        )

    @property
    def registered_formats(self) -> List[FileFormat]:
        """Supported formats."""
        return list(self._serializers.keys())

    # =======================================================
    # Internal Registration
    # =======================================================

    def _register_builtin_formats(self) -> None:
        """
        Register built-in serializers.

        Actual implementations are added in later parts.
        """

        self._serializers = {}

        self._deserializers = {}
# ============================================================
# Part 1.1 - Path Utilities
# ============================================================

    def normalize_path(
        self,
        path: Union[str, Path],
    ) -> Path:
        """
        Convert to an absolute normalized Path.
        """

        return Path(path).expanduser().resolve()

    # -----------------------------------------------------

    def exists(
        self,
        path: Union[str, Path],
    ) -> bool:
        """
        Check whether a path exists.
        """

        return self.normalize_path(path).exists()

    # -----------------------------------------------------

    def is_file(
        self,
        path: Union[str, Path],
    ) -> bool:
        """
        Check whether path is a file.
        """

        return self.normalize_path(path).is_file()

    # -----------------------------------------------------

    def is_directory(
        self,
        path: Union[str, Path],
    ) -> bool:
        """
        Check whether path is a directory.
        """

        return self.normalize_path(path).is_dir()

    # -----------------------------------------------------

    def create_directory(
        self,
        directory: Union[str, Path],
        *,
        parents: bool = True,
        exist_ok: bool = True,
    ) -> Path:
        """
        Create a directory if it does not exist.
        """

        directory = self.normalize_path(directory)

        directory.mkdir(
            parents=parents,
            exist_ok=exist_ok,
        )

        return directory

    # -----------------------------------------------------

    def ensure_parent_directory(
        self,
        filepath: Union[str, Path],
    ) -> Path:
        """
        Ensure the parent directory exists.
        """

        filepath = self.normalize_path(filepath)

        if self.config.create_directories:

            filepath.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

        return filepath

    # -----------------------------------------------------

    def delete(
        self,
        path: Union[str, Path],
        *,
        missing_ok: bool = True,
    ) -> bool:
        """
        Delete a file.
        """

        path = self.normalize_path(path)

        if not path.exists():

            return missing_ok

        path.unlink()

        return True

    # -----------------------------------------------------

    def rename(
        self,
        source: Union[str, Path],
        destination: Union[str, Path],
    ) -> Path:
        """
        Rename or move a file.
        """

        source = self.normalize_path(source)

        destination = self.ensure_parent_directory(
            destination
        )

        return source.rename(destination)

    # -----------------------------------------------------

    def copy(
        self,
        source: Union[str, Path],
        destination: Union[str, Path],
    ) -> Path:
        """
        Copy a file.
        """

        source = self.normalize_path(source)

        destination = self.ensure_parent_directory(
            destination
        )

        shutil.copy2(
            source,
            destination,
        )

        return destination

    # -----------------------------------------------------

    def move(
        self,
        source: Union[str, Path],
        destination: Union[str, Path],
    ) -> Path:
        """
        Move a file.
        """

        source = self.normalize_path(source)

        destination = self.ensure_parent_directory(
            destination
        )

        shutil.move(
            str(source),
            str(destination),
        )

        return destination

    # -----------------------------------------------------

    def temporary_file(
        self,
        *,
        suffix: str = DEFAULT_TEMP_EXTENSION,
        prefix: str = "arkit_",
        directory: Optional[
            Union[str, Path]
        ] = None,
    ) -> Path:
        """
        Create a temporary file.

        The file is created and closed immediately.
        """

        fd, filename = tempfile.mkstemp(

            suffix=suffix,

            prefix=prefix,

            dir=None
            if directory is None
            else str(
                self.normalize_path(directory)
            ),

        )

        os.close(fd)

        return Path(filename)

    # -----------------------------------------------------

    def file_size(
        self,
        path: Union[str, Path],
    ) -> int:
        """
        Return file size in bytes.
        """

        path = self.normalize_path(path)

        return path.stat().st_size

    # -----------------------------------------------------

    def modification_time(
        self,
        path: Union[str, Path],
    ) -> datetime:
        """
        Last modification time.
        """

        path = self.normalize_path(path)

        return datetime.fromtimestamp(
            path.stat().st_mtime
        )

    # -----------------------------------------------------

    def creation_time(
        self,
        path: Union[str, Path],
    ) -> datetime:
        """
        File creation time.
        """

        path = self.normalize_path(path)

        return datetime.fromtimestamp(
            path.stat().st_ctime
        )

    # -----------------------------------------------------

    def extension(
        self,
        path: Union[str, Path],
    ) -> str:
        """
        Return lowercase file extension.
        """

        return self.normalize_path(
            path
        ).suffix.lower()

    # -----------------------------------------------------

    def stem(
        self,
        path: Union[str, Path],
    ) -> str:
        """
        Return filename without extension.
        """

        return self.normalize_path(
            path
        ).stem

    # -----------------------------------------------------

    def filename(
        self,
        path: Union[str, Path],
    ) -> str:
        """
        Return filename.
        """

        return self.normalize_path(
            path
        ).name

    # -----------------------------------------------------

    def parent_directory(
        self,
        path: Union[str, Path],
    ) -> Path:
        """
        Return parent directory.
        """

        return self.normalize_path(
            path
        ).parent

    # -----------------------------------------------------

    def relative_path(
        self,
        path: Union[str, Path],
        start: Union[str, Path],
    ) -> Path:
        """
        Compute relative path.
        """

        return Path(

            os.path.relpath(

                self.normalize_path(path),

                self.normalize_path(start),

            )

        )

    # -----------------------------------------------------

    def file_metadata(
        self,
        path: Union[str, Path],
    ) -> FileMetadata:
        """
        Build FileMetadata from a path.
        """

        path = self.normalize_path(path)

        return FileMetadata(

            path=path,

            format=self.detect_format(path),

            size=path.stat().st_size,

            created=datetime.fromtimestamp(
                path.stat().st_ctime
            ),

            modified=datetime.fromtimestamp(
                path.stat().st_mtime
            ),

        )

    # -----------------------------------------------------

    def touch(
        self,
        path: Union[str, Path],
    ) -> Path:
        """
        Create an empty file if it
        does not exist.
        """

        path = self.ensure_parent_directory(
            path
        )

        path.touch(
            exist_ok=True
        )

        return path

    # -----------------------------------------------------

    def resolve_unique_path(
        self,
        path: Union[str, Path],
    ) -> Path:
        """
        Prevent overwriting by generating
        filename_1.ext, filename_2.ext...
        """

        path = self.normalize_path(path)

        if not path.exists():

            return path

        stem = path.stem

        suffix = path.suffix

        parent = path.parent

        counter = 1

        while True:

            candidate = parent / (
                f"{stem}_{counter}{suffix}"
            )

            if not candidate.exists():

                return candidate

            counter += 1
# ============================================================
# Part 1.2 - File Validation
# ============================================================

    #
    # Supported extensions
    #

    _FORMAT_EXTENSIONS = {

        FileFormat.JSON: {
            ".json",
        },

        FileFormat.YAML: {
            ".yaml",
            ".yml",
        },

        FileFormat.CSV: {
            ".csv",
        },

        FileFormat.BINARY: {
            ".bin",
        },

        FileFormat.PICKLE: {
            ".pickle",
            ".pkl",
        },

        FileFormat.ZIP: {
            ".zip",
            ".gz",
        },

    }

    # -----------------------------------------------------

    def detect_format(
        self,
        path: Union[str, Path],
    ) -> FileFormat:
        """
        Detect the file format from its extension.
        """

        extension = self.extension(path)

        for fmt, extensions in self._FORMAT_EXTENSIONS.items():

            if extension in extensions:

                return fmt

        return FileFormat.UNKNOWN

    # -----------------------------------------------------

    def validate_exists(
        self,
        path: Union[str, Path],
    ) -> None:
        """
        Raise if file does not exist.
        """

        path = self.normalize_path(path)

        if not path.exists():

            raise FileIOError(
                f"File does not exist: {path}"
            )

    # -----------------------------------------------------

    def validate_file(
        self,
        path: Union[str, Path],
    ) -> None:
        """
        Ensure path is a regular file.
        """

        self.validate_exists(path)

        path = self.normalize_path(path)

        if not path.is_file():

            raise FileIOError(
                f"Not a file: {path}"
            )

    # -----------------------------------------------------

    def validate_directory(
        self,
        path: Union[str, Path],
    ) -> None:
        """
        Ensure path is a directory.
        """

        self.validate_exists(path)

        path = self.normalize_path(path)

        if not path.is_dir():

            raise FileIOError(
                f"Not a directory: {path}"
            )

    # -----------------------------------------------------

    def validate_extension(
        self,
        path: Union[str, Path],
        expected: Union[
            FileFormat,
            Sequence[FileFormat],
        ],
    ) -> FileFormat:
        """
        Validate file extension.
        """

        detected = self.detect_format(path)

        if isinstance(expected, FileFormat):

            expected = [expected]

        if detected not in expected:

            names = ", ".join(

                fmt.value

                for fmt in expected

            )

            raise FileFormatError(

                f"Expected {names}, "

                f"got {detected.value}"

            )

        return detected

    # -----------------------------------------------------

    def validate_readable(
        self,
        path: Union[str, Path],
    ) -> None:
        """
        Ensure the file is readable.
        """

        path = self.normalize_path(path)

        self.validate_file(path)

        if not os.access(path, os.R_OK):

            raise FileIOError(

                f"File is not readable: {path}"

            )

    # -----------------------------------------------------

    def validate_writable(
        self,
        path: Union[str, Path],
    ) -> None:
        """
        Ensure the destination is writable.
        """

        path = self.normalize_path(path)

        parent = path.parent

        if not parent.exists():

            if self.config.create_directories:

                parent.mkdir(

                    parents=True,

                    exist_ok=True,

                )

            else:

                raise FileIOError(

                    f"Directory does not exist: {parent}"

                )

        if not os.access(parent, os.W_OK):

            raise FileIOError(

                f"Directory not writable: {parent}"

            )

    # -----------------------------------------------------

    def validate_not_empty(
        self,
        path: Union[str, Path],
    ) -> None:
        """
        Ensure the file is not empty.
        """

        self.validate_file(path)

        if self.file_size(path) == 0:

            raise FileIOError(

                f"File is empty: {path}"

            )

    # -----------------------------------------------------

    def validate_json(
        self,
        path: Union[str, Path],
    ) -> None:
        """
        Validate JSON syntax.
        """

        self.validate_extension(

            path,

            FileFormat.JSON,

        )

        self.validate_readable(path)

        try:

            with open(

                path,

                "r",

                encoding=self.config.encoding,

            ) as fp:

                json.load(fp)

        except Exception as exc:

            raise SerializationError(

                f"Invalid JSON: {path}"

            ) from exc

    # -----------------------------------------------------

    def validate_yaml(
        self,
        path: Union[str, Path],
    ) -> None:
        """
        Validate YAML syntax.
        """

        if yaml is None:

            raise FileIOError(

                "PyYAML is not installed."

            )

        self.validate_extension(

            path,

            FileFormat.YAML,

        )

        self.validate_readable(path)

        try:

            with open(

                path,

                "r",

                encoding=self.config.encoding,

            ) as fp:

                yaml.safe_load(fp)

        except Exception as exc:

            raise SerializationError(

                f"Invalid YAML: {path}"

            ) from exc

    # -----------------------------------------------------

    def validate_csv(
        self,
        path: Union[str, Path],
    ) -> None:
        """
        Validate CSV formatting.
        """

        self.validate_extension(

            path,

            FileFormat.CSV,

        )

        self.validate_readable(path)

        try:

            with open(

                path,

                newline="",

                encoding=self.config.encoding,

            ) as fp:

                reader = csv.reader(fp)

                for _ in reader:

                    pass

        except Exception as exc:

            raise SerializationError(

                f"Invalid CSV: {path}"

            ) from exc

    # -----------------------------------------------------

    def validate_binary(
        self,
        path: Union[str, Path],
    ) -> None:
        """
        Validate binary file.
        """

        self.validate_extension(

            path,

            (

                FileFormat.BINARY,

                FileFormat.PICKLE,

            ),

        )

        self.validate_readable(path)

    # -----------------------------------------------------

    def validate_save_path(
        self,
        path: Union[str, Path],
        file_format: FileFormat,
    ) -> Path:
        """
        Validate a destination path before saving.
        """

        path = self.ensure_parent_directory(path)

        self.validate_writable(path)

        self.validate_extension(

            path,

            file_format,

        )

        return path

    # -----------------------------------------------------

    def validate(
        self,
        path: Union[str, Path],
    ) -> bool:
        """
        Generic validation entry point.
        """

        fmt = self.detect_format(path)

        if fmt == FileFormat.JSON:

            self.validate_json(path)

        elif fmt == FileFormat.YAML:

            self.validate_yaml(path)

        elif fmt == FileFormat.CSV:

            self.validate_csv(path)

        elif fmt in (

            FileFormat.BINARY,

            FileFormat.PICKLE,

        ):

            self.validate_binary(path)

        else:

            raise FileFormatError(

                f"Unsupported format: {path}"

            )

        return True

    # -----------------------------------------------------

    def is_valid(
        self,
        path: Union[str, Path],
    ) -> bool:
        """
        Safe validation.

        Returns False instead of raising.
        """

        try:

            return self.validate(path)

        except Exception:

            return False
# ============================================================
# Part 1.3 - JSON Reader / Writer
# ============================================================

    def load_json(
        self,
        path: Union[str, Path],
        *,
        validate: bool = True,
    ) -> Any:
        """
        Load JSON data from disk.

        Args:
            path:
                JSON file.

            validate:
                Validate before loading.

        Returns:
            Parsed Python object.
        """

        start = time.perf_counter()

        path = self.normalize_path(path)

        try:

            if validate:

                self.validate_json(path)

            with path.open(

                "r",

                encoding=self.config.encoding,

            ) as fp:

                data = json.load(fp)

            elapsed = time.perf_counter() - start

            result = IOResult(

                status=IOStatus.SUCCESS,

                success=True,

                path=path,

                format=FileFormat.JSON,

                data=data,

                elapsed_time=elapsed,

            )

            self._history.append(result)

            self._successful_operations += 1

            return data

        except Exception as exc:

            elapsed = time.perf_counter() - start

            result = IOResult(

                status=IOStatus.FAILED,

                success=False,

                path=path,

                format=FileFormat.JSON,

                message=str(exc),

                elapsed_time=elapsed,

            )

            self._history.append(result)

            self._failed_operations += 1

            raise FileIOError(

                f"Unable to load JSON file: {path}"

            ) from exc

    # -----------------------------------------------------

    def save_json(
        self,
        path: Union[str, Path],
        data: Any,
        *,
        indent: Optional[int] = None,
        sort_keys: bool = False,
        ensure_ascii: bool = False,
    ) -> IOResult:
        """
        Save Python object as JSON.
        """

        start = time.perf_counter()

        path = self.normalize_path(path)

        indent = (

            self.config.indent

            if indent is None

            else indent

        )

        try:

            self.validate_save_path(

                path,

                FileFormat.JSON,

            )

            if self.config.atomic_writes:

                self.atomic_save_json(

                    path,

                    data,

                    indent=indent,

                    sort_keys=sort_keys,

                    ensure_ascii=ensure_ascii,

                )

            else:

                with path.open(

                    "w",

                    encoding=self.config.encoding,

                ) as fp:

                    json.dump(

                        data,

                        fp,

                        indent=indent,

                        sort_keys=sort_keys,

                        ensure_ascii=ensure_ascii,

                    )

            elapsed = time.perf_counter() - start

            result = IOResult(

                status=IOStatus.SUCCESS,

                success=True,

                path=path,

                format=FileFormat.JSON,

                data=data,

                elapsed_time=elapsed,

            )

            self._history.append(result)

            self._successful_operations += 1

            return result

        except Exception as exc:

            elapsed = time.perf_counter() - start

            result = IOResult(

                status=IOStatus.FAILED,

                success=False,

                path=path,

                format=FileFormat.JSON,

                message=str(exc),

                elapsed_time=elapsed,

            )

            self._history.append(result)

            self._failed_operations += 1

            raise FileIOError(

                f"Unable to save JSON file: {path}"

            ) from exc

    # -----------------------------------------------------

    def loads_json(
        self,
        text: str,
    ) -> Any:
        """
        Deserialize JSON string.
        """

        try:

            return json.loads(text)

        except Exception as exc:

            raise SerializationError(

                "Invalid JSON string."

            ) from exc

    # -----------------------------------------------------

    def dumps_json(
        self,
        data: Any,
        *,
        indent: Optional[int] = None,
        sort_keys: bool = False,
        ensure_ascii: bool = False,
    ) -> str:
        """
        Serialize object into JSON string.
        """

        indent = (

            self.config.indent

            if indent is None

            else indent

        )

        try:

            return json.dumps(

                data,

                indent=indent,

                sort_keys=sort_keys,

                ensure_ascii=ensure_ascii,

            )

        except Exception as exc:

            raise SerializationError(

                "Unable to serialize JSON."

            ) from exc

    # -----------------------------------------------------

    def append_json(
        self,
        path: Union[str, Path],
        value: Any,
    ) -> IOResult:
        """
        Append an item to a JSON list.

        If the file does not exist,
        a new list is created.
        """

        if self.exists(path):

            data = self.load_json(path)

        else:

            data = []

        if not isinstance(data, list):

            raise SerializationError(

                "JSON root must be a list."

            )

        data.append(value)

        return self.save_json(

            path,

            data,

        )

    # -----------------------------------------------------

    def update_json(
        self,
        path: Union[str, Path],
        values: Dict[str, Any],
    ) -> IOResult:
        """
        Update a JSON dictionary.
        """

        if self.exists(path):

            data = self.load_json(path)

        else:

            data = {}

        if not isinstance(data, dict):

            raise SerializationError(

                "JSON root must be an object."

            )

        data.update(values)

        return self.save_json(

            path,

            data,

        )

    # -----------------------------------------------------

    def pretty_print_json(
        self,
        data: Any,
    ) -> str:
        """
        Pretty formatted JSON.
        """

        return self.dumps_json(

            data,

            indent=4,

            sort_keys=True,

        )

    # -----------------------------------------------------

    def minify_json(
        self,
        data: Any,
    ) -> str:
        """
        Compact JSON string.
        """

        try:

            return json.dumps(

                data,

                separators=(",", ":"),

                ensure_ascii=False,

            )

        except Exception as exc:

            raise SerializationError(

                "Unable to minify JSON."

            ) from exc

    # -----------------------------------------------------

    def json_size(
        self,
        data: Any,
    ) -> int:
        """
        Size of serialized JSON
        in bytes.
        """

        return len(

            self.minify_json(data).encode(

                self.config.encoding

            )

        )

    # -----------------------------------------------------

    def read_json_metadata(
        self,
        path: Union[str, Path],
    ) -> FileMetadata:
        """
        Read metadata for a JSON file.
        """

        self.validate_json(path)

        metadata = self.file_metadata(path)

        metadata.checksum = self.checksum(path)

        return metadata

    # -----------------------------------------------------

    def register_json_serializer(
        self,
        serializer: Callable[[Any], Any],
    ) -> None:
        """
        Register a custom JSON serializer.
        """

        self._serializers[
            FileFormat.JSON

        ] = serializer

    # -----------------------------------------------------

    def register_json_deserializer(
        self,
        deserializer: Callable[[Any], Any],
    ) -> None:
        """
        Register a custom JSON deserializer.
        """

        self._deserializers[
            FileFormat.JSON

        ] = deserializer
# ============================================================
# Part 1.4 - YAML Reader / Writer
# ============================================================

    def load_yaml(
        self,
        path: Union[str, Path],
        *,
        validate: bool = True,
    ) -> Any:
        """
        Load a YAML file.

        Returns:
            Python object.
        """

        if yaml is None:

            raise FileIOError(
                "PyYAML is not installed."
            )

        start = time.perf_counter()

        path = self.normalize_path(path)

        try:

            if validate:

                self.validate_yaml(path)

            with path.open(
                "r",
                encoding=self.config.encoding,
            ) as fp:

                data = yaml.safe_load(fp)

            elapsed = time.perf_counter() - start

            result = IOResult(

                status=IOStatus.SUCCESS,

                success=True,

                path=path,

                format=FileFormat.YAML,

                data=data,

                elapsed_time=elapsed,

            )

            self._history.append(result)

            self._successful_operations += 1

            return data

        except Exception as exc:

            elapsed = time.perf_counter() - start

            self._history.append(

                IOResult(

                    status=IOStatus.FAILED,

                    success=False,

                    path=path,

                    format=FileFormat.YAML,

                    message=str(exc),

                    elapsed_time=elapsed,

                )

            )

            self._failed_operations += 1

            raise FileIOError(

                f"Unable to load YAML: {path}"

            ) from exc

    # -----------------------------------------------------

    def save_yaml(
        self,
        path: Union[str, Path],
        data: Any,
        *,
        default_flow_style: bool = False,
        sort_keys: bool = False,
    ) -> IOResult:
        """
        Save a YAML file.
        """

        if yaml is None:

            raise FileIOError(
                "PyYAML is not installed."
            )

        start = time.perf_counter()

        path = self.normalize_path(path)

        try:

            self.validate_save_path(

                path,

                FileFormat.YAML,

            )

            if self.config.atomic_writes:

                self.atomic_save_yaml(

                    path,

                    data,

                    default_flow_style=default_flow_style,

                    sort_keys=sort_keys,

                )

            else:

                with path.open(
                    "w",
                    encoding=self.config.encoding,
                ) as fp:

                    yaml.safe_dump(

                        data,

                        fp,

                        default_flow_style=default_flow_style,

                        sort_keys=sort_keys,

                        allow_unicode=True,

                    )

            elapsed = time.perf_counter() - start

            result = IOResult(

                status=IOStatus.SUCCESS,

                success=True,

                path=path,

                format=FileFormat.YAML,

                data=data,

                elapsed_time=elapsed,

            )

            self._history.append(result)

            self._successful_operations += 1

            return result

        except Exception as exc:

            elapsed = time.perf_counter() - start

            self._history.append(

                IOResult(

                    status=IOStatus.FAILED,

                    success=False,

                    path=path,

                    format=FileFormat.YAML,

                    message=str(exc),

                    elapsed_time=elapsed,

                )

            )

            self._failed_operations += 1

            raise FileIOError(

                f"Unable to save YAML: {path}"

            ) from exc

    # -----------------------------------------------------

    def loads_yaml(
        self,
        text: str,
    ) -> Any:
        """
        Deserialize a YAML string.
        """

        if yaml is None:

            raise FileIOError(
                "PyYAML is not installed."
            )

        try:

            return yaml.safe_load(text)

        except Exception as exc:

            raise SerializationError(

                "Invalid YAML string."

            ) from exc

    # -----------------------------------------------------

    def dumps_yaml(
        self,
        data: Any,
        *,
        default_flow_style: bool = False,
        sort_keys: bool = False,
    ) -> str:
        """
        Serialize object to YAML.
        """

        if yaml is None:

            raise FileIOError(
                "PyYAML is not installed."
            )

        try:

            return yaml.safe_dump(

                data,

                default_flow_style=default_flow_style,

                sort_keys=sort_keys,

                allow_unicode=True,

            )

        except Exception as exc:

            raise SerializationError(

                "Unable to serialize YAML."

            ) from exc

    # -----------------------------------------------------

    def append_yaml(
        self,
        path: Union[str, Path],
        value: Any,
    ) -> IOResult:
        """
        Append to a YAML list.
        """

        if self.exists(path):

            data = self.load_yaml(path)

        else:

            data = []

        if not isinstance(data, list):

            raise SerializationError(

                "YAML root must be a list."

            )

        data.append(value)

        return self.save_yaml(

            path,

            data,

        )

    # -----------------------------------------------------

    def update_yaml(
        self,
        path: Union[str, Path],
        values: Dict[str, Any],
    ) -> IOResult:
        """
        Update a YAML dictionary.
        """

        if self.exists(path):

            data = self.load_yaml(path)

        else:

            data = {}

        if not isinstance(data, dict):

            raise SerializationError(

                "YAML root must be a dictionary."

            )

        data.update(values)

        return self.save_yaml(

            path,

            data,

        )

    # -----------------------------------------------------

    def yaml_size(
        self,
        data: Any,
    ) -> int:
        """
        Serialized YAML size in bytes.
        """

        return len(

            self.dumps_yaml(data).encode(

                self.config.encoding

            )

        )

    # -----------------------------------------------------

    def read_yaml_metadata(
        self,
        path: Union[str, Path],
    ) -> FileMetadata:
        """
        Read YAML metadata.
        """

        self.validate_yaml(path)

        metadata = self.file_metadata(path)

        metadata.checksum = self.checksum(path)

        return metadata

    # -----------------------------------------------------

    def register_yaml_serializer(
        self,
        serializer: Callable[[Any], Any],
    ) -> None:
        """
        Register custom YAML serializer.
        """

        self._serializers[
            FileFormat.YAML
        ] = serializer

    # -----------------------------------------------------

    def register_yaml_deserializer(
        self,
        deserializer: Callable[[Any], Any],
    ) -> None:
        """
        Register custom YAML deserializer.
        """

        self._deserializers[
            FileFormat.YAML
        ] = deserializer

    # -----------------------------------------------------

    def yaml_to_json(
        self,
        yaml_path: Union[str, Path],
        json_path: Union[str, Path],
    ) -> IOResult:
        """
        Convert YAML → JSON.
        """

        data = self.load_yaml(yaml_path)

        return self.save_json(

            json_path,

            data,

        )

    # -----------------------------------------------------

    def json_to_yaml(
        self,
        json_path: Union[str, Path],
        yaml_path: Union[str, Path],
    ) -> IOResult:
        """
        Convert JSON → YAML.
        """

        data = self.load_json(json_path)

        return self.save_yaml(

            yaml_path,

            data,

        )
# ============================================================
# Part 1.4 - YAML Reader / Writer
# ============================================================

    def load_yaml(
        self,
        path: Union[str, Path],
        *,
        validate: bool = True,
    ) -> Any:
        """
        Load a YAML file.

        Returns:
            Python object.
        """

        if yaml is None:

            raise FileIOError(
                "PyYAML is not installed."
            )

        start = time.perf_counter()

        path = self.normalize_path(path)

        try:

            if validate:

                self.validate_yaml(path)

            with path.open(
                "r",
                encoding=self.config.encoding,
            ) as fp:

                data = yaml.safe_load(fp)

            elapsed = time.perf_counter() - start

            result = IOResult(

                status=IOStatus.SUCCESS,

                success=True,

                path=path,

                format=FileFormat.YAML,

                data=data,

                elapsed_time=elapsed,

            )

            self._history.append(result)

            self._successful_operations += 1

            return data

        except Exception as exc:

            elapsed = time.perf_counter() - start

            self._history.append(

                IOResult(

                    status=IOStatus.FAILED,

                    success=False,

                    path=path,

                    format=FileFormat.YAML,

                    message=str(exc),

                    elapsed_time=elapsed,

                )

            )

            self._failed_operations += 1

            raise FileIOError(

                f"Unable to load YAML: {path}"

            ) from exc

    # -----------------------------------------------------

    def save_yaml(
        self,
        path: Union[str, Path],
        data: Any,
        *,
        default_flow_style: bool = False,
        sort_keys: bool = False,
    ) -> IOResult:
        """
        Save a YAML file.
        """

        if yaml is None:

            raise FileIOError(
                "PyYAML is not installed."
            )

        start = time.perf_counter()

        path = self.normalize_path(path)

        try:

            self.validate_save_path(

                path,

                FileFormat.YAML,

            )

            if self.config.atomic_writes:

                self.atomic_save_yaml(

                    path,

                    data,

                    default_flow_style=default_flow_style,

                    sort_keys=sort_keys,

                )

            else:

                with path.open(
                    "w",
                    encoding=self.config.encoding,
                ) as fp:

                    yaml.safe_dump(

                        data,

                        fp,

                        default_flow_style=default_flow_style,

                        sort_keys=sort_keys,

                        allow_unicode=True,

                    )

            elapsed = time.perf_counter() - start

            result = IOResult(

                status=IOStatus.SUCCESS,

                success=True,

                path=path,

                format=FileFormat.YAML,

                data=data,

                elapsed_time=elapsed,

            )

            self._history.append(result)

            self._successful_operations += 1

            return result

        except Exception as exc:

            elapsed = time.perf_counter() - start

            self._history.append(

                IOResult(

                    status=IOStatus.FAILED,

                    success=False,

                    path=path,

                    format=FileFormat.YAML,

                    message=str(exc),

                    elapsed_time=elapsed,

                )

            )

            self._failed_operations += 1

            raise FileIOError(

                f"Unable to save YAML: {path}"

            ) from exc

    # -----------------------------------------------------

    def loads_yaml(
        self,
        text: str,
    ) -> Any:
        """
        Deserialize a YAML string.
        """

        if yaml is None:

            raise FileIOError(
                "PyYAML is not installed."
            )

        try:

            return yaml.safe_load(text)

        except Exception as exc:

            raise SerializationError(

                "Invalid YAML string."

            ) from exc

    # -----------------------------------------------------

    def dumps_yaml(
        self,
        data: Any,
        *,
        default_flow_style: bool = False,
        sort_keys: bool = False,
    ) -> str:
        """
        Serialize object to YAML.
        """

        if yaml is None:

            raise FileIOError(
                "PyYAML is not installed."
            )

        try:

            return yaml.safe_dump(

                data,

                default_flow_style=default_flow_style,

                sort_keys=sort_keys,

                allow_unicode=True,

            )

        except Exception as exc:

            raise SerializationError(

                "Unable to serialize YAML."

            ) from exc

    # -----------------------------------------------------

    def append_yaml(
        self,
        path: Union[str, Path],
        value: Any,
    ) -> IOResult:
        """
        Append to a YAML list.
        """

        if self.exists(path):

            data = self.load_yaml(path)

        else:

            data = []

        if not isinstance(data, list):

            raise SerializationError(

                "YAML root must be a list."

            )

        data.append(value)

        return self.save_yaml(

            path,

            data,

        )

    # -----------------------------------------------------

    def update_yaml(
        self,
        path: Union[str, Path],
        values: Dict[str, Any],
    ) -> IOResult:
        """
        Update a YAML dictionary.
        """

        if self.exists(path):

            data = self.load_yaml(path)

        else:

            data = {}

        if not isinstance(data, dict):

            raise SerializationError(

                "YAML root must be a dictionary."

            )

        data.update(values)

        return self.save_yaml(

            path,

            data,

        )

    # -----------------------------------------------------

    def yaml_size(
        self,
        data: Any,
    ) -> int:
        """
        Serialized YAML size in bytes.
        """

        return len(

            self.dumps_yaml(data).encode(

                self.config.encoding

            )

        )

    # -----------------------------------------------------

    def read_yaml_metadata(
        self,
        path: Union[str, Path],
    ) -> FileMetadata:
        """
        Read YAML metadata.
        """

        self.validate_yaml(path)

        metadata = self.file_metadata(path)

        metadata.checksum = self.checksum(path)

        return metadata

    # -----------------------------------------------------

    def register_yaml_serializer(
        self,
        serializer: Callable[[Any], Any],
    ) -> None:
        """
        Register custom YAML serializer.
        """

        self._serializers[
            FileFormat.YAML
        ] = serializer

    # -----------------------------------------------------

    def register_yaml_deserializer(
        self,
        deserializer: Callable[[Any], Any],
    ) -> None:
        """
        Register custom YAML deserializer.
        """

        self._deserializers[
            FileFormat.YAML
        ] = deserializer

    # -----------------------------------------------------

    def yaml_to_json(
        self,
        yaml_path: Union[str, Path],
        json_path: Union[str, Path],
    ) -> IOResult:
        """
        Convert YAML → JSON.
        """

        data = self.load_yaml(yaml_path)

        return self.save_json(

            json_path,

            data,

        )

    # -----------------------------------------------------

    def json_to_yaml(
        self,
        json_path: Union[str, Path],
        yaml_path: Union[str, Path],
    ) -> IOResult:
        """
        Convert JSON → YAML.
        """

        data = self.load_json(json_path)

        return self.save_yaml(

            yaml_path,

            data,

        )
# ============================================================
# Part 2.0 - Mapping Import / Export
# ============================================================

    def load_mapping(
        self,
        path: Union[str, Path],
        *,
        validate: bool = True,
    ) -> List["ARKitMapping"]:
        """
        Load ARKit mappings from disk.

        Supports:
            - JSON
            - YAML
            - CSV

        Returns:
            List[ARKitMapping]
        """

        from .mapping import ARKitMapping

        path = self.normalize_path(path)

        fmt = self.detect_format(path)

        #
        # Load raw data
        #

        if fmt == FileFormat.JSON:

            raw = self.load_json(
                path,
                validate=validate,
            )

        elif fmt == FileFormat.YAML:

            raw = self.load_yaml(
                path,
                validate=validate,
            )

        elif fmt == FileFormat.CSV:

            raw = self.load_csv(
                path,
                validate=validate,
            )

        else:

            raise FileFormatError(
                f"Unsupported mapping format: {fmt.value}"
            )

        if raw is None:

            return []

        #
        # Deserialize
        #

        mappings = []

        for item in raw:

            if hasattr(
                ARKitMapping,
                "from_dict",
            ):

                mapping = ARKitMapping.from_dict(
                    item
                )

            else:

                mapping = ARKitMapping(
                    **item
                )

            mappings.append(mapping)

        return mappings

    # -----------------------------------------------------

    def save_mapping(
        self,
        path: Union[str, Path],
        mappings: Sequence["ARKitMapping"],
        *,
        format: Optional[
            FileFormat
        ] = None,
    ) -> IOResult:
        """
        Save mappings.

        Format is inferred from the extension unless
        explicitly specified.
        """

        path = self.normalize_path(path)

        if format is None:

            format = self.detect_format(path)

        #
        # Serialize
        #

        data = []

        for mapping in mappings:

            if hasattr(
                mapping,
                "to_dict",
            ):

                data.append(
                    mapping.to_dict()
                )

            else:

                data.append(
                    vars(mapping)
                )

        #
        # Save
        #

        if format == FileFormat.JSON:

            return self.save_json(
                path,
                data,
            )

        elif format == FileFormat.YAML:

            return self.save_yaml(
                path,
                data,
            )

        elif format == FileFormat.CSV:

            return self.save_csv(
                path,
                data,
            )

        raise FileFormatError(
            f"Unsupported mapping format: {format.value}"
        )

    # -----------------------------------------------------

    def export_mapping(
        self,
        mappings: Sequence["ARKitMapping"],
        destination: Union[str, Path],
    ) -> IOResult:
        """
        Export mappings.

        Alias of save_mapping().
        """

        return self.save_mapping(
            destination,
            mappings,
        )

    # -----------------------------------------------------

    def import_mapping(
        self,
        source: Union[str, Path],
    ) -> List["ARKitMapping"]:
        """
        Import mappings.

        Alias of load_mapping().
        """

        return self.load_mapping(
            source,
        )

    # -----------------------------------------------------

    def merge_mappings(
        self,
        *mapping_sets: Sequence["ARKitMapping"],
    ) -> List["ARKitMapping"]:
        """
        Merge multiple mapping collections.

        Duplicate ARKit names are replaced by the
        newest occurrence.
        """

        merged = {}

        for collection in mapping_sets:

            for mapping in collection:

                merged[
                    mapping.arkit_name
                ] = mapping

        return list(
            merged.values()
        )

    # -----------------------------------------------------

    def validate_mapping_file(
        self,
        path: Union[str, Path],
    ) -> bool:
        """
        Validate a mapping file.
        """

        mappings = self.load_mapping(path)

        if not mappings:

            return False

        arkit_names = set()

        rig_names = set()

        for mapping in mappings:

            if mapping.arkit_name in arkit_names:

                raise SerializationError(

                    f"Duplicate ARKit channel: "
                    f"{mapping.arkit_name}"

                )

            if mapping.rig_name in rig_names:

                raise SerializationError(

                    f"Duplicate rig target: "
                    f"{mapping.rig_name}"

                )

            arkit_names.add(
                mapping.arkit_name
            )

            rig_names.add(
                mapping.rig_name
            )

        return True

    # -----------------------------------------------------

    def mapping_statistics(
        self,
        mappings: Sequence["ARKitMapping"],
    ) -> Dict[str, Any]:
        """
        Generate mapping statistics.
        """

        enabled = sum(
            m.enabled
            for m in mappings
        )

        disabled = len(mappings) - enabled

        groups = {}

        for mapping in mappings:

            group = getattr(
                mapping,
                "category",
                "Default",
            )

            groups[group] = (
                groups.get(group, 0)
                + 1
            )

        return {

            "total": len(mappings),

            "enabled": enabled,

            "disabled": disabled,

            "groups": groups,

        }

    # -----------------------------------------------------

    def mapping_to_dataframe(
        self,
        mappings: Sequence["ARKitMapping"],
    ):
        """
        Convert mappings into a pandas DataFrame.

        Raises ImportError if pandas is unavailable.
        """

        import pandas as pd

        rows = []

        for mapping in mappings:

            if hasattr(
                mapping,
                "to_dict",
            ):

                rows.append(
                    mapping.to_dict()
                )

            else:

                rows.append(
                    vars(mapping)
                )

        return pd.DataFrame(rows)

    # -----------------------------------------------------

    def dataframe_to_mapping(
        self,
        dataframe,
    ) -> List["ARKitMapping"]:
        """
        Convert pandas DataFrame into mappings.
        """

        from .mapping import ARKitMapping

        mappings = []

        for row in dataframe.to_dict(
            orient="records"
        ):

            if hasattr(
                ARKitMapping,
                "from_dict",
            ):

                mappings.append(
                    ARKitMapping.from_dict(
                        row
                    )
                )

            else:

                mappings.append(
                    ARKitMapping(
                        **row
                    )
                )

        return mappings

    # -----------------------------------------------------

    def clone_mapping(
        self,
        mappings: Sequence["ARKitMapping"],
    ) -> List["ARKitMapping"]:
        """
        Deep-copy a mapping collection.
        """

        return pickle.loads(
            pickle.dumps(mappings)
        )
# ============================================================
# Part 2.1 - Preset Import / Export
# ============================================================

    def load_preset(
        self,
        path: Union[str, Path],
        *,
        validate: bool = True,
    ) -> Dict[str, float]:
        """
        Load a preset.

        Supported formats:
            • JSON
            • YAML
            • CSV

        Returns
        -------
        Dict[str, float]
            rig_name -> value
        """

        path = self.normalize_path(path)

        fmt = self.detect_format(path)

        if fmt == FileFormat.JSON:

            data = self.load_json(
                path,
                validate=validate,
            )

        elif fmt == FileFormat.YAML:

            data = self.load_yaml(
                path,
                validate=validate,
            )

        elif fmt == FileFormat.CSV:

            rows = self.load_csv(
                path,
                validate=validate,
            )

            data = {}

            for row in rows:

                data[row["rig_name"]] = float(
                    row["value"]
                )

        else:

            raise FileFormatError(
                f"Unsupported preset format: {fmt.value}"
            )

        return {
            k: float(v)
            for k, v in data.items()
        }

    # -----------------------------------------------------

    def save_preset(
        self,
        path: Union[str, Path],
        preset: Dict[str, float],
        *,
        format: Optional[
            FileFormat
        ] = None,
    ) -> IOResult:
        """
        Save a preset.
        """

        path = self.normalize_path(path)

        if format is None:

            format = self.detect_format(path)

        if format == FileFormat.JSON:

            return self.save_json(
                path,
                preset,
            )

        elif format == FileFormat.YAML:

            return self.save_yaml(
                path,
                preset,
            )

        elif format == FileFormat.CSV:

            rows = []

            for rig, value in preset.items():

                rows.append({

                    "rig_name": rig,

                    "value": value,

                })

            return self.save_csv(
                path,
                rows,
            )

        raise FileFormatError(
            f"Unsupported preset format: {format.value}"
        )

    # -----------------------------------------------------

    def import_preset(
        self,
        source: Union[str, Path],
    ) -> Dict[str, float]:
        """
        Alias of load_preset().
        """

        return self.load_preset(source)

    # -----------------------------------------------------

    def export_preset(
        self,
        preset: Dict[str, float],
        destination: Union[str, Path],
    ) -> IOResult:
        """
        Alias of save_preset().
        """

        return self.save_preset(
            destination,
            preset,
        )

    # -----------------------------------------------------

    def validate_preset(
        self,
        preset: Dict[str, float],
    ) -> bool:
        """
        Validate preset values.
        """

        if not isinstance(
            preset,
            dict,
        ):

            raise SerializationError(
                "Preset must be a dictionary."
            )

        for rig, value in preset.items():

            if not isinstance(
                rig,
                str,
            ):

                raise SerializationError(
                    "Rig names must be strings."
                )

            try:

                value = float(value)

            except Exception:

                raise SerializationError(
                    f"Invalid preset value for '{rig}'."
                )

            if value < 0.0 or value > 1.0:

                raise SerializationError(

                    f"Preset value out of range "
                    f"for '{rig}': {value}"

                )

        return True

    # -----------------------------------------------------

    def validate_preset_file(
        self,
        path: Union[str, Path],
    ) -> bool:
        """
        Validate a preset file.
        """

        preset = self.load_preset(path)

        return self.validate_preset(
            preset
        )

    # -----------------------------------------------------

    def merge_presets(
        self,
        *presets: Dict[str, float],
    ) -> Dict[str, float]:
        """
        Merge multiple presets.

        Later presets overwrite earlier ones.
        """

        merged = {}

        for preset in presets:

            merged.update(preset)

        return merged

    # -----------------------------------------------------

    def blend_presets(
        self,
        preset_a: Dict[str, float],
        preset_b: Dict[str, float],
        weight: float = 0.5,
    ) -> Dict[str, float]:
        """
        Blend two presets.

        weight=0 -> preset_a

        weight=1 -> preset_b
        """

        weight = max(
            0.0,
            min(
                1.0,
                weight,
            ),
        )

        result = {}

        keys = (
            set(preset_a.keys())
            |
            set(preset_b.keys())
        )

        for key in keys:

            a = preset_a.get(
                key,
                0.0,
            )

            b = preset_b.get(
                key,
                0.0,
            )

            result[key] = (

                a * (1.0 - weight)

                +

                b * weight

            )

        return result

    # -----------------------------------------------------

    def preset_statistics(
        self,
        preset: Dict[str, float],
    ) -> Dict[str, Any]:
        """
        Generate statistics for a preset.
        """

        values = list(
            preset.values()
        )

        if not values:

            return {

                "count": 0,

                "minimum": 0.0,

                "maximum": 0.0,

                "average": 0.0,

                "active": 0,

            }

        return {

            "count": len(values),

            "minimum": min(values),

            "maximum": max(values),

            "average": sum(values) / len(values),

            "active": sum(

                v > 0.0

                for v in values

            ),

        }

    # -----------------------------------------------------

    def clone_preset(
        self,
        preset: Dict[str, float],
    ) -> Dict[str, float]:
        """
        Deep-copy a preset.
        """

        return pickle.loads(
            pickle.dumps(
                preset
            )
        )

    # -----------------------------------------------------

    def preset_to_dataframe(
        self,
        preset: Dict[str, float],
    ):
        """
        Convert preset to pandas DataFrame.
        """

        import pandas as pd

        rows = []

        for rig, value in preset.items():

            rows.append({

                "rig_name": rig,

                "value": value,

            })

        return pd.DataFrame(rows)

    # -----------------------------------------------------

    def dataframe_to_preset(
        self,
        dataframe,
    ) -> Dict[str, float]:
        """
        Convert pandas DataFrame to preset.
        """

        preset = {}

        for row in dataframe.to_dict(
            orient="records"
        ):

            preset[
                row["rig_name"]
            ] = float(
                row["value"]
            )

        return preset
# ============================================================
# Part 2.3 - Runtime Snapshot Import / Export
# ============================================================

    def save_runtime_snapshot(
        self,
        path: Union[str, Path],
        runtime: Any,
        *,
        format: Optional[FileFormat] = None,
        include_statistics: bool = True,
        include_callbacks: bool = False,
        include_metadata: bool = True,
    ) -> IOResult:
        """
        Save a runtime session snapshot.

        The runtime object may be a RuntimeManager,
        RuntimeSession, or any object implementing
        a to_dict() method.
        """

        path = self.normalize_path(path)

        if format is None:
            format = self.detect_format(path)

        #
        # Serialize runtime
        #

        if hasattr(runtime, "to_dict"):

            data = runtime.to_dict()

        elif isinstance(runtime, dict):

            data = dict(runtime)

        else:

            data = vars(runtime).copy()

        #
        # Remove callback references
        #

        if not include_callbacks:

            data.pop("callbacks", None)
            data.pop("_callbacks", None)
            data.pop("frame_callbacks", None)
            data.pop("update_callbacks", None)

        #
        # Remove statistics if requested
        #

        if not include_statistics:

            data.pop("statistics", None)
            data.pop("_statistics", None)

        #
        # Metadata
        #

        if include_metadata:

            data["_snapshot"] = {

                "created": datetime.now().isoformat(),

                "version": IO_VERSION,

                "type": "runtime",

            }

        #
        # Export
        #

        if format == FileFormat.JSON:

            return self.save_json(
                path,
                data,
            )

        elif format == FileFormat.YAML:

            return self.save_yaml(
                path,
                data,
            )

        elif format == FileFormat.BINARY:

            return self.save_binary(
                path,
                data,
            )

        raise FileFormatError(
            f"Unsupported runtime format: {format.value}"
        )

    # -----------------------------------------------------

    def load_runtime_snapshot(
        self,
        path: Union[str, Path],
        *,
        validate: bool = True,
    ) -> Dict[str, Any]:
        """
        Load a runtime snapshot.

        Returns a dictionary suitable for
        RuntimeManager.from_dict().
        """

        path = self.normalize_path(path)

        fmt = self.detect_format(path)

        if fmt == FileFormat.JSON:

            data = self.load_json(
                path,
                validate=validate,
            )

        elif fmt == FileFormat.YAML:

            data = self.load_yaml(
                path,
                validate=validate,
            )

        elif fmt == FileFormat.BINARY:

            data = self.load_binary(path)

        else:

            raise FileFormatError(
                f"Unsupported runtime snapshot: {fmt.value}"
            )

        return data

    # -----------------------------------------------------

    def export_runtime(
        self,
        runtime: Any,
        destination: Union[str, Path],
    ) -> IOResult:
        """
        Alias of save_runtime_snapshot().
        """

        return self.save_runtime_snapshot(
            destination,
            runtime,
        )

    # -----------------------------------------------------

    def import_runtime(
        self,
        source: Union[str, Path],
    ) -> Dict[str, Any]:
        """
        Alias of load_runtime_snapshot().
        """

        return self.load_runtime_snapshot(
            source,
        )

    # -----------------------------------------------------

    def clone_runtime_snapshot(
        self,
        runtime: Any,
    ) -> Dict[str, Any]:
        """
        Deep-copy a runtime snapshot.
        """

        if hasattr(runtime, "to_dict"):

            runtime = runtime.to_dict()

        return pickle.loads(
            pickle.dumps(runtime)
        )

    # -----------------------------------------------------

    def runtime_snapshot_statistics(
        self,
        snapshot: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate statistics about a runtime snapshot.
        """

        statistics = snapshot.get(
            "statistics",
            {},
        )

        callback_count = 0

        callbacks = snapshot.get(
            "callbacks",
            [],
        )

        if isinstance(callbacks, list):

            callback_count = len(callbacks)

        return {

            "keys": len(snapshot),

            "statistics_keys": len(statistics),

            "callbacks": callback_count,

            "created": snapshot.get(
                "_snapshot",
                {},
            ).get(
                "created",
                None,
            ),

            "version": snapshot.get(
                "_snapshot",
                {},
            ).get(
                "version",
                None,
            ),

        }

    # -----------------------------------------------------

    def validate_runtime_snapshot(
        self,
        snapshot: Dict[str, Any],
    ) -> bool:
        """
        Validate runtime snapshot structure.
        """

        if not isinstance(snapshot, dict):

            raise SerializationError(
                "Runtime snapshot must be a dictionary."
            )

        metadata = snapshot.get(
            "_snapshot"
        )

        if metadata is None:

            raise SerializationError(
                "Missing runtime metadata."
            )

        if "version" not in metadata:

            raise SerializationError(
                "Snapshot version missing."
            )

        return True

    # -----------------------------------------------------

    def validate_runtime_snapshot_file(
        self,
        path: Union[str, Path],
    ) -> bool:
        """
        Validate runtime snapshot file.
        """

        snapshot = self.load_runtime_snapshot(path)

        return self.validate_runtime_snapshot(
            snapshot
        )

    # -----------------------------------------------------

    def runtime_to_dataframe(
        self,
        snapshot: Dict[str, Any],
    ):
        """
        Convert runtime snapshot into a pandas DataFrame.
        """

        import pandas as pd

        rows = []

        for key, value in snapshot.items():

            rows.append({

                "key": key,

                "value": value,

            })

        return pd.DataFrame(rows)

    # -----------------------------------------------------

    def dataframe_to_runtime(
        self,
        dataframe,
    ) -> Dict[str, Any]:
        """
        Convert DataFrame back into a runtime snapshot.
        """

        snapshot = {}

        for row in dataframe.to_dict(
            orient="records"
        ):

            snapshot[
                row["key"]
            ] = row["value"]

        return snapshot

    # -----------------------------------------------------

    def compare_runtime_snapshots(
        self,
        snapshot_a: Dict[str, Any],
        snapshot_b: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Compare two runtime snapshots.

        Returns added, removed,
        modified, and unchanged keys.
        """

        keys_a = set(snapshot_a.keys())
        keys_b = set(snapshot_b.keys())

        added = keys_b - keys_a
        removed = keys_a - keys_b
        common = keys_a & keys_b

        modified = [
            key
            for key in common
            if snapshot_a[key] != snapshot_b[key]
        ]

        unchanged = [
            key
            for key in common
            if snapshot_a[key] == snapshot_b[key]
        ]

        return {

            "added": sorted(added),

            "removed": sorted(removed),

            "modified": sorted(modified),

            "unchanged": sorted(unchanged),

        }
# ============================================================
# Part 2.4 - Project Import / Export
# ============================================================

    def save_project(
        self,
        path: Union[str, Path],
        project: Union[ProjectSnapshot, Dict[str, Any]],
        *,
        format: Optional[FileFormat] = None,
    ) -> IOResult:
        """
        Save a complete ARKit Mapper project.

        A project contains mappings, presets,
        runtime information, statistics and metadata.
        """

        path = self.normalize_path(path)

        if format is None:
            format = self.detect_format(path)

        #
        # Convert dataclass to dictionary
        #

        if isinstance(project, ProjectSnapshot):

            data = {

                "version": project.version,

                "created": project.created.isoformat(),

                "mappings": project.mappings,

                "presets": project.presets,

                "statistics": project.statistics,

                "runtime": project.runtime,

                "metadata": project.metadata,

            }

        else:

            data = dict(project)

        #
        # Ensure required fields exist
        #

        data.setdefault("version", IO_VERSION)

        data.setdefault(
            "created",
            datetime.now().isoformat(),
        )

        data.setdefault("mappings", {})

        data.setdefault("presets", {})

        data.setdefault("statistics", {})

        data.setdefault("runtime", {})

        data.setdefault("metadata", {})

        #
        # Export
        #

        if format == FileFormat.JSON:

            return self.save_json(
                path,
                data,
            )

        elif format == FileFormat.YAML:

            return self.save_yaml(
                path,
                data,
            )

        elif format == FileFormat.BINARY:

            return self.save_binary(
                path,
                data,
            )

        raise FileFormatError(
            f"Unsupported project format: {format.value}"
        )

    # -----------------------------------------------------

    def load_project(
        self,
        path: Union[str, Path],
        *,
        validate: bool = True,
    ) -> ProjectSnapshot:
        """
        Load a complete project.
        """

        path = self.normalize_path(path)

        fmt = self.detect_format(path)

        if fmt == FileFormat.JSON:

            data = self.load_json(
                path,
                validate=validate,
            )

        elif fmt == FileFormat.YAML:

            data = self.load_yaml(
                path,
                validate=validate,
            )

        elif fmt == FileFormat.BINARY:

            data = self.load_binary(path)

        else:

            raise FileFormatError(
                f"Unsupported project format: {fmt.value}"
            )

        if validate:

            self.validate_project(data)

        return ProjectSnapshot(

            version=data.get(
                "version",
                IO_VERSION,
            ),

            created=datetime.fromisoformat(
                data.get(
                    "created",
                    datetime.now().isoformat(),
                )
            ),

            mappings=data.get(
                "mappings",
                {},
            ),

            presets=data.get(
                "presets",
                {},
            ),

            statistics=data.get(
                "statistics",
                {},
            ),

            runtime=data.get(
                "runtime",
                {},
            ),

            metadata=data.get(
                "metadata",
                {},
            ),

        )

    # -----------------------------------------------------

    def export_project(
        self,
        project: Union[
            ProjectSnapshot,
            Dict[str, Any],
        ],
        destination: Union[str, Path],
    ) -> IOResult:
        """
        Alias of save_project().
        """

        return self.save_project(
            destination,
            project,
        )

    # -----------------------------------------------------

    def import_project(
        self,
        source: Union[str, Path],
    ) -> ProjectSnapshot:
        """
        Alias of load_project().
        """

        return self.load_project(source)

    # -----------------------------------------------------

    def validate_project(
        self,
        project: Union[
            ProjectSnapshot,
            Dict[str, Any],
        ],
    ) -> bool:
        """
        Validate project structure.
        """

        if isinstance(
            project,
            ProjectSnapshot,
        ):

            project = {

                "version": project.version,

                "created": project.created,

                "mappings": project.mappings,

                "presets": project.presets,

                "statistics": project.statistics,

                "runtime": project.runtime,

                "metadata": project.metadata,

            }

        required = (

            "version",

            "created",

            "mappings",

            "presets",

            "statistics",

            "runtime",

            "metadata",

        )

        for key in required:

            if key not in project:

                raise SerializationError(

                    f"Project missing '{key}'."

                )

        return True

    # -----------------------------------------------------

    def validate_project_file(
        self,
        path: Union[str, Path],
    ) -> bool:
        """
        Validate a project file.
        """

        project = self.load_project(path)

        return self.validate_project(project)

    # -----------------------------------------------------

    def clone_project(
        self,
        project: Union[
            ProjectSnapshot,
            Dict[str, Any],
        ],
    ) -> ProjectSnapshot:
        """
        Deep-copy a project.
        """

        return pickle.loads(
            pickle.dumps(project)
        )

    # -----------------------------------------------------

    def project_statistics(
        self,
        project: Union[
            ProjectSnapshot,
            Dict[str, Any],
        ],
    ) -> Dict[str, Any]:
        """
        Return project statistics.
        """

        if isinstance(
            project,
            ProjectSnapshot,
        ):

            mappings = project.mappings

            presets = project.presets

            runtime = project.runtime

            statistics = project.statistics

            metadata = project.metadata

        else:

            mappings = project.get(
                "mappings",
                {},
            )

            presets = project.get(
                "presets",
                {},
            )

            runtime = project.get(
                "runtime",
                {},
            )

            statistics = project.get(
                "statistics",
                {},
            )

            metadata = project.get(
                "metadata",
                {},
            )

        return {

            "mapping_count": len(mappings),

            "preset_count": len(presets),

            "runtime_entries": len(runtime),

            "statistics_entries": len(statistics),

            "metadata_entries": len(metadata),

        }

    # -----------------------------------------------------

    def merge_projects(
        self,
        *projects: ProjectSnapshot,
    ) -> ProjectSnapshot:
        """
        Merge multiple projects.

        Later projects overwrite earlier
        values.
        """

        merged = ProjectSnapshot()

        for project in projects:

            merged.mappings.update(
                project.mappings
            )

            merged.presets.update(
                project.presets
            )

            merged.statistics.update(
                project.statistics
            )

            merged.runtime.update(
                project.runtime
            )

            merged.metadata.update(
                project.metadata
            )

            merged.version = project.version

            merged.created = project.created

        return merged

    # -----------------------------------------------------

    def compare_projects(
        self,
        project_a: ProjectSnapshot,
        project_b: ProjectSnapshot,
    ) -> Dict[str, Any]:
        """
        Compare two projects.
        """

        differences = {}

        for field in (

            "mappings",

            "presets",

            "statistics",

            "runtime",

            "metadata",

        ):

            left = getattr(
                project_a,
                field,
            )

            right = getattr(
                project_b,
                field,
            )

            if left != right:

                differences[field] = {

                    "left": left,

                    "right": right,

                }

        return differences

    # -----------------------------------------------------

    def project_to_dataframe(
        self,
        project: ProjectSnapshot,
    ):
        """
        Convert project metadata
        into a pandas DataFrame.
        """

        import pandas as pd

        rows = []

        for section in (

            "mappings",

            "presets",

            "statistics",

            "runtime",

            "metadata",

        ):

            value = getattr(
                project,
                section,
            )

            rows.append({

                "section": section,

                "entries": len(value),

            })

        return pd.DataFrame(rows)
# ============================================================
# Part 2.5 - Backup Manager
# ============================================================

    def create_backup(
        self,
        source: Union[str, Path],
        *,
        destination: Optional[Union[str, Path]] = None,
        timestamp: bool = True,
    ) -> Path:
        """
        Create a backup copy of a file.

        Returns
        -------
        Path
            Backup file path.
        """

        source = self.normalize_path(source)

        self.validate_file(source)

        if destination is None:

            backup_dir = source.parent / "backups"

            backup_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

            name = source.stem

            if timestamp:

                stamp = datetime.now().strftime(
                    "%Y%m%d_%H%M%S"
                )

                filename = (
                    f"{name}_{stamp}"
                    f"{source.suffix}"
                )

            else:

                filename = (
                    f"{name}_backup"
                    f"{source.suffix}"
                )

            destination = backup_dir / filename

        destination = self.normalize_path(destination)

        shutil.copy2(
            source,
            destination,
        )

        return destination

    # -----------------------------------------------------

    def restore_backup(
        self,
        backup_file: Union[str, Path],
        destination: Union[str, Path],
    ) -> IOResult:
        """
        Restore a backup file.
        """

        backup_file = self.normalize_path(
            backup_file
        )

        destination = self.normalize_path(
            destination
        )

        self.validate_file(
            backup_file
        )

        self.ensure_parent_directory(
            destination
        )

        shutil.copy2(
            backup_file,
            destination,
        )

        return IOResult(

            status=IOStatus.SUCCESS,

            success=True,

            path=destination,

            format=self.detect_format(
                destination
            ),

        )

    # -----------------------------------------------------

    def list_backups(
        self,
        source: Union[str, Path],
    ) -> List[Path]:
        """
        List all backups belonging
        to a source file.
        """

        source = self.normalize_path(source)

        backup_dir = (
            source.parent / "backups"
        )

        if not backup_dir.exists():

            return []

        pattern = (
            f"{source.stem}*"
            f"{source.suffix}"
        )

        backups = sorted(

            backup_dir.glob(pattern),

            key=lambda p: p.stat().st_mtime,

            reverse=True,

        )

        return backups

    # -----------------------------------------------------

    def latest_backup(
        self,
        source: Union[str, Path],
    ) -> Optional[Path]:
        """
        Return the newest backup.
        """

        backups = self.list_backups(
            source
        )

        if backups:

            return backups[0]

        return None

    # -----------------------------------------------------

    def delete_backup(
        self,
        backup: Union[str, Path],
    ) -> bool:
        """
        Delete a backup file.
        """

        backup = self.normalize_path(
            backup
        )

        if not backup.exists():

            return False

        backup.unlink()

        return True

    # -----------------------------------------------------

    def delete_all_backups(
        self,
        source: Union[str, Path],
    ) -> int:
        """
        Delete every backup for
        a source file.

        Returns
        -------
        int
            Number removed.
        """

        count = 0

        for backup in self.list_backups(
            source
        ):

            backup.unlink()

            count += 1

        return count

    # -----------------------------------------------------

    def prune_backups(
        self,
        source: Union[str, Path],
        *,
        keep: int = 10,
    ) -> int:
        """
        Keep only the newest N backups.

        Returns
        -------
        int
            Number deleted.
        """

        backups = self.list_backups(
            source
        )

        removed = 0

        for backup in backups[keep:]:

            backup.unlink()

            removed += 1

        return removed

    # -----------------------------------------------------

    def backup_exists(
        self,
        source: Union[str, Path],
    ) -> bool:
        """
        Check whether a backup exists.
        """

        return (
            self.latest_backup(source)
            is not None
        )

    # -----------------------------------------------------

    def backup_statistics(
        self,
        source: Union[str, Path],
    ) -> Dict[str, Any]:
        """
        Return backup statistics.
        """

        backups = self.list_backups(
            source
        )

        total_size = sum(

            b.stat().st_size

            for b in backups

        )

        latest = None

        if backups:

            latest = datetime.fromtimestamp(

                backups[0].stat().st_mtime

            )

        return {

            "count": len(backups),

            "total_size": total_size,

            "latest_backup": latest,

        }

    # -----------------------------------------------------

    def export_backup_manifest(
        self,
        source: Union[str, Path],
        destination: Union[str, Path],
    ) -> IOResult:
        """
        Export a JSON manifest of
        every backup.
        """

        backups = self.list_backups(
            source
        )

        manifest = []

        for backup in backups:

            manifest.append({

                "file": backup.name,

                "path": str(backup),

                "size": backup.stat().st_size,

                "modified": datetime.fromtimestamp(

                    backup.stat().st_mtime

                ).isoformat(),

            })

        return self.save_json(

            destination,

            manifest,

        )

    # -----------------------------------------------------

    def verify_backup(
        self,
        source: Union[str, Path],
        backup: Union[str, Path],
    ) -> bool:
        """
        Verify that a backup matches
        the original using checksums.
        """

        return (

            self.checksum(source)

            ==

            self.checksum(backup)

        )

    # -----------------------------------------------------

    def rotate_backups(
        self,
        source: Union[str, Path],
        *,
        keep: int = 5,
    ) -> Path:
        """
        Create a new backup and
        automatically prune old ones.
        """

        backup = self.create_backup(
            source
        )

        self.prune_backups(

            source,

            keep=keep,

        )

        return backup

    # -----------------------------------------------------

    def restore_latest_backup(
        self,
        source: Union[str, Path],
    ) -> IOResult:
        """
        Restore the newest backup
        over the original file.
        """

        backup = self.latest_backup(
            source
        )

        if backup is None:

            raise FileIOError(
                "No backup available."
            )

        return self.restore_backup(

            backup,

            source,

        )
# ============================================================
# Part 3.0A - Checksums & Hashing Foundation
# ============================================================

#
# Internal hash algorithm registry
#

_HASH_ALGORITHMS = {

    ChecksumAlgorithm.MD5: hashlib.md5,

    ChecksumAlgorithm.SHA1: hashlib.sha1,

    ChecksumAlgorithm.SHA256: hashlib.sha256,

    ChecksumAlgorithm.SHA512: hashlib.sha512,

}

# ------------------------------------------------------------

def _create_hasher(
    self,
    algorithm: Optional[
        ChecksumAlgorithm
    ] = None,
):
    """
    Create a new hash object.

    Parameters
    ----------
    algorithm
        Hash algorithm to use.
        If None, IOConfig.checksum_algorithm
        is used.

    Returns
    -------
    hashlib hash object.
    """

    if algorithm is None:

        algorithm = self.config.checksum_algorithm

    factory = self._HASH_ALGORITHMS.get(
        algorithm
    )

    if factory is None:

        raise FileIOError(

            f"Unsupported checksum algorithm: "
            f"{algorithm}"

        )

    return factory()

# ------------------------------------------------------------

def available_checksum_algorithms(
    self,
) -> List[str]:
    """
    Return supported checksum algorithms.
    """

    return [

        algorithm.value

        for algorithm in self._HASH_ALGORITHMS

    ]

# ------------------------------------------------------------

def hash_bytes(
    self,
    data: bytes,
    *,
    algorithm: Optional[
        ChecksumAlgorithm
    ] = None,
) -> str:
    """
    Compute checksum of raw bytes.
    """

    hasher = self._create_hasher(
        algorithm
    )

    hasher.update(data)

    return hasher.hexdigest()

# ------------------------------------------------------------

def hash_string(
    self,
    text: str,
    *,
    encoding: Optional[str] = None,
    algorithm: Optional[
        ChecksumAlgorithm
    ] = None,
) -> str:
    """
    Compute checksum of a string.
    """

    if encoding is None:

        encoding = self.config.encoding

    return self.hash_bytes(

        text.encode(encoding),

        algorithm=algorithm,

    )

# ------------------------------------------------------------

def hash_object(
    self,
    obj: Any,
    *,
    algorithm: Optional[
        ChecksumAlgorithm
    ] = None,
) -> str:
    """
    Compute checksum of a Python object.

    Objects are serialized to JSON
    before hashing.

    Falls back to pickle if JSON
    serialization fails.
    """

    try:

        serialized = json.dumps(

            obj,

            sort_keys=True,

            default=str,

        ).encode(

            self.config.encoding

        )

    except Exception:

        serialized = pickle.dumps(obj)

    return self.hash_bytes(

        serialized,

        algorithm=algorithm,

    )

# ------------------------------------------------------------

def checksum(
    self,
    source: Union[
        str,
        Path,
        bytes,
        bytearray,
    ],
    *,
    algorithm: Optional[
        ChecksumAlgorithm
    ] = None,
) -> str:
    """
    Universal checksum function.

    Accepts

        • file paths

        • bytes

        • bytearray

        • strings

    Returns
    -------
    Hex digest.
    """

    #
    # Bytes
    #

    if isinstance(

        source,

        (bytes, bytearray),

    ):

        return self.hash_bytes(

            bytes(source),

            algorithm=algorithm,

        )

    #
    # Path
    #

    candidate = Path(source)

    if candidate.exists():

        return self.file_checksum(

            candidate,

            algorithm=algorithm,

        )

    #
    # String
    #

    return self.hash_string(

        str(source),

        algorithm=algorithm,

    )

# ------------------------------------------------------------

def compare_checksums(
    self,
    left: str,
    right: str,
) -> bool:
    """
    Constant-time checksum comparison.
    """

    import hmac

    return hmac.compare_digest(

        left,

        right,

    )

# ------------------------------------------------------------

def generate_checksum_manifest(
    self,
    objects: Dict[
        str,
        Any,
    ],
    *,
    algorithm: Optional[
        ChecksumAlgorithm
    ] = None,
) -> Dict[str, str]:
    """
    Generate checksums for an object
    dictionary.

    Example
    -------

    {

        "mapping": "...",

        "preset": "...",

        "runtime": "...",

    }
    """

    manifest = {}

    for name, obj in objects.items():

        manifest[name] = self.hash_object(

            obj,

            algorithm=algorithm,

        )

    return manifest

# ------------------------------------------------------------

def verify_checksum_manifest(
    self,
    objects: Dict[
        str,
        Any,
    ],
    manifest: Dict[
        str,
        str,
    ],
    *,
    algorithm: Optional[
        ChecksumAlgorithm
    ] = None,
) -> bool:
    """
    Verify an entire checksum manifest.
    """

    for name, expected in manifest.items():

        if name not in objects:

            return False

        actual = self.hash_object(

            objects[name],

            algorithm=algorithm,

        )

        if not self.compare_checksums(

            actual,

            expected,

        ):

            return False

    return True
# ============================================================
# Part 3.0B - File Hashing
# ============================================================

    def file_checksum(
        self,
        path: Union[str, Path],
        *,
        algorithm: Optional[
            ChecksumAlgorithm
        ] = None,
        chunk_size: int = DEFAULT_BUFFER_SIZE,
    ) -> str:
        """
        Compute the checksum of a file.

        The file is streamed in chunks, allowing
        efficient hashing of very large files.

        Parameters
        ----------
        path
            File to hash.

        algorithm
            Hash algorithm to use.

        chunk_size
            Read buffer size in bytes.

        Returns
        -------
        str
            Hex digest.
        """

        path = self.normalize_path(path)

        self.validate_file(path)

        hasher = self._create_hasher(
            algorithm
        )

        with path.open("rb") as fp:

            while True:

                block = fp.read(chunk_size)

                if not block:

                    break

                hasher.update(block)

        return hasher.hexdigest()

    # -----------------------------------------------------

    def md5(
        self,
        path: Union[str, Path],
    ) -> str:
        """
        Compute MD5 checksum.
        """

        return self.file_checksum(

            path,

            algorithm=ChecksumAlgorithm.MD5,

        )

    # -----------------------------------------------------

    def sha1(
        self,
        path: Union[str, Path],
    ) -> str:
        """
        Compute SHA1 checksum.
        """

        return self.file_checksum(

            path,

            algorithm=ChecksumAlgorithm.SHA1,

        )

    # -----------------------------------------------------

    def sha256(
        self,
        path: Union[str, Path],
    ) -> str:
        """
        Compute SHA256 checksum.
        """

        return self.file_checksum(

            path,

            algorithm=ChecksumAlgorithm.SHA256,

        )

    # -----------------------------------------------------

    def sha512(
        self,
        path: Union[str, Path],
    ) -> str:
        """
        Compute SHA512 checksum.
        """

        return self.file_checksum(

            path,

            algorithm=ChecksumAlgorithm.SHA512,

        )

    # -----------------------------------------------------

    def crc32(
        self,
        path: Union[str, Path],
        *,
        chunk_size: int = DEFAULT_BUFFER_SIZE,
    ) -> str:
        """
        Compute CRC32 checksum.

        Returns
        -------
        str
            Eight-character hexadecimal CRC32.
        """

        import zlib

        path = self.normalize_path(path)

        self.validate_file(path)

        checksum = 0

        with path.open("rb") as fp:

            while True:

                block = fp.read(chunk_size)

                if not block:

                    break

                checksum = zlib.crc32(
                    block,
                    checksum,
                )

        checksum &= 0xFFFFFFFF

        return f"{checksum:08x}"

    # -----------------------------------------------------

    def file_hashes(
        self,
        path: Union[str, Path],
    ) -> Dict[str, str]:
        """
        Compute every supported checksum for a file.

        Returns
        -------
        dict

            {
                "md5": "...",
                "sha1": "...",
                "sha256": "...",
                "sha512": "...",
                "crc32": "..."
            }
        """

        return {

            "md5": self.md5(path),

            "sha1": self.sha1(path),

            "sha256": self.sha256(path),

            "sha512": self.sha512(path),

            "crc32": self.crc32(path),

        }

    # -----------------------------------------------------

    def verify_file_checksum(
        self,
        path: Union[str, Path],
        expected: str,
        *,
        algorithm: Optional[
            ChecksumAlgorithm
        ] = None,
    ) -> bool:
        """
        Verify a file against an expected checksum.
        """

        actual = self.file_checksum(

            path,

            algorithm=algorithm,

        )

        return self.compare_checksums(

            actual,

            expected,

        )

    # -----------------------------------------------------

    def verify_file_hashes(
        self,
        path: Union[str, Path],
        hashes: Dict[str, str],
    ) -> Dict[str, bool]:
        """
        Verify multiple hashes.

        Example
        -------
        {
            "md5": True,
            "sha256": False
        }
        """

        results = {}

        for name, expected in hashes.items():

            key = name.lower()

            if key == "md5":

                actual = self.md5(path)

            elif key == "sha1":

                actual = self.sha1(path)

            elif key == "sha256":

                actual = self.sha256(path)

            elif key == "sha512":

                actual = self.sha512(path)

            elif key == "crc32":

                actual = self.crc32(path)

            else:

                continue

            results[key] = self.compare_checksums(

                actual,

                expected,

            )

        return results

    # -----------------------------------------------------

    def hash_stream(
        self,
        stream: BinaryIO,
        *,
        algorithm: Optional[
            ChecksumAlgorithm
        ] = None,
        chunk_size: int = DEFAULT_BUFFER_SIZE,
    ) -> str:
        """
        Compute the checksum of an already-open
        binary stream.

        The current stream position is restored
        before returning.
        """

        hasher = self._create_hasher(
            algorithm
        )

        position = stream.tell()

        stream.seek(0)

        while True:

            block = stream.read(chunk_size)

            if not block:

                break

            hasher.update(block)

        stream.seek(position)

        return hasher.hexdigest()

    # -----------------------------------------------------

    def identical_files(
        self,
        first: Union[str, Path],
        second: Union[str, Path],
        *,
        algorithm: ChecksumAlgorithm = (
            ChecksumAlgorithm.SHA256
        ),
    ) -> bool:
        """
        Compare two files by checksum.
        """

        return self.compare_checksums(

            self.file_checksum(

                first,

                algorithm=algorithm,

            ),

            self.file_checksum(

                second,

                algorithm=algorithm,

            ),

        )
# ============================================================
# Part 3.0C - Directory Hashing & Manifest Generation
# ============================================================

    def directory_checksum(
        self,
        directory: Union[str, Path],
        *,
        algorithm: Optional[
            ChecksumAlgorithm
        ] = None,
        recursive: bool = True,
        include_hidden: bool = False,
    ) -> str:
        """
        Compute a deterministic checksum for an entire
        directory.

        The checksum is based on:

            - relative file paths
            - file contents

        File ordering is normalized so the result is
        platform-independent.
        """

        directory = self.normalize_path(directory)

        self.validate_directory(directory)

        hasher = self._create_hasher(
            algorithm
        )

        manifest = self.directory_manifest(

            directory,

            algorithm=algorithm,

            recursive=recursive,

            include_hidden=include_hidden,

        )

        #
        # Stable ordering
        #

        for relative_path in sorted(manifest.keys()):

            hasher.update(
                relative_path.encode("utf-8")
            )

            hasher.update(
                manifest[relative_path].encode("utf-8")
            )

        return hasher.hexdigest()

    # -----------------------------------------------------

    def directory_manifest(
        self,
        directory: Union[str, Path],
        *,
        algorithm: Optional[
            ChecksumAlgorithm
        ] = None,
        recursive: bool = True,
        include_hidden: bool = False,
    ) -> Dict[str, str]:
        """
        Generate a checksum manifest for every file.

        Returns
        -------
        {
            "textures/head.png": "...",
            "mapping.json": "...",
            ...
        }
        """

        directory = self.normalize_path(
            directory
        )

        self.validate_directory(
            directory
        )

        manifest = {}

        if recursive:

            iterator = directory.rglob("*")

        else:

            iterator = directory.glob("*")

        for item in iterator:

            if not item.is_file():

                continue

            relative = item.relative_to(
                directory
            )

            if (

                not include_hidden

                and any(

                    part.startswith(".")

                    for part in relative.parts

                )

            ):

                continue

            manifest[str(relative)] = (

                self.file_checksum(

                    item,

                    algorithm=algorithm,

                )

            )

        return manifest

    # -----------------------------------------------------

    def save_manifest(
        self,
        directory: Union[str, Path],
        output: Union[str, Path],
        *,
        algorithm: Optional[
            ChecksumAlgorithm
        ] = None,
        recursive: bool = True,
    ) -> IOResult:
        """
        Save a directory checksum manifest
        as JSON.
        """

        manifest = self.directory_manifest(

            directory,

            algorithm=algorithm,

            recursive=recursive,

        )

        data = {

            "directory": str(

                self.normalize_path(directory)

            ),

            "algorithm": (

                algorithm.value

                if algorithm

                else self.config.checksum_algorithm.value

            ),

            "created": datetime.now().isoformat(),

            "checksum": self.directory_checksum(

                directory,

                algorithm=algorithm,

                recursive=recursive,

            ),

            "files": manifest,

        }

        return self.save_json(

            output,

            data,

        )

    # -----------------------------------------------------

    def load_manifest(
        self,
        path: Union[str, Path],
    ) -> Dict[str, Any]:
        """
        Load a checksum manifest.
        """

        return self.load_json(path)

    # -----------------------------------------------------

    def verify_manifest(
        self,
        directory: Union[str, Path],
        manifest: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Verify a directory against a
        checksum manifest.
        """

        directory = self.normalize_path(
            directory
        )

        current = self.directory_manifest(

            directory,

            algorithm=ChecksumAlgorithm(

                manifest["algorithm"]

            ),

        )

        expected = manifest["files"]

        added = []
        removed = []
        modified = []
        verified = []

        #
        # Missing / Modified
        #

        for filename, checksum in expected.items():

            if filename not in current:

                removed.append(filename)

                continue

            if current[filename] != checksum:

                modified.append(filename)

            else:

                verified.append(filename)

        #
        # Added
        #

        for filename in current:

            if filename not in expected:

                added.append(filename)

        return {

            "success": (

                not added

                and not removed

                and not modified

            ),

            "verified": sorted(

                verified

            ),

            "added": sorted(

                added

            ),

            "removed": sorted(

                removed

            ),

            "modified": sorted(

                modified

            ),

        }

    # -----------------------------------------------------

    def compare_directories(
        self,
        left: Union[str, Path],
        right: Union[str, Path],
        *,
        algorithm: Optional[
            ChecksumAlgorithm
        ] = None,
    ) -> Dict[str, Any]:
        """
        Compare two directories.
        """

        left_manifest = self.directory_manifest(

            left,

            algorithm=algorithm,

        )

        right_manifest = self.directory_manifest(

            right,

            algorithm=algorithm,

        )

        added = []
        removed = []
        modified = []
        identical = []

        all_files = sorted(

            set(left_manifest)

            |

            set(right_manifest)

        )

        for filename in all_files:

            in_left = filename in left_manifest
            in_right = filename in right_manifest

            if not in_left:

                added.append(filename)

                continue

            if not in_right:

                removed.append(filename)

                continue

            if (

                left_manifest[filename]

                ==

                right_manifest[filename]

            ):

                identical.append(filename)

            else:

                modified.append(filename)

        return {

            "identical": identical,

            "added": added,

            "removed": removed,

            "modified": modified,

            "same": (

                not added

                and not removed

                and not modified

            ),

        }

    # -----------------------------------------------------

    def project_fingerprint(
        self,
        project_directory: Union[str, Path],
    ) -> str:
        """
        Produce a single fingerprint
        representing the entire project.
        """

        return self.directory_checksum(

            project_directory,

            algorithm=ChecksumAlgorithm.SHA256,

        )

    # -----------------------------------------------------

    def manifest_statistics(
        self,
        manifest: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Return summary information for a
        checksum manifest.
        """

        files = manifest.get(

            "files",

            {},

        )

        return {

            "algorithm": manifest.get(

                "algorithm"

            ),

            "directory": manifest.get(

                "directory"

            ),

            "created": manifest.get(

                "created"

            ),

            "file_count": len(files),

            "directory_checksum": manifest.get(

                "checksum"

            ),

        }
  # ============================================================
# Part 3.0D - Verification & Integrity Checking
# ============================================================

    def verify_file_integrity(
        self,
        path: Union[str, Path],
        expected_checksum: str,
        *,
        algorithm: Optional[ChecksumAlgorithm] = None,
    ) -> VerificationResult:
        """
        Verify a file against an expected checksum.

        Returns
        -------
        VerificationResult
        """

        path = self.normalize_path(path)

        self.validate_file(path)

        actual = self.file_checksum(
            path,
            algorithm=algorithm,
        )

        success = self.compare_checksums(
            actual,
            expected_checksum,
        )

        return VerificationResult(
            success=success,
            target=str(path),
            expected=expected_checksum,
            actual=actual,
            algorithm=(
                algorithm
                or self.config.checksum_algorithm
            ),
            message=(
                "Checksum verified."
                if success
                else "Checksum mismatch."
            ),
        )

    # -----------------------------------------------------

    def verify_directory_integrity(
        self,
        directory: Union[str, Path],
        manifest_path: Union[str, Path],
    ) -> VerificationResult:
        """
        Verify an entire directory using a
        previously generated manifest.
        """

        manifest = self.load_manifest(
            manifest_path
        )

        report = self.verify_manifest(
            directory,
            manifest,
        )

        success = report["success"]

        return VerificationResult(
            success=success,
            target=str(directory),
            expected=manifest.get(
                "checksum",
                ""
            ),
            actual=self.directory_checksum(
                directory,
                algorithm=ChecksumAlgorithm(
                    manifest["algorithm"]
                ),
            ),
            algorithm=ChecksumAlgorithm(
                manifest["algorithm"]
            ),
            message=(
                "Directory verified."
                if success
                else "Directory integrity failed."
            ),
            details=report,
        )

    # -----------------------------------------------------

    def verify_project_integrity(
        self,
        project_directory: Union[str, Path],
        manifest_file: Union[str, Path],
    ) -> VerificationResult:
        """
        Verify an entire ARKit Mapper project.
        """

        return self.verify_directory_integrity(
            project_directory,
            manifest_file,
        )

    # -----------------------------------------------------

    def verify_object(
        self,
        obj: Any,
        checksum: str,
        *,
        algorithm: Optional[
            ChecksumAlgorithm
        ] = None,
    ) -> VerificationResult:
        """
        Verify an arbitrary Python object.
        """

        actual = self.hash_object(
            obj,
            algorithm=algorithm,
        )

        success = self.compare_checksums(
            actual,
            checksum,
        )

        return VerificationResult(
            success=success,
            target=type(obj).__name__,
            expected=checksum,
            actual=actual,
            algorithm=(
                algorithm
                or self.config.checksum_algorithm
            ),
            message=(
                "Object verified."
                if success
                else "Object checksum mismatch."
            ),
        )

    # -----------------------------------------------------

    def verify_binary(
        self,
        data: bytes,
        checksum: str,
        *,
        algorithm: Optional[
            ChecksumAlgorithm
        ] = None,
    ) -> VerificationResult:
        """
        Verify raw binary data.
        """

        actual = self.hash_bytes(
            data,
            algorithm=algorithm,
        )

        success = self.compare_checksums(
            actual,
            checksum,
        )

        return VerificationResult(
            success=success,
            target="BinaryData",
            expected=checksum,
            actual=actual,
            algorithm=(
                algorithm
                or self.config.checksum_algorithm
            ),
            message=(
                "Binary verified."
                if success
                else "Binary checksum mismatch."
            ),
        )

    # -----------------------------------------------------

    def verify_string(
        self,
        text: str,
        checksum: str,
        *,
        algorithm: Optional[
            ChecksumAlgorithm
        ] = None,
    ) -> VerificationResult:
        """
        Verify a text string.
        """

        actual = self.hash_string(
            text,
            algorithm=algorithm,
        )

        success = self.compare_checksums(
            actual,
            checksum,
        )

        return VerificationResult(
            success=success,
            target="String",
            expected=checksum,
            actual=actual,
            algorithm=(
                algorithm
                or self.config.checksum_algorithm
            ),
            message=(
                "String verified."
                if success
                else "String checksum mismatch."
            ),
        )

    # -----------------------------------------------------

    def verify_manifest_file(
        self,
        manifest_path: Union[str, Path],
    ) -> bool:
        """
        Verify that a manifest itself is valid.
        """

        manifest = self.load_manifest(
            manifest_path
        )

        required = (
            "directory",
            "algorithm",
            "created",
            "checksum",
            "files",
        )

        return all(
            key in manifest
            for key in required
        )

    # -----------------------------------------------------

    def integrity_report(
        self,
        verification: VerificationResult,
    ) -> Dict[str, Any]:
        """
        Convert VerificationResult into a
        serializable report.
        """

        return {

            "success": verification.success,

            "target": verification.target,

            "expected": verification.expected,

            "actual": verification.actual,

            "algorithm": verification.algorithm.value,

            "message": verification.message,

            "details": verification.details,

            "timestamp": datetime.now().isoformat(),

        }

    # -----------------------------------------------------

    def save_integrity_report(
        self,
        verification: VerificationResult,
        path: Union[str, Path],
    ) -> IOResult:
        """
        Save an integrity report as JSON.
        """

        report = self.integrity_report(
            verification
        )

        return self.save_json(
            path,
            report,
        )

    # -----------------------------------------------------

    def load_integrity_report(
        self,
        path: Union[str, Path],
    ) -> Dict[str, Any]:
        """
        Load a previously saved integrity report.
        """

        return self.load_json(path)

    # -----------------------------------------------------

    def compare_verification_results(
        self,
        first: VerificationResult,
        second: VerificationResult,
    ) -> Dict[str, Any]:
        """
        Compare two verification results.
        """

        return {

            "same_success":
                first.success == second.success,

            "same_algorithm":
                first.algorithm == second.algorithm,

            "same_checksum":
                first.actual == second.actual,

            "same_target":
                first.target == second.target,

            "same_expected":
                first.expected == second.expected,

        }
# ============================================================
# Part 3.0E - Checksum Utilities & Convenience APIs
# ============================================================

    def checksum_info(
        self,
        source: Union[str, Path, bytes, bytearray, Any],
        *,
        algorithm: Optional[ChecksumAlgorithm] = None,
    ) -> Dict[str, Any]:
        """
        Return detailed checksum information.

        Works with:
            - files
            - directories
            - bytes
            - strings
            - python objects
        """

        if algorithm is None:
            algorithm = self.config.checksum_algorithm

        result = {

            "algorithm": algorithm.value,

            "checksum": None,

            "type": None,

            "size": None,

        }

        #
        # File
        #

        if isinstance(source, (str, Path)):

            candidate = Path(source)

            if candidate.exists():

                if candidate.is_file():

                    result["type"] = "file"

                    result["size"] = candidate.stat().st_size

                    result["checksum"] = self.file_checksum(
                        candidate,
                        algorithm=algorithm,
                    )

                    return result

                if candidate.is_dir():

                    result["type"] = "directory"

                    result["checksum"] = self.directory_checksum(
                        candidate,
                        algorithm=algorithm,
                    )

                    return result

        #
        # Bytes
        #

        if isinstance(source, (bytes, bytearray)):

            result["type"] = "bytes"

            result["size"] = len(source)

            result["checksum"] = self.hash_bytes(
                bytes(source),
                algorithm=algorithm,
            )

            return result

        #
        # String
        #

        if isinstance(source, str):

            result["type"] = "string"

            result["size"] = len(source)

            result["checksum"] = self.hash_string(
                source,
                algorithm=algorithm,
            )

            return result

        #
        # Generic object
        #

        result["type"] = type(source).__name__

        result["checksum"] = self.hash_object(
            source,
            algorithm=algorithm,
        )

        return result

    # -----------------------------------------------------

    def checksum_report(
        self,
        source: Union[str, Path],
    ) -> Dict[str, str]:
        """
        Generate every supported checksum.
        """

        return {

            "md5": self.file_checksum(
                source,
                algorithm=ChecksumAlgorithm.MD5,
            ),

            "sha1": self.file_checksum(
                source,
                algorithm=ChecksumAlgorithm.SHA1,
            ),

            "sha256": self.file_checksum(
                source,
                algorithm=ChecksumAlgorithm.SHA256,
            ),

            "sha512": self.file_checksum(
                source,
                algorithm=ChecksumAlgorithm.SHA512,
            ),

            "crc32": self.crc32(source),

        }

    # -----------------------------------------------------

    def print_checksum_report(
        self,
        source: Union[str, Path],
    ) -> None:
        """
        Pretty-print checksum information.
        """

        report = self.checksum_report(source)

        print("=" * 60)
        print("Checksum Report")
        print("=" * 60)

        for name, value in report.items():

            print(

                f"{name.upper():<10} {value}"

            )

    # -----------------------------------------------------

    def compare_objects(
        self,
        left: Any,
        right: Any,
        *,
        algorithm: Optional[
            ChecksumAlgorithm
        ] = None,
    ) -> bool:
        """
        Compare two arbitrary Python objects
        using checksums.
        """

        return self.compare_checksums(

            self.hash_object(
                left,
                algorithm=algorithm,
            ),

            self.hash_object(
                right,
                algorithm=algorithm,
            ),

        )

    # -----------------------------------------------------

    def fingerprint(
        self,
        source: Any,
    ) -> str:
        """
        Alias for checksum().

        Used throughout ARKit Mapper
        for quick object identification.
        """

        return self.checksum(source)

    # -----------------------------------------------------

    def unique_identifier(
        self,
        obj: Any,
    ) -> str:
        """
        Create a stable object identifier.

        Uses SHA256 regardless of the
        configured checksum algorithm.
        """

        return self.hash_object(

            obj,

            algorithm=ChecksumAlgorithm.SHA256,

        )

    # -----------------------------------------------------

    def checksum_equals(
        self,
        source: Any,
        checksum: str,
        *,
        algorithm: Optional[
            ChecksumAlgorithm
        ] = None,
    ) -> bool:
        """
        Convenience checksum comparison.
        """

        return self.compare_checksums(

            self.checksum(

                source,

                algorithm=algorithm,

            ),

            checksum,

        )

    # -----------------------------------------------------

    def cache_key(
        self,
        *objects: Any,
    ) -> str:
        """
        Generate a deterministic cache key.

        Frequently used by the runtime,
        statistics system, and converter.
        """

        hasher = self._create_hasher(

            ChecksumAlgorithm.SHA256

        )

        for obj in objects:

            hasher.update(

                self.hash_object(obj).encode(

                    "utf-8"

                )

            )

        return hasher.hexdigest()

    # -----------------------------------------------------

    def manifest_hash(
        self,
        manifest: Dict[str, Any],
    ) -> str:
        """
        Compute a checksum for an
        already-loaded manifest.
        """

        return self.hash_object(

            manifest,

            algorithm=ChecksumAlgorithm.SHA256,

        )

    # -----------------------------------------------------

    def object_signature(
        self,
        obj: Any,
    ) -> Dict[str, Any]:
        """
        Generate a reusable object signature.

        Useful for debugging,
        caching,
        dependency tracking.
        """

        return {

            "type": type(obj).__name__,

            "checksum": self.hash_object(obj),

            "sha256": self.hash_object(

                obj,

                algorithm=ChecksumAlgorithm.SHA256,

            ),

            "id": id(obj),

        }

    # -----------------------------------------------------

    def checksum_summary(
        self,
        source: Union[str, Path],
    ) -> str:
        """
        One-line checksum summary.

        Example

            SHA256:
            9d8a61...
        """

        checksum = self.file_checksum(

            source,

            algorithm=ChecksumAlgorithm.SHA256,

        )

        return (

            f"SHA256: "

            f"{checksum}"

        )

    # -----------------------------------------------------

    def verify_or_raise(
        self,
        source: Union[str, Path],
        checksum: str,
        *,
        algorithm: Optional[
            ChecksumAlgorithm
        ] = None,
    ) -> None:
        """
        Verify checksum.

        Raises
        ------
        IntegrityError
            If verification fails.
        """

        if not self.checksum_equals(

            source,

            checksum,

            algorithm=algorithm,

        ):

            raise IntegrityError(

                "Checksum verification failed."

            )

    # -----------------------------------------------------

    def clear_checksum_cache(
        self,
    ) -> None:
        """
        Clear internal checksum cache.

        Future versions may implement
        cached hashing for very large
        projects.
        """

        if hasattr(self, "_checksum_cache"):

            self._checksum_cache.clear()

    # -----------------------------------------------------

    @property
    def checksum_algorithm(
        self,
    ) -> ChecksumAlgorithm:
        """
        Current default checksum algorithm.
        """

        return self.config.checksum_algorithm

    @checksum_algorithm.setter
    def checksum_algorithm(
        self,
        algorithm: ChecksumAlgorithm,
    ) -> None:
        """
        Change the default checksum algorithm.
        """

        if algorithm not in self._HASH_ALGORITHMS:

            raise FileIOError(

                f"Unsupported checksum algorithm: "

                f"{algorithm}"

            )

        self.config.checksum_algorithm = algorithm
# ============================================================
# Part 3.1A - Binary Foundation
# ============================================================

    def serialize(
        self,
        obj: Any,
        *,
        protocol: Optional[int] = None,
    ) -> bytes:
        """
        Serialize a Python object into bytes.

        Parameters
        ----------
        obj
            Object to serialize.

        protocol
            Pickle protocol version.
            Defaults to the configured protocol.

        Returns
        -------
        bytes
        """

        if protocol is None:

            protocol = getattr(
                self.config,
                "pickle_protocol",
                pickle.HIGHEST_PROTOCOL,
            )

        try:

            return pickle.dumps(
                obj,
                protocol=protocol,
            )

        except Exception as exc:

            raise SerializationError(

                f"Failed to serialize object: {exc}"

            ) from exc

    # -----------------------------------------------------

    def deserialize(
        self,
        data: bytes,
    ) -> Any:
        """
        Deserialize binary data.

        Parameters
        ----------
        data
            Pickled bytes.

        Returns
        -------
        Any
        """

        try:

            return pickle.loads(data)

        except Exception as exc:

            raise SerializationError(

                f"Failed to deserialize object: {exc}"

            ) from exc

    # -----------------------------------------------------

    def save_binary(
        self,
        path: Union[str, Path],
        obj: Any,
        *,
        protocol: Optional[int] = None,
        create_backup: bool = False,
    ) -> IOResult:
        """
        Save an object as a binary file.
        """

        path = self.normalize_path(path)

        self.ensure_parent_directory(path)

        if create_backup and path.exists():

            self.create_backup(path)

        binary = self.serialize(
            obj,
            protocol=protocol,
        )

        try:

            with path.open("wb") as fp:

                fp.write(binary)

        except Exception as exc:

            raise FileIOError(

                f"Unable to save binary file '{path}': {exc}"

            ) from exc

        return IOResult(

            status=IOStatus.SUCCESS,

            success=True,

            path=path,

            format=FileFormat.BINARY,

            size=len(binary),

        )

    # -----------------------------------------------------

    def load_binary(
        self,
        path: Union[str, Path],
        *,
        validate: bool = True,
    ) -> Any:
        """
        Load a binary file.
        """

        path = self.normalize_path(path)

        self.validate_file(path)

        try:

            with path.open("rb") as fp:

                binary = fp.read()

        except Exception as exc:

            raise FileIOError(

                f"Unable to read binary file '{path}': {exc}"

            ) from exc

        if validate and not binary:

            raise SerializationError(

                "Binary file is empty."

            )

        return self.deserialize(binary)

    # -----------------------------------------------------

    def binary_size(
        self,
        obj: Any,
        *,
        protocol: Optional[int] = None,
    ) -> int:
        """
        Return the serialized size of an object
        without writing it to disk.
        """

        return len(

            self.serialize(

                obj,

                protocol=protocol,

            )

        )

    # -----------------------------------------------------

    def is_binary_file(
        self,
        path: Union[str, Path],
    ) -> bool:
        """
        Check whether a file appears to contain
        valid serialized binary data.
        """

        path = self.normalize_path(path)

        if not path.exists():

            return False

        try:

            self.load_binary(
                path,
                validate=False,
            )

            return True

        except Exception:

            return False

    # -----------------------------------------------------

    def binary_metadata(
        self,
        path: Union[str, Path],
    ) -> Dict[str, Any]:
        """
        Return metadata describing a binary file.
        """

        path = self.normalize_path(path)

        self.validate_file(path)

        return {

            "path": str(path),

            "size": path.stat().st_size,

            "modified": datetime.fromtimestamp(

                path.stat().st_mtime

            ).isoformat(),

            "checksum": self.file_checksum(

                path,

                algorithm=ChecksumAlgorithm.SHA256,

            ),

            "format": FileFormat.BINARY.value,

        }

    # -----------------------------------------------------

    def copy_binary(
        self,
        source: Union[str, Path],
        destination: Union[str, Path],
    ) -> IOResult:
        """
        Copy a binary file.
        """

        source = self.normalize_path(source)

        destination = self.normalize_path(destination)

        self.validate_file(source)

        self.ensure_parent_directory(destination)

        shutil.copy2(
            source,
            destination,
        )

        return IOResult(

            status=IOStatus.SUCCESS,

            success=True,

            path=destination,

            format=FileFormat.BINARY,

        )

    # -----------------------------------------------------

    def clone_binary_object(
        self,
        obj: Any,
    ) -> Any:
        """
        Create a deep copy of an object using
        binary serialization.
        """

        return self.deserialize(

            self.serialize(obj)

        )

    # -----------------------------------------------------

    def binary_roundtrip(
        self,
        obj: Any,
    ) -> bool:
        """
        Verify that an object survives a
        serialize/deserialize roundtrip.
        """

        restored = self.deserialize(

            self.serialize(obj)

        )

        return restored == obj

    # -----------------------------------------------------

    def binary_protocol(
        self,
    ) -> int:
        """
        Return the currently configured pickle
        protocol.
        """

        return getattr(

            self.config,

            "pickle_protocol",

            pickle.HIGHEST_PROTOCOL,

        )

    # -----------------------------------------------------

    def set_binary_protocol(
        self,
        protocol: int,
    ) -> None:
        """
        Set the default pickle protocol.
        """

        if not isinstance(protocol, int):

            raise ValueError(

                "Protocol must be an integer."

            )

        if protocol < 0:

            raise ValueError(

                "Protocol must be >= 0."

            )

        self.config.pickle_protocol = protocol

# ============================================================
# Part 3.1B - Bytes & Base64 APIs
# ============================================================

    def to_bytes(
        self,
        obj: Any,
        *,
        protocol: Optional[int] = None,
    ) -> bytes:
        """
        Convert a Python object to raw bytes.

        Alias of serialize().
        """

        return self.serialize(
            obj,
            protocol=protocol,
        )

    # -----------------------------------------------------

    def from_bytes(
        self,
        data: bytes,
    ) -> Any:
        """
        Deserialize an object from bytes.

        Alias of deserialize().
        """

        return self.deserialize(data)

    # -----------------------------------------------------

    def bytes_to_file(
        self,
        data: bytes,
        path: Union[str, Path],
    ) -> IOResult:
        """
        Write raw bytes to disk.
        """

        path = self.normalize_path(path)

        self.ensure_parent_directory(path)

        try:

            with path.open("wb") as fp:

                fp.write(data)

        except Exception as exc:

            raise FileIOError(

                f"Unable to write bytes to '{path}': {exc}"

            ) from exc

        return IOResult(

            status=IOStatus.SUCCESS,

            success=True,

            path=path,

            format=FileFormat.BINARY,

            size=len(data),

        )

    # -----------------------------------------------------

    def file_to_bytes(
        self,
        path: Union[str, Path],
    ) -> bytes:
        """
        Read an entire file into memory.
        """

        path = self.normalize_path(path)

        self.validate_file(path)

        try:

            with path.open("rb") as fp:

                return fp.read()

        except Exception as exc:

            raise FileIOError(

                f"Unable to read '{path}': {exc}"

            ) from exc

    # -----------------------------------------------------

    def object_to_base64(
        self,
        obj: Any,
        *,
        protocol: Optional[int] = None,
    ) -> str:
        """
        Serialize an object and encode it
        as a Base64 string.
        """

        binary = self.serialize(
            obj,
            protocol=protocol,
        )

        return base64.b64encode(
            binary
        ).decode("ascii")

    # -----------------------------------------------------

    def object_from_base64(
        self,
        encoded: str,
    ) -> Any:
        """
        Decode a Base64 string into a
        Python object.
        """

        try:

            binary = base64.b64decode(
                encoded.encode("ascii")
            )

        except Exception as exc:

            raise SerializationError(

                f"Invalid Base64 data: {exc}"

            ) from exc

        return self.deserialize(binary)

    # -----------------------------------------------------

    def bytes_to_base64(
        self,
        data: bytes,
    ) -> str:
        """
        Encode bytes as Base64.
        """

        return base64.b64encode(
            data
        ).decode("ascii")

    # -----------------------------------------------------

    def base64_to_bytes(
        self,
        encoded: str,
    ) -> bytes:
        """
        Decode Base64 into bytes.
        """

        try:

            return base64.b64decode(
                encoded.encode("ascii")
            )

        except Exception as exc:

            raise SerializationError(

                f"Invalid Base64 data: {exc}"

            ) from exc

    # -----------------------------------------------------

    def file_to_base64(
        self,
        path: Union[str, Path],
    ) -> str:
        """
        Encode an entire file as Base64.
        """

        data = self.file_to_bytes(path)

        return self.bytes_to_base64(data)

    # -----------------------------------------------------

    def base64_to_file(
        self,
        encoded: str,
        destination: Union[str, Path],
    ) -> IOResult:
        """
        Decode Base64 directly to a file.
        """

        data = self.base64_to_bytes(
            encoded
        )

        return self.bytes_to_file(
            data,
            destination,
        )

    # -----------------------------------------------------

    def text_to_bytes(
        self,
        text: str,
        *,
        encoding: Optional[str] = None,
    ) -> bytes:
        """
        Encode text into bytes.
        """

        if encoding is None:

            encoding = self.config.encoding

        return text.encode(encoding)

    # -----------------------------------------------------

    def bytes_to_text(
        self,
        data: bytes,
        *,
        encoding: Optional[str] = None,
    ) -> str:
        """
        Decode bytes into text.
        """

        if encoding is None:

            encoding = self.config.encoding

        return data.decode(encoding)

    # -----------------------------------------------------

    def is_base64(
        self,
        value: str,
    ) -> bool:
        """
        Check whether a string appears to
        be valid Base64.
        """

        try:

            decoded = base64.b64decode(
                value,
                validate=True,
            )

            base64.b64encode(decoded)

            return True

        except Exception:

            return False

    # -----------------------------------------------------

    def base64_size(
        self,
        encoded: str,
    ) -> int:
        """
        Return the decoded size (bytes)
        of a Base64 string.
        """

        return len(

            self.base64_to_bytes(
                encoded
            )

        )

    # -----------------------------------------------------

    def object_size(
        self,
        obj: Any,
    ) -> Dict[str, int]:
        """
        Return serialized object size
        in multiple representations.
        """

        binary = self.serialize(obj)

        encoded = self.bytes_to_base64(binary)

        return {

            "binary": len(binary),

            "base64": len(encoded),

        }

    # -----------------------------------------------------

    def convert_bytes_encoding(
        self,
        data: bytes,
        *,
        source_encoding: str = "utf-8",
        target_encoding: str = "utf-8",
    ) -> bytes:
        """
        Convert bytes between text encodings.
        """

        text = data.decode(
            source_encoding
        )

        return text.encode(
            target_encoding
        )
```
# ============================================================
# Part 3.1C - Advanced Object Serialization
# ============================================================

    def serialize_object(
        self,
        obj: Any,
        *,
        protocol: Optional[int] = None,
        include_metadata: bool = True,
    ) -> bytes:
        """
        Serialize any Python object together with
        optional metadata.
        """

        payload = {
            "object": obj,
        }

        if include_metadata:

            payload["metadata"] = {

                "class": obj.__class__.__name__,

                "module": obj.__class__.__module__,

                "serialized_at": datetime.now().isoformat(),

                "io_version": IO_VERSION,

                "python_version": sys.version,

            }

        return self.serialize(
            payload,
            protocol=protocol,
        )

    # -----------------------------------------------------

    def deserialize_object(
        self,
        data: bytes,
    ) -> Any:
        """
        Deserialize an object created by
        serialize_object().
        """

        payload = self.deserialize(data)

        if isinstance(payload, dict):

            return payload.get("object")

        return payload

    # -----------------------------------------------------

    def serialize_dataclass(
        self,
        obj: Any,
        *,
        protocol: Optional[int] = None,
    ) -> bytes:
        """
        Serialize a dataclass instance.
        """

        if not dataclasses.is_dataclass(obj):

            raise SerializationError(
                "Object is not a dataclass."
            )

        return self.serialize_object(
            dataclasses.asdict(obj),
            protocol=protocol,
        )

    # -----------------------------------------------------

    def deserialize_dataclass(
        self,
        cls: Type[T],
        data: bytes,
    ) -> T:
        """
        Deserialize bytes into a dataclass.
        """

        values = self.deserialize_object(data)

        return cls(**values)

    # -----------------------------------------------------

    def serialize_enum(
        self,
        value: Enum,
    ) -> bytes:
        """
        Serialize an Enum.
        """

        payload = {

            "enum": value.__class__.__name__,

            "module": value.__class__.__module__,

            "name": value.name,

            "value": value.value,

        }

        return self.serialize(payload)

    # -----------------------------------------------------

    def deserialize_enum(
        self,
        enum_type: Type[Enum],
        data: bytes,
    ) -> Enum:
        """
        Deserialize an Enum.
        """

        payload = self.deserialize(data)

        return enum_type[payload["name"]]

    # -----------------------------------------------------

    def serialize_dictionary(
        self,
        dictionary: Dict[str, Any],
    ) -> bytes:
        """
        Serialize a dictionary.
        """

        return self.serialize(dictionary)

    # -----------------------------------------------------

    def deserialize_dictionary(
        self,
        data: bytes,
    ) -> Dict[str, Any]:
        """
        Deserialize a dictionary.
        """

        obj = self.deserialize(data)

        if not isinstance(obj, dict):

            raise SerializationError(
                "Serialized object is not a dictionary."
            )

        return obj

    # -----------------------------------------------------

    def serialize_list(
        self,
        values: List[Any],
    ) -> bytes:
        """
        Serialize a list.
        """

        return self.serialize(values)

    # -----------------------------------------------------

    def deserialize_list(
        self,
        data: bytes,
    ) -> List[Any]:
        """
        Deserialize a list.
        """

        obj = self.deserialize(data)

        if not isinstance(obj, list):

            raise SerializationError(
                "Serialized object is not a list."
            )

        return obj

    # -----------------------------------------------------

    def serialize_numpy(
        self,
        array: Any,
    ) -> bytes:
        """
        Serialize a NumPy array.

        Requires NumPy.
        """

        try:

            import numpy as np

        except ImportError:

            raise SerializationError(
                "NumPy is not installed."
            )

        if not isinstance(array, np.ndarray):

            raise SerializationError(
                "Expected numpy.ndarray."
            )

        payload = {

            "dtype": str(array.dtype),

            "shape": array.shape,

            "data": array.tobytes(),

        }

        return self.serialize(payload)

    # -----------------------------------------------------

    def deserialize_numpy(
        self,
        data: bytes,
    ):
        """
        Deserialize a NumPy array.
        """

        try:

            import numpy as np

        except ImportError:

            raise SerializationError(
                "NumPy is not installed."
            )

        payload = self.deserialize(data)

        return np.frombuffer(
            payload["data"],
            dtype=payload["dtype"],
        ).reshape(payload["shape"])

    # -----------------------------------------------------

    def register_serializer(
        self,
        cls: Type,
        serializer: Callable,
        deserializer: Callable,
    ) -> None:
        """
        Register a custom serializer.
        """

        if not hasattr(self, "_serializers"):

            self._serializers = {}

        self._serializers[cls] = {

            "serialize": serializer,

            "deserialize": deserializer,

        }

    # -----------------------------------------------------

    def unregister_serializer(
        self,
        cls: Type,
    ) -> None:
        """
        Remove a custom serializer.
        """

        if hasattr(self, "_serializers"):

            self._serializers.pop(
                cls,
                None,
            )

    # -----------------------------------------------------

    def has_serializer(
        self,
        cls: Type,
    ) -> bool:
        """
        Check if a custom serializer exists.
        """

        return (

            hasattr(self, "_serializers")

            and

            cls in self._serializers

        )

    # -----------------------------------------------------

    def serializer_info(
        self,
    ) -> Dict[str, Any]:
        """
        Return information about registered
        serializers.
        """

        if not hasattr(self, "_serializers"):

            return {

                "count": 0,

                "classes": [],

            }

        return {

            "count": len(self._serializers),

            "classes": [

                cls.__name__

                for cls in self._serializers

            ],

        }

    # -----------------------------------------------------

    def clone_object(
        self,
        obj: Any,
    ) -> Any:
        """
        Deep-copy an object through binary
        serialization.
        """

        return self.deserialize(

            self.serialize(obj)

        )
# ============================================================
# Part 3.1D - Binary Streams
# ============================================================

    def serialize_to_stream(
        self,
        obj: Any,
        stream: BinaryIO,
        *,
        protocol: Optional[int] = None,
    ) -> int:
        """
        Serialize an object directly to an open binary stream.

        Parameters
        ----------
        obj
            Object to serialize.

        stream
            Writable binary stream.

        protocol
            Pickle protocol.

        Returns
        -------
        int
            Number of bytes written.
        """

        data = self.serialize(
            obj,
            protocol=protocol,
        )

        stream.write(data)
        stream.flush()

        return len(data)

    # -----------------------------------------------------

    def deserialize_from_stream(
        self,
        stream: BinaryIO,
    ) -> Any:
        """
        Deserialize an object from an open
        binary stream.
        """

        stream.seek(0)

        data = stream.read()

        return self.deserialize(data)

    # -----------------------------------------------------

    def object_to_bytes_io(
        self,
        obj: Any,
        *,
        protocol: Optional[int] = None,
    ) -> io.BytesIO:
        """
        Serialize an object into a BytesIO buffer.
        """

        buffer = io.BytesIO()

        self.serialize_to_stream(
            obj,
            buffer,
            protocol=protocol,
        )

        buffer.seek(0)

        return buffer

    # -----------------------------------------------------

    def object_from_bytes_io(
        self,
        buffer: io.BytesIO,
    ) -> Any:
        """
        Deserialize an object from a BytesIO buffer.
        """

        buffer.seek(0)

        return self.deserialize(
            buffer.read()
        )

    # -----------------------------------------------------

    def save_stream(
        self,
        stream: BinaryIO,
        destination: Union[str, Path],
    ) -> IOResult:
        """
        Save an existing binary stream to disk.
        """

        destination = self.normalize_path(
            destination
        )

        self.ensure_parent_directory(
            destination
        )

        stream.seek(0)

        with destination.open("wb") as fp:

            shutil.copyfileobj(
                stream,
                fp,
            )

        return IOResult(

            status=IOStatus.SUCCESS,

            success=True,

            path=destination,

            format=FileFormat.BINARY,

            size=destination.stat().st_size,

        )

    # -----------------------------------------------------

    def load_stream(
        self,
        path: Union[str, Path],
    ) -> io.BytesIO:
        """
        Load a binary file into a BytesIO stream.
        """

        path = self.normalize_path(path)

        self.validate_file(path)

        with path.open("rb") as fp:

            data = fp.read()

        return io.BytesIO(data)

    # -----------------------------------------------------

    def stream_size(
        self,
        stream: BinaryIO,
    ) -> int:
        """
        Return the size of a binary stream
        without changing its current position.
        """

        position = stream.tell()

        stream.seek(0, io.SEEK_END)

        size = stream.tell()

        stream.seek(position)

        return size

    # -----------------------------------------------------

    def stream_checksum(
        self,
        stream: BinaryIO,
        *,
        algorithm: Optional[
            ChecksumAlgorithm
        ] = None,
    ) -> str:
        """
        Compute the checksum of a stream.

        Preserves the stream position.
        """

        position = stream.tell()

        stream.seek(0)

        hasher = self._create_hasher(
            algorithm
        )

        while True:

            block = stream.read(
                DEFAULT_BUFFER_SIZE
            )

            if not block:

                break

            hasher.update(block)

        stream.seek(position)

        return hasher.hexdigest()

    # -----------------------------------------------------

    def copy_stream(
        self,
        source: BinaryIO,
        destination: BinaryIO,
        *,
        chunk_size: int = DEFAULT_BUFFER_SIZE,
    ) -> int:
        """
        Copy one binary stream into another.

        Returns
        -------
        int
            Number of bytes copied.
        """

        source.seek(0)
        destination.seek(0)

        total = 0

        while True:

            chunk = source.read(chunk_size)

            if not chunk:

                break

            destination.write(chunk)

            total += len(chunk)

        destination.flush()

        return total

    # -----------------------------------------------------

    def stream_to_bytes(
        self,
        stream: BinaryIO,
    ) -> bytes:
        """
        Read an entire stream into bytes.
        """

        position = stream.tell()

        stream.seek(0)

        data = stream.read()

        stream.seek(position)

        return data

    # -----------------------------------------------------

    def bytes_to_stream(
        self,
        data: bytes,
    ) -> io.BytesIO:
        """
        Create a BytesIO stream from bytes.
        """

        return io.BytesIO(data)

    # -----------------------------------------------------

    def stream_to_base64(
        self,
        stream: BinaryIO,
    ) -> str:
        """
        Encode a stream as Base64.
        """

        data = self.stream_to_bytes(
            stream
        )

        return self.bytes_to_base64(data)

    # -----------------------------------------------------

    def base64_to_stream(
        self,
        encoded: str,
    ) -> io.BytesIO:
        """
        Decode Base64 into a BytesIO stream.
        """

        return io.BytesIO(

            self.base64_to_bytes(
                encoded
            )

        )

    # -----------------------------------------------------

    def duplicate_stream(
        self,
        stream: BinaryIO,
    ) -> io.BytesIO:
        """
        Create an in-memory duplicate of
        a binary stream.
        """

        return io.BytesIO(

            self.stream_to_bytes(
                stream
            )

        )

    # -----------------------------------------------------

    def compare_streams(
        self,
        first: BinaryIO,
        second: BinaryIO,
        *,
        algorithm: ChecksumAlgorithm = (
            ChecksumAlgorithm.SHA256
        ),
    ) -> bool:
        """
        Compare two streams using checksums.
        """

        return self.compare_checksums(

            self.stream_checksum(
                first,
                algorithm=algorithm,
            ),

            self.stream_checksum(
                second,
                algorithm=algorithm,
            ),

        )

    # -----------------------------------------------------

    def is_stream_empty(
        self,
        stream: BinaryIO,
    ) -> bool:
        """
        Determine whether a stream contains
        any data.
        """

        return self.stream_size(stream) == 0
# ============================================================
# Part 3.1E - Validation & Compatibility
# ============================================================

    def validate_serialized_data(
        self,
        data: bytes,
    ) -> bool:
        """
        Validate that serialized bytes can be
        successfully deserialized.
        """

        if not data:

            return False

        try:

            pickle.loads(data)

            return True

        except Exception:

            return False

    # -----------------------------------------------------

    def validate_binary_file(
        self,
        path: Union[str, Path],
    ) -> bool:
        """
        Validate that a binary file contains
        valid serialized data.
        """

        path = self.normalize_path(path)

        if not path.exists():

            return False

        try:

            data = self.file_to_bytes(path)

            return self.validate_serialized_data(data)

        except Exception:

            return False

    # -----------------------------------------------------

    def serialization_report(
        self,
        obj: Any,
    ) -> Dict[str, Any]:
        """
        Generate serialization diagnostics.
        """

        binary = self.serialize(obj)

        return {

            "class": obj.__class__.__name__,

            "module": obj.__class__.__module__,

            "binary_size": len(binary),

            "checksum": self.hash_bytes(

                binary,

                algorithm=ChecksumAlgorithm.SHA256,

            ),

            "pickle_protocol": self.binary_protocol(),

            "python_version": sys.version,

        }

    # -----------------------------------------------------

    def serialization_supported(
        self,
        obj: Any,
    ) -> bool:
        """
        Determine whether an object can be
        serialized.
        """

        try:

            self.serialize(obj)

            return True

        except Exception:

            return False

    # -----------------------------------------------------

    def assert_serializable(
        self,
        obj: Any,
    ) -> None:
        """
        Raise an exception if an object cannot
        be serialized.
        """

        if not self.serialization_supported(obj):

            raise SerializationError(

                f"{type(obj).__name__} "

                "cannot be serialized."

            )

    # -----------------------------------------------------

    def verify_roundtrip(
        self,
        obj: Any,
    ) -> VerificationResult:
        """
        Verify serialization integrity by
        performing a serialize/deserialize cycle.
        """

        original = self.hash_object(

            obj,

            algorithm=ChecksumAlgorithm.SHA256,

        )

        restored = self.deserialize(

            self.serialize(obj)

        )

        restored_hash = self.hash_object(

            restored,

            algorithm=ChecksumAlgorithm.SHA256,

        )

        success = self.compare_checksums(

            original,

            restored_hash,

        )

        return VerificationResult(

            success=success,

            target=type(obj).__name__,

            expected=original,

            actual=restored_hash,

            algorithm=ChecksumAlgorithm.SHA256,

            message=(

                "Roundtrip successful."

                if success

                else

                "Roundtrip verification failed."

            ),

        )

    # -----------------------------------------------------

    def compatibility_info(
        self,
    ) -> Dict[str, Any]:
        """
        Return runtime serialization compatibility
        information.
        """

        return {

            "python_version": sys.version,

            "pickle_protocol": self.binary_protocol(),

            "highest_protocol": pickle.HIGHEST_PROTOCOL,

            "default_encoding": self.config.encoding,

            "platform": platform.platform(),

            "implementation": platform.python_implementation(),

        }

    # -----------------------------------------------------

    def is_protocol_supported(
        self,
        protocol: int,
    ) -> bool:
        """
        Check whether a pickle protocol
        is supported.
        """

        return (

            0

            <=

            protocol

            <=

            pickle.HIGHEST_PROTOCOL

        )

    # -----------------------------------------------------

    def upgrade_protocol(
        self,
        source: Union[str, Path],
        destination: Union[str, Path],
        *,
        protocol: Optional[int] = None,
    ) -> IOResult:
        """
        Rewrite a binary file using a newer
        pickle protocol.
        """

        if protocol is None:

            protocol = pickle.HIGHEST_PROTOCOL

        obj = self.load_binary(source)

        return self.save_binary(

            destination,

            obj,

            protocol=protocol,

        )

    # -----------------------------------------------------

    def binary_file_info(
        self,
        path: Union[str, Path],
    ) -> Dict[str, Any]:
        """
        Extended binary file information.
        """

        path = self.normalize_path(path)

        self.validate_file(path)

        return {

            **self.binary_metadata(path),

            "valid": self.validate_binary_file(path),

            "checksum_sha256": self.sha256(path),

            "checksum_md5": self.md5(path),

        }

    # -----------------------------------------------------

    def compare_serialized_objects(
        self,
        first: Any,
        second: Any,
    ) -> bool:
        """
        Compare two objects by comparing their
        serialized binary representation.
        """

        return self.compare_checksums(

            self.hash_bytes(

                self.serialize(first)

            ),

            self.hash_bytes(

                self.serialize(second)

            ),

        )

    # -----------------------------------------------------

    def deserialize_safe(
        self,
        data: bytes,
        *,
        expected_type: Optional[Type] = None,
    ) -> Any:
        """
        Safely deserialize data and optionally
        verify the resulting type.
        """

        obj = self.deserialize(data)

        if (

            expected_type is not None

            and

            not isinstance(obj, expected_type)

        ):

            raise SerializationError(

                f"Expected "

                f"{expected_type.__name__}, "

                f"received "

                f"{type(obj).__name__}."

            )

        return obj

    # -----------------------------------------------------

    def binary_summary(
        self,
        path: Union[str, Path],
    ) -> str:
        """
        Human-readable summary describing
        a binary file.
        """

        info = self.binary_file_info(path)

        return (

            f"Binary File\n"

            f"-----------\n"

            f"Path: {info['path']}\n"

            f"Size: {info['size']} bytes\n"

            f"Valid: {info['valid']}\n"

            f"SHA256: {info['checksum_sha256']}\n"

            f"Protocol: {self.binary_protocol()}"

        )

    # -----------------------------------------------------

    @contextmanager
    def serialization_context(
        self,
        *,
        protocol: Optional[int] = None,
    ):
        """
        Temporary serialization configuration.

        Example
        -------
        with io.serialization_context(protocol=5):
            ...
        """

        previous = self.binary_protocol()

        if protocol is not None:

            self.set_binary_protocol(protocol)

        try:

            yield self

        finally:

            self.set_binary_protocol(previous)
# ============================================================
# Part 3.2A - Compression Foundation
# ============================================================

#
# Supported compression algorithms
#

_COMPRESSION_HANDLERS = {

    CompressionType.NONE: None,

    CompressionType.GZIP: gzip,

    CompressionType.ZIP: zipfile,

    CompressionType.BZ2: bz2,

    CompressionType.LZMA: lzma,

}

#
# Default file extensions
#

_COMPRESSION_EXTENSIONS = {

    CompressionType.NONE: "",

    CompressionType.GZIP: ".gz",

    CompressionType.ZIP: ".zip",

    CompressionType.BZ2: ".bz2",

    CompressionType.LZMA: ".xz",

}

# ------------------------------------------------------------

def available_compression_types(
    self,
) -> List[str]:
    """
    Return all supported compression types.
    """

    return [

        compression.value

        for compression

        in CompressionType

    ]

# ------------------------------------------------------------

def compression_supported(
    self,
    compression: CompressionType,
) -> bool:
    """
    Check whether a compression type is
    available on this platform.
    """

    return compression in self._COMPRESSION_HANDLERS

# ------------------------------------------------------------

def default_compression(
    self,
) -> CompressionType:
    """
    Return the configured default compression.
    """

    return self.config.compression

# ------------------------------------------------------------

def set_default_compression(
    self,
    compression: CompressionType,
) -> None:
    """
    Change the default compression.
    """

    if not self.compression_supported(
        compression
    ):

        raise CompressionError(

            f"Unsupported compression: "

            f"{compression}"

        )

    self.config.compression = compression

# ------------------------------------------------------------

def compression_extension(
    self,
    compression: CompressionType,
) -> str:
    """
    Return the file extension associated
    with a compression type.
    """

    return self._COMPRESSION_EXTENSIONS.get(

        compression,

        "",

    )

# ------------------------------------------------------------

def guess_compression(
    self,
    path: Union[str, Path],
) -> CompressionType:
    """
    Guess compression from filename.
    """

    suffix = Path(path).suffix.lower()

    for compression, extension in (

        self._COMPRESSION_EXTENSIONS.items()

    ):

        if extension == suffix:

            return compression

    return CompressionType.NONE

# ------------------------------------------------------------

def compression_level(
    self,
) -> int:
    """
    Return configured compression level.
    """

    return getattr(

        self.config,

        "compression_level",

        6,

    )

# ------------------------------------------------------------

def set_compression_level(
    self,
    level: int,
) -> None:
    """
    Set compression level.

    Valid values are 0–9.
    """

    if not (

        0 <= level <= 9

    ):

        raise ValueError(

            "Compression level "

            "must be between 0 and 9."

        )

    self.config.compression_level = level

# ------------------------------------------------------------

def open_compressed_writer(
    self,
    path: Union[str, Path],
    *,
    compression: Optional[
        CompressionType
    ] = None,
):
    """
    Open a writable compressed stream.
    """

    if compression is None:

        compression = self.default_compression()

    path = self.normalize_path(path)

    self.ensure_parent_directory(path)

    level = self.compression_level()

    if compression == CompressionType.NONE:

        return open(path, "wb")

    if compression == CompressionType.GZIP:

        return gzip.open(

            path,

            "wb",

            compresslevel=level,

        )

    if compression == CompressionType.BZ2:

        return bz2.open(

            path,

            "wb",

            compresslevel=level,

        )

    if compression == CompressionType.LZMA:

        return lzma.open(

            path,

            "wb",

            preset=level,

        )

    raise CompressionError(

        f"{compression} "

        "requires archive handling."

    )

# ------------------------------------------------------------

def open_compressed_reader(
    self,
    path: Union[str, Path],
    *,
    compression: Optional[
        CompressionType
    ] = None,
):
    """
    Open a readable compressed stream.
    """

    if compression is None:

        compression = self.guess_compression(path)

    path = self.normalize_path(path)

    self.validate_file(path)

    if compression == CompressionType.NONE:

        return open(path, "rb")

    if compression == CompressionType.GZIP:

        return gzip.open(

            path,

            "rb",

        )

    if compression == CompressionType.BZ2:

        return bz2.open(

            path,

            "rb",

        )

    if compression == CompressionType.LZMA:

        return lzma.open(

            path,

            "rb",

        )

    raise CompressionError(

        f"{compression} "

        "requires archive handling."

    )

# ------------------------------------------------------------

def compression_info(
    self,
) -> Dict[str, Any]:
    """
    Return current compression settings.
    """

    return {

        "default": self.default_compression().value,

        "level": self.compression_level(),

        "supported": self.available_compression_types(),

    }

# ------------------------------------------------------------

def estimate_compression_ratio(
    self,
    original_size: int,
    compressed_size: int,
) -> float:
    """
    Calculate compression ratio.

    Returns
    -------
    0.0–1.0

    Example

        0.42

    means the compressed file occupies
    42% of the original size.
    """

    if original_size <= 0:

        return 1.0

    return compressed_size / original_size

# ------------------------------------------------------------

def compression_percentage(
    self,
    original_size: int,
    compressed_size: int,
) -> float:
    """
    Percentage reduction.

    Example

        68.4
    """

    if original_size <= 0:

        return 0.0

    return (

        1.0 -

        (

            compressed_size

            / original_size

        )

    ) * 100.0

# ------------------------------------------------------------

def format_size(
    self,
    size: int,
) -> str:
    """
    Human-readable byte formatting.
    """

    units = (

        "B",

        "KB",

        "MB",

        "GB",

        "TB",

    )

    value = float(size)

    unit = 0

    while (

        value >= 1024

        and

        unit < len(units) - 1

    ):

        value /= 1024.0

        unit += 1

    return f"{value:.2f} {units[unit]}"
# ============================================================
# Part 3.2B - Compressed Serialization
# ============================================================

    def compress_bytes(
        self,
        data: bytes,
        *,
        compression: Optional[
            CompressionType
        ] = None,
        level: Optional[int] = None,
    ) -> bytes:
        """
        Compress a bytes object.

        Parameters
        ----------
        data
            Raw bytes.

        compression
            Compression algorithm.

        level
            Compression level.

        Returns
        -------
        bytes
        """

        if compression is None:

            compression = self.default_compression()

        if level is None:

            level = self.compression_level()

        if compression == CompressionType.NONE:

            return data

        if compression == CompressionType.GZIP:

            return gzip.compress(

                data,

                compresslevel=level,

            )

        if compression == CompressionType.BZ2:

            return bz2.compress(

                data,

                compresslevel=level,

            )

        if compression == CompressionType.LZMA:

            return lzma.compress(

                data,

                preset=level,

            )

        raise CompressionError(

            f"{compression} "

            "does not support direct byte compression."

        )

    # -----------------------------------------------------

    def decompress_bytes(
        self,
        data: bytes,
        *,
        compression: CompressionType,
    ) -> bytes:
        """
        Decompress raw bytes.
        """

        if compression == CompressionType.NONE:

            return data

        if compression == CompressionType.GZIP:

            return gzip.decompress(data)

        if compression == CompressionType.BZ2:

            return bz2.decompress(data)

        if compression == CompressionType.LZMA:

            return lzma.decompress(data)

        raise CompressionError(

            f"{compression} "

            "does not support direct byte decompression."

        )

    # -----------------------------------------------------

    def save_compressed(
        self,
        path: Union[str, Path],
        obj: Any,
        *,
        compression: Optional[
            CompressionType
        ] = None,
        protocol: Optional[int] = None,
    ) -> IOResult:
        """
        Serialize and compress an object.
        """

        if compression is None:

            compression = self.default_compression()

        binary = self.serialize(

            obj,

            protocol=protocol,

        )

        compressed = self.compress_bytes(

            binary,

            compression=compression,

        )

        return self.bytes_to_file(

            compressed,

            path,

        )

    # -----------------------------------------------------

    def load_compressed(
        self,
        path: Union[str, Path],
        *,
        compression: Optional[
            CompressionType
        ] = None,
    ) -> Any:
        """
        Load a compressed serialized object.
        """

        if compression is None:

            compression = self.guess_compression(path)

        compressed = self.file_to_bytes(path)

        binary = self.decompress_bytes(

            compressed,

            compression=compression,

        )

        return self.deserialize(binary)

    # -----------------------------------------------------

    def save_compressed_json(
        self,
        path: Union[str, Path],
        data: Dict[str, Any],
        *,
        compression: Optional[
            CompressionType
        ] = None,
    ) -> IOResult:
        """
        Save compressed JSON.
        """

        binary = json.dumps(

            data,

            indent=4,

            ensure_ascii=False,

        ).encode(

            self.config.encoding

        )

        compressed = self.compress_bytes(

            binary,

            compression=compression,

        )

        return self.bytes_to_file(

            compressed,

            path,

        )

    # -----------------------------------------------------

    def load_compressed_json(
        self,
        path: Union[str, Path],
        *,
        compression: Optional[
            CompressionType
        ] = None,
    ) -> Dict[str, Any]:
        """
        Load compressed JSON.
        """

        if compression is None:

            compression = self.guess_compression(path)

        compressed = self.file_to_bytes(path)

        binary = self.decompress_bytes(

            compressed,

            compression=compression,

        )

        return json.loads(

            binary.decode(

                self.config.encoding

            )

        )

    # -----------------------------------------------------

    def save_compressed_yaml(
        self,
        path: Union[str, Path],
        data: Dict[str, Any],
        *,
        compression: Optional[
            CompressionType
        ] = None,
    ) -> IOResult:
        """
        Save compressed YAML.
        """

        text = yaml.safe_dump(

            data,

            sort_keys=False,

            allow_unicode=True,

        )

        compressed = self.compress_bytes(

            text.encode(

                self.config.encoding

            ),

            compression=compression,

        )

        return self.bytes_to_file(

            compressed,

            path,

        )

    # -----------------------------------------------------

    def load_compressed_yaml(
        self,
        path: Union[str, Path],
        *,
        compression: Optional[
            CompressionType
        ] = None,
    ) -> Dict[str, Any]:
        """
        Load compressed YAML.
        """

        if compression is None:

            compression = self.guess_compression(path)

        compressed = self.file_to_bytes(path)

        binary = self.decompress_bytes(

            compressed,

            compression=compression,

        )

        return yaml.safe_load(

            binary.decode(

                self.config.encoding

            )

        )

    # -----------------------------------------------------

    def compression_statistics(
        self,
        original: bytes,
        compressed: bytes,
    ) -> Dict[str, Any]:
        """
        Compression statistics.
        """

        original_size = len(original)

        compressed_size = len(compressed)

        return {

            "original_size": original_size,

            "compressed_size": compressed_size,

            "ratio": self.estimate_compression_ratio(

                original_size,

                compressed_size,

            ),

            "saved_percent":

                self.compression_percentage(

                    original_size,

                    compressed_size,

                ),

            "space_saved":

                original_size -

                compressed_size,

        }

    # -----------------------------------------------------

    def serialize_and_compress(
        self,
        obj: Any,
        *,
        compression: Optional[
            CompressionType
        ] = None,
        protocol: Optional[int] = None,
    ) -> bytes:
        """
        Serialize an object directly into
        compressed bytes.
        """

        binary = self.serialize(

            obj,

            protocol=protocol,

        )

        return self.compress_bytes(

            binary,

            compression=compression,

        )

    # -----------------------------------------------------

    def decompress_and_deserialize(
        self,
        compressed: bytes,
        *,
        compression: CompressionType,
    ) -> Any:
        """
        Reverse of serialize_and_compress().
        """

        binary = self.decompress_bytes(

            compressed,

            compression=compression,

        )

        return self.deserialize(binary)

    # -----------------------------------------------------

    def recompress(
        self,
        data: bytes,
        *,
        source: CompressionType,
        target: CompressionType,
    ) -> bytes:
        """
        Convert between compression formats.
        """

        raw = self.decompress_bytes(

            data,

            compression=source,

        )

        return self.compress_bytes(

            raw,

            compression=target,

        )
# ============================================================
# Part 3.2C - Archive Management
# ============================================================

    def create_archive(
        self,
        archive_path: Union[str, Path],
        sources: Iterable[Union[str, Path]],
        *,
        compression: int = zipfile.ZIP_DEFLATED,
        compresslevel: Optional[int] = None,
    ) -> IOResult:
        """
        Create a ZIP archive from one or more files/directories.
        """

        archive_path = self.normalize_path(archive_path)
        self.ensure_parent_directory(archive_path)

        if compresslevel is None:
            compresslevel = self.compression_level()

        file_count = 0

        with zipfile.ZipFile(
            archive_path,
            mode="w",
            compression=compression,
            compresslevel=compresslevel,
        ) as archive:

            for source in sources:

                source = self.normalize_path(source)

                self.validate_file_or_directory(source)

                if source.is_file():

                    archive.write(
                        source,
                        arcname=source.name,
                    )

                    file_count += 1

                else:

                    for item in source.rglob("*"):

                        if item.is_file():

                            archive.write(
                                item,
                                arcname=item.relative_to(source),
                            )

                            file_count += 1

        return IOResult(
            status=IOStatus.SUCCESS,
            success=True,
            path=archive_path,
            format=FileFormat.ZIP,
            size=archive_path.stat().st_size,
            metadata={
                "files": file_count,
            },
        )

    # -----------------------------------------------------

    def extract_archive(
        self,
        archive_path: Union[str, Path],
        destination: Union[str, Path],
        *,
        overwrite: bool = True,
    ) -> IOResult:
        """
        Extract a ZIP archive.
        """

        archive_path = self.normalize_path(archive_path)
        destination = self.normalize_path(destination)

        self.validate_file(archive_path)

        destination.mkdir(
            parents=True,
            exist_ok=True,
        )

        with zipfile.ZipFile(
            archive_path,
            "r",
        ) as archive:

            if overwrite:

                archive.extractall(destination)

            else:

                for member in archive.infolist():

                    target = destination / member.filename

                    if not target.exists():

                        archive.extract(
                            member,
                            destination,
                        )

        return IOResult(
            status=IOStatus.SUCCESS,
            success=True,
            path=destination,
            format=FileFormat.DIRECTORY,
        )

    # -----------------------------------------------------

    def list_archive(
        self,
        archive_path: Union[str, Path],
    ) -> List[str]:
        """
        Return filenames contained in an archive.
        """

        archive_path = self.normalize_path(archive_path)

        self.validate_file(archive_path)

        with zipfile.ZipFile(
            archive_path,
            "r",
        ) as archive:

            return archive.namelist()

    # -----------------------------------------------------

    def archive_info(
        self,
        archive_path: Union[str, Path],
    ) -> Dict[str, Any]:
        """
        Return archive metadata.
        """

        archive_path = self.normalize_path(archive_path)

        self.validate_file(archive_path)

        with zipfile.ZipFile(
            archive_path,
            "r",
        ) as archive:

            members = archive.infolist()

            compressed = sum(
                m.compress_size
                for m in members
            )

            uncompressed = sum(
                m.file_size
                for m in members
            )

        return {

            "path": str(archive_path),

            "entries": len(members),

            "compressed_size": compressed,

            "uncompressed_size": uncompressed,

            "compression_ratio":
                self.estimate_compression_ratio(
                    uncompressed,
                    compressed,
                ),

            "checksum":
                self.sha256(archive_path),

        }

    # -----------------------------------------------------

    def archive_contains(
        self,
        archive_path: Union[str, Path],
        filename: str,
    ) -> bool:
        """
        Check whether an archive contains a file.
        """

        return filename in self.list_archive(
            archive_path
        )

    # -----------------------------------------------------

    def archive_member_info(
        self,
        archive_path: Union[str, Path],
        filename: str,
    ) -> Dict[str, Any]:
        """
        Return metadata for one archive member.
        """

        archive_path = self.normalize_path(
            archive_path
        )

        with zipfile.ZipFile(
            archive_path,
            "r",
        ) as archive:

            info = archive.getinfo(filename)

        return {

            "filename": info.filename,

            "compressed_size":
                info.compress_size,

            "size":
                info.file_size,

            "modified":
                datetime(
                    *info.date_time
                ).isoformat(),

            "crc":
                hex(info.CRC),

        }

    # -----------------------------------------------------

    def add_to_archive(
        self,
        archive_path: Union[str, Path],
        source: Union[str, Path],
        *,
        arcname: Optional[str] = None,
    ) -> None:
        """
        Add a file to an existing archive.
        """

        archive_path = self.normalize_path(
            archive_path
        )

        source = self.normalize_path(source)

        self.validate_file(source)

        with zipfile.ZipFile(
            archive_path,
            "a",
            compression=zipfile.ZIP_DEFLATED,
        ) as archive:

            archive.write(

                source,

                arcname=arcname
                or source.name,

            )

    # -----------------------------------------------------

    def extract_member(
        self,
        archive_path: Union[str, Path],
        filename: str,
        destination: Union[str, Path],
    ) -> Path:
        """
        Extract a single member.
        """

        archive_path = self.normalize_path(
            archive_path
        )

        destination = self.normalize_path(
            destination
        )

        with zipfile.ZipFile(
            archive_path,
            "r",
        ) as archive:

            archive.extract(
                filename,
                destination,
            )

        return destination / filename

    # -----------------------------------------------------

    def read_archive_member(
        self,
        archive_path: Union[str, Path],
        filename: str,
    ) -> bytes:
        """
        Read a file inside an archive.
        """

        archive_path = self.normalize_path(
            archive_path
        )

        with zipfile.ZipFile(
            archive_path,
            "r",
        ) as archive:

            return archive.read(filename)

    # -----------------------------------------------------

    def archive_checksum(
        self,
        archive_path: Union[str, Path],
    ) -> str:
        """
        SHA256 checksum of an archive.
        """

        return self.sha256(archive_path)

    # -----------------------------------------------------

    def verify_archive(
        self,
        archive_path: Union[str, Path],
    ) -> bool:
        """
        Verify ZIP archive integrity.
        """

        archive_path = self.normalize_path(
            archive_path
        )

        self.validate_file(archive_path)

        with zipfile.ZipFile(
            archive_path,
            "r",
        ) as archive:

            return archive.testzip() is None

    # -----------------------------------------------------

    def remove_archive(
        self,
        archive_path: Union[str, Path],
    ) -> None:
        """
        Delete an archive.
        """

        archive_path = self.normalize_path(
            archive_path
        )

        if archive_path.exists():

            archive_path.unlink()

    # -----------------------------------------------------

    def archive_summary(
        self,
        archive_path: Union[str, Path],
    ) -> str:
        """
        Human-readable archive summary.
        """

        info = self.archive_info(
            archive_path
        )

        return (
            f"Archive: {info['path']}\n"
            f"Entries: {info['entries']}\n"
            f"Compressed: "
            f"{self.format_size(info['compressed_size'])}\n"
            f"Original: "
            f"{self.format_size(info['uncompressed_size'])}\n"
            f"Ratio: "
            f"{info['compression_ratio']:.2%}"
        )
# ============================================================
# Part 3.2D - Atomic Saving
# ============================================================

    @contextmanager
    def atomic_write(
        self,
        destination: Union[str, Path],
        *,
        mode: str = "wb",
        encoding: Optional[str] = None,
        suffix: str = ".tmp",
        preserve_permissions: bool = True,
    ):
        """
        Context manager for atomic file writing.

        A temporary file is created in the same directory as the
        destination. Upon successful completion, it atomically
        replaces the destination file. On failure, the temporary
        file is removed.

        Example
        -------
        with self.atomic_write("scene.json", "w") as fp:
            json.dump(data, fp)
        """

        destination = self.normalize_path(destination)

        self.ensure_parent_directory(destination)

        if encoding is None:
            encoding = self.config.encoding

        fd, temp_name = tempfile.mkstemp(
            dir=str(destination.parent),
            suffix=suffix,
        )

        os.close(fd)

        temp_path = Path(temp_name)

        try:

            kwargs = {}

            if "b" not in mode:
                kwargs["encoding"] = encoding

            with temp_path.open(mode, **kwargs) as stream:
                yield stream

            if (
                preserve_permissions
                and destination.exists()
            ):

                shutil.copystat(
                    destination,
                    temp_path,
                )

            os.replace(
                temp_path,
                destination,
            )

        except Exception:

            if temp_path.exists():

                temp_path.unlink()

            raise

    # -----------------------------------------------------

    def atomic_save_bytes(
        self,
        path: Union[str, Path],
        data: bytes,
    ) -> IOResult:
        """
        Atomically save raw bytes.
        """

        with self.atomic_write(
            path,
            mode="wb",
        ) as fp:

            fp.write(data)

        return IOResult(
            status=IOStatus.SUCCESS,
            success=True,
            path=Path(path),
            format=FileFormat.BINARY,
            size=len(data),
        )

    # -----------------------------------------------------

    def atomic_save_text(
        self,
        path: Union[str, Path],
        text: str,
        *,
        encoding: Optional[str] = None,
    ) -> IOResult:
        """
        Atomically save text.
        """

        with self.atomic_write(
            path,
            mode="w",
            encoding=encoding,
        ) as fp:

            fp.write(text)

        return IOResult(
            status=IOStatus.SUCCESS,
            success=True,
            path=Path(path),
            format=FileFormat.TEXT,
            size=len(text.encode(
                encoding or self.config.encoding
            )),
        )

    # -----------------------------------------------------

    def atomic_save_json(
        self,
        path: Union[str, Path],
        data: Any,
        *,
        indent: int = 4,
    ) -> IOResult:
        """
        Atomically save JSON.
        """

        with self.atomic_write(
            path,
            mode="w",
        ) as fp:

            json.dump(
                data,
                fp,
                indent=indent,
                ensure_ascii=False,
            )

        return IOResult(
            status=IOStatus.SUCCESS,
            success=True,
            path=Path(path),
            format=FileFormat.JSON,
        )

    # -----------------------------------------------------

    def atomic_save_yaml(
        self,
        path: Union[str, Path],
        data: Any,
    ) -> IOResult:
        """
        Atomically save YAML.
        """

        with self.atomic_write(
            path,
            mode="w",
        ) as fp:

            yaml.safe_dump(
                data,
                fp,
                allow_unicode=True,
                sort_keys=False,
            )

        return IOResult(
            status=IOStatus.SUCCESS,
            success=True,
            path=Path(path),
            format=FileFormat.YAML,
        )

    # -----------------------------------------------------

    def atomic_save_binary(
        self,
        path: Union[str, Path],
        obj: Any,
        *,
        protocol: Optional[int] = None,
    ) -> IOResult:
        """
        Atomically serialize and save a Python object.
        """

        binary = self.serialize(
            obj,
            protocol=protocol,
        )

        return self.atomic_save_bytes(
            path,
            binary,
        )

    # -----------------------------------------------------

    def atomic_save_csv(
        self,
        path: Union[str, Path],
        rows: Iterable[Iterable[Any]],
    ) -> IOResult:
        """
        Atomically save CSV data.
        """

        with self.atomic_write(
            path,
            mode="w",
        ) as fp:

            writer = csv.writer(fp)

            for row in rows:

                writer.writerow(row)

        return IOResult(
            status=IOStatus.SUCCESS,
            success=True,
            path=Path(path),
            format=FileFormat.CSV,
        )

    # -----------------------------------------------------

    def atomic_replace(
        self,
        source: Union[str, Path],
        destination: Union[str, Path],
    ) -> None:
        """
        Atomically replace one file with another.
        """

        source = self.normalize_path(source)
        destination = self.normalize_path(destination)

        os.replace(
            source,
            destination,
        )

    # -----------------------------------------------------

    def atomic_copy(
        self,
        source: Union[str, Path],
        destination: Union[str, Path],
    ) -> IOResult:
        """
        Copy using a temporary file followed
        by an atomic replace.
        """

        source = self.normalize_path(source)
        destination = self.normalize_path(destination)

        self.validate_file(source)

        fd, temp_name = tempfile.mkstemp(
            dir=str(destination.parent),
        )

        os.close(fd)

        temp_path = Path(temp_name)

        try:

            shutil.copy2(
                source,
                temp_path,
            )

            os.replace(
                temp_path,
                destination,
            )

        finally:

            if temp_path.exists():

                temp_path.unlink()

        return IOResult(
            status=IOStatus.SUCCESS,
            success=True,
            path=destination,
            format=FileFormat.BINARY,
        )

    # -----------------------------------------------------

    def safe_delete(
        self,
        path: Union[str, Path],
    ) -> bool:
        """
        Delete a file safely.

        Returns False if the file does not exist.
        """

        path = self.normalize_path(path)

        if not path.exists():

            return False

        path.unlink()

        return True

    # -----------------------------------------------------

    def atomic_exists(
        self,
        path: Union[str, Path],
    ) -> bool:
        """
        Convenience wrapper for existence checks.
        """

        return self.normalize_path(path).exists()

    # -----------------------------------------------------

    def verify_atomic_write(
        self,
        path: Union[str, Path],
        expected_checksum: str,
    ) -> bool:
        """
        Verify a completed atomic write.
        """

        actual = self.sha256(path)

        return self.compare_checksums(
            actual,
            expected_checksum,
        )

    # -----------------------------------------------------

    def transactional_save(
        self,
        path: Union[str, Path],
        writer: Callable[[Any], None],
        *,
        mode: str = "wb",
    ) -> IOResult:
        """
        Generic transactional save.

        The caller receives an open stream
        and performs all write operations.
        """

        with self.atomic_write(
            path,
            mode=mode,
        ) as fp:

            writer(fp)

        return IOResult(
            status=IOStatus.SUCCESS,
            success=True,
            path=Path(path),
        )
# ============================================================
# Part 3.2E - High-Level Utilities
# ============================================================

    def smart_save(
        self,
        path: Union[str, Path],
        obj: Any,
        *,
        compression: Optional[CompressionType] = None,
        atomic: bool = True,
        create_backup: bool = False,
        protocol: Optional[int] = None,
    ) -> IOResult:
        """
        Intelligent save operation.

        Automatically combines serialization,
        compression, backup creation, and
        atomic writing.
        """

        path = self.normalize_path(path)

        if compression is None:
            compression = self.default_compression()

        if create_backup and path.exists():
            self.create_backup(path)

        data = self.serialize(obj, protocol=protocol)

        if compression != CompressionType.NONE:
            data = self.compress_bytes(
                data,
                compression=compression,
            )

        if atomic:
            return self.atomic_save_bytes(path, data)

        return self.bytes_to_file(data, path)

    # -----------------------------------------------------

    def smart_load(
        self,
        path: Union[str, Path],
        *,
        compression: Optional[CompressionType] = None,
    ) -> Any:
        """
        Intelligent load operation.
        """

        path = self.normalize_path(path)

        if compression is None:
            compression = self.guess_compression(path)

        data = self.file_to_bytes(path)

        if compression != CompressionType.NONE:
            data = self.decompress_bytes(
                data,
                compression=compression,
            )

        return self.deserialize(data)

    # -----------------------------------------------------

    def backup_and_save(
        self,
        path: Union[str, Path],
        obj: Any,
        *,
        compression: Optional[
            CompressionType
        ] = None,
    ) -> IOResult:
        """
        Backup an existing file before saving.
        """

        return self.smart_save(
            path,
            obj,
            compression=compression,
            atomic=True,
            create_backup=True,
        )

    # -----------------------------------------------------

    def verify_saved_file(
        self,
        path: Union[str, Path],
        expected: Any,
        *,
        compression: Optional[
            CompressionType
        ] = None,
    ) -> bool:
        """
        Verify a saved object by loading it
        back and comparing hashes.
        """

        loaded = self.smart_load(
            path,
            compression=compression,
        )

        return self.compare_objects(
            expected,
            loaded,
        )

    # -----------------------------------------------------

    def save_snapshot(
        self,
        directory: Union[str, Path],
        name: str,
        obj: Any,
    ) -> IOResult:
        """
        Save a timestamped snapshot.
        """

        directory = self.normalize_path(directory)

        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        filename = (
            f"{name}_{timestamp}.bin"
        )

        return self.smart_save(
            directory / filename,
            obj,
        )

    # -----------------------------------------------------

    def batch_save(
        self,
        items: Mapping[
            Union[str, Path],
            Any,
        ],
        *,
        compression: Optional[
            CompressionType
        ] = None,
    ) -> List[IOResult]:
        """
        Save multiple objects.
        """

        results = []

        for path, obj in items.items():

            results.append(

                self.smart_save(
                    path,
                    obj,
                    compression=compression,
                )

            )

        return results

    # -----------------------------------------------------

    def batch_load(
        self,
        paths: Iterable[
            Union[str, Path]
        ],
        *,
        compression: Optional[
            CompressionType
        ] = None,
    ) -> Dict[Path, Any]:
        """
        Load multiple serialized objects.
        """

        result = {}

        for path in paths:

            path = self.normalize_path(path)

            result[path] = self.smart_load(
                path,
                compression=compression,
            )

        return result

    # -----------------------------------------------------

    def duplicate_file(
        self,
        source: Union[str, Path],
        destination: Union[str, Path],
    ) -> IOResult:
        """
        Duplicate a file while preserving
        metadata.
        """

        source = self.normalize_path(source)
        destination = self.normalize_path(destination)

        self.ensure_parent_directory(
            destination
        )

        shutil.copy2(
            source,
            destination,
        )

        return IOResult(
            status=IOStatus.SUCCESS,
            success=True,
            path=destination,
            format=FileFormat.BINARY,
        )

    # -----------------------------------------------------

    def optimize_storage(
        self,
        obj: Any,
    ) -> Dict[str, Any]:
        """
        Evaluate every supported compression
        algorithm and recommend the smallest.
        """

        binary = self.serialize(obj)

        best = {
            "compression": CompressionType.NONE,
            "size": len(binary),
        }

        report = {}

        for compression in (
            CompressionType.NONE,
            CompressionType.GZIP,
            CompressionType.BZ2,
            CompressionType.LZMA,
        ):

            compressed = self.compress_bytes(
                binary,
                compression=compression,
            )

            size = len(compressed)

            report[
                compression.value
            ] = size

            if size < best["size"]:

                best = {
                    "compression": compression,
                    "size": size,
                }

        return {

            "original": len(binary),

            "recommended":
                best["compression"].value,

            "compressed_size":
                best["size"],

            "results": report,

        }

    # -----------------------------------------------------

    def export_package(
        self,
        archive_path: Union[str, Path],
        files: Iterable[
            Union[str, Path]
        ],
    ) -> IOResult:
        """
        Export a portable ZIP package.
        """

        return self.create_archive(
            archive_path,
            files,
        )

    # -----------------------------------------------------

    def import_package(
        self,
        archive_path: Union[str, Path],
        destination: Union[str, Path],
    ) -> IOResult:
        """
        Import a previously exported package.
        """

        return self.extract_archive(
            archive_path,
            destination,
        )

    # -----------------------------------------------------

    def storage_summary(
        self,
    ) -> Dict[str, Any]:
        """
        Return storage configuration.
        """

        return {

            "compression":
                self.default_compression().value,

            "compression_level":
                self.compression_level(),

            "pickle_protocol":
                self.binary_protocol(),

            "encoding":
                self.config.encoding,

            "checksum":
                self.checksum_algorithm.value,

            "atomic_writes": True,

        }

    # -----------------------------------------------------

    def reset_storage_defaults(
        self,
    ) -> None:
        """
        Restore recommended storage settings.
        """

        self.set_default_compression(
            CompressionType.GZIP
        )

        self.set_compression_level(6)

        self.set_binary_protocol(
            pickle.HIGHEST_PROTOCOL
        )

    # -----------------------------------------------------

    @contextmanager
    def storage_configuration(
        self,
        *,
        compression: Optional[
            CompressionType
        ] = None,
        compression_level: Optional[
            int
        ] = None,
        protocol: Optional[
            int
        ] = None,
    ):
        """
        Temporarily override storage settings.
        """

        previous = {

            "compression":
                self.default_compression(),

            "level":
                self.compression_level(),

            "protocol":
                self.binary_protocol(),

        }

        try:

            if compression is not None:
                self.set_default_compression(
                    compression
                )

            if compression_level is not None:
                self.set_compression_level(
                    compression_level
                )

            if protocol is not None:
                self.set_binary_protocol(
                    protocol
                )

            yield self

        finally:

            self.set_default_compression(
                previous["compression"]
            )

            self.set_compression_level(
                previous["level"]
            )

            self.set_binary_protocol(
                previous["protocol"]
            )  
# ============================================================
# Part 3.3A - Version Foundation
# ============================================================

# ------------------------------------------------------------
# Module Version Constants
# ------------------------------------------------------------

IO_VERSION = "1.0.0"

IO_VERSION_MAJOR = 1
IO_VERSION_MINOR = 0
IO_VERSION_PATCH = 0

IO_SCHEMA_VERSION = 1

# ------------------------------------------------------------
# Semantic Version Utilities
# ------------------------------------------------------------

    def parse_version(
        self,
        version: Union[str, Tuple[int, int, int]],
    ) -> Tuple[int, int, int]:
        """
        Parse a semantic version.

        Examples
        --------
        "1.2.5" -> (1, 2, 5)
        (1,2,5) -> (1,2,5)
        """

        if isinstance(version, tuple):

            if len(version) != 3:

                raise VersionError(
                    "Version tuple must contain three values."
                )

            return tuple(
                int(v)
                for v in version
            )

        parts = str(version).strip().split(".")

        if len(parts) != 3:

            raise VersionError(
                f"Invalid semantic version: {version}"
            )

        try:

            return tuple(
                int(part)
                for part in parts
            )

        except ValueError as exc:

            raise VersionError(
                f"Invalid version: {version}"
            ) from exc

    # -----------------------------------------------------

    def version_string(
        self,
        version: Tuple[int, int, int],
    ) -> str:
        """
        Convert a version tuple into a string.
        """

        return ".".join(

            str(v)

            for v in version

        )

    # -----------------------------------------------------

    def current_version(
        self,
    ) -> str:
        """
        Current IO module version.
        """

        return IO_VERSION

    # -----------------------------------------------------

    def current_version_tuple(
        self,
    ) -> Tuple[int, int, int]:
        """
        Current version tuple.
        """

        return (

            IO_VERSION_MAJOR,

            IO_VERSION_MINOR,

            IO_VERSION_PATCH,

        )

    # -----------------------------------------------------

    def compare_versions(
        self,
        left: Union[str, Tuple[int, int, int]],
        right: Union[str, Tuple[int, int, int]],
    ) -> int:
        """
        Compare two semantic versions.

        Returns
        -------
        -1
            left < right

         0
            left == right

         1
            left > right
        """

        left = self.parse_version(left)
        right = self.parse_version(right)

        if left < right:

            return -1

        if left > right:

            return 1

        return 0

    # -----------------------------------------------------

    def version_equal(
        self,
        left,
        right,
    ) -> bool:

        return self.compare_versions(
            left,
            right,
        ) == 0

    # -----------------------------------------------------

    def version_newer(
        self,
        left,
        right,
    ) -> bool:

        return self.compare_versions(
            left,
            right,
        ) > 0

    # -----------------------------------------------------

    def version_older(
        self,
        left,
        right,
    ) -> bool:

        return self.compare_versions(
            left,
            right,
        ) < 0

    # -----------------------------------------------------

    def version_difference(
        self,
        left,
        right,
    ) -> Dict[str, int]:
        """
        Difference between two versions.
        """

        a = self.parse_version(left)
        b = self.parse_version(right)

        return {

            "major": b[0] - a[0],

            "minor": b[1] - a[1],

            "patch": b[2] - a[2],

        }

    # -----------------------------------------------------

    def bump_major(
        self,
        version,
    ) -> str:
        """
        Increment major version.
        """

        major, _, _ = self.parse_version(version)

        return self.version_string(

            (major + 1, 0, 0)

        )

    # -----------------------------------------------------

    def bump_minor(
        self,
        version,
    ) -> str:
        """
        Increment minor version.
        """

        major, minor, _ = self.parse_version(version)

        return self.version_string(

            (major, minor + 1, 0)

        )

    # -----------------------------------------------------

    def bump_patch(
        self,
        version,
    ) -> str:
        """
        Increment patch version.
        """

        major, minor, patch = self.parse_version(version)

        return self.version_string(

            (

                major,

                minor,

                patch + 1,

            )

        )

    # -----------------------------------------------------

    def compatible_version(
        self,
        version,
    ) -> bool:
        """
        Determine whether a version is
        compatible with the current IO version.

        Compatibility rule:
            Same major version.
        """

        major = self.parse_version(version)[0]

        return major == IO_VERSION_MAJOR

    # -----------------------------------------------------

    def latest_version(
        self,
    ) -> str:
        """
        Return the latest supported version.
        """

        return IO_VERSION

    # -----------------------------------------------------

    def version_metadata(
        self,
    ) -> Dict[str, Any]:
        """
        Return metadata describing the
        current storage format.
        """

        return {

            "version": IO_VERSION,

            "version_tuple":

                self.current_version_tuple(),

            "schema_version":

                IO_SCHEMA_VERSION,

            "python":

                sys.version,

            "platform":

                platform.platform(),

            "created":

                datetime.now().isoformat(),

        }

    # -----------------------------------------------------

    def version_summary(
        self,
    ) -> str:
        """
        Human-readable version summary.
        """

        metadata = self.version_metadata()

        return (

            f"IO Version : {metadata['version']}\n"

            f"Schema     : {metadata['schema_version']}\n"

            f"Python     : "

            f"{platform.python_version()}\n"

            f"Platform   : "

            f"{metadata['platform']}"

        )

    # -----------------------------------------------------

    def validate_version(
        self,
        version,
    ) -> None:
        """
        Validate semantic version syntax.
        """

        self.parse_version(version)

    # -----------------------------------------------------

    def require_compatible_version(
        self,
        version,
    ) -> None:
        """
        Raise VersionError if the supplied
        version is incompatible.
        """

        if not self.compatible_version(version):

            raise VersionError(

                f"Incompatible version "

                f"{version}. "

                f"Expected major "

                f"{IO_VERSION_MAJOR}.x.x"

            )
# ============================================================
# Part 3.3B - Migration Registry
# ============================================================

    def initialize_migration_registry(self) -> None:
        """
        Initialize the migration registry.

        Structure
        ---------
        {
            ("1.0.0", "1.1.0"): migration_function,
            ("1.1.0", "1.2.0"): migration_function,
        }
        """

        if not hasattr(self, "_migrations"):

            self._migrations: Dict[
                Tuple[str, str],
                Callable[[Any], Any]
            ] = {}

    # -----------------------------------------------------

    def register_migration(
        self,
        source_version: str,
        target_version: str,
        migration: Callable[[Any], Any],
    ) -> None:
        """
        Register a migration.
        """

        self.validate_version(source_version)
        self.validate_version(target_version)

        self.initialize_migration_registry()

        key = (
            source_version,
            target_version,
        )

        if key in self._migrations:

            raise VersionError(
                f"Migration {key} already exists."
            )

        self._migrations[key] = migration

    # -----------------------------------------------------

    def unregister_migration(
        self,
        source_version: str,
        target_version: str,
    ) -> bool:
        """
        Remove a migration.
        """

        self.initialize_migration_registry()

        return (

            self._migrations.pop(
                (source_version, target_version),
                None,
            )

            is not None

        )

    # -----------------------------------------------------

    def has_migration(
        self,
        source_version: str,
        target_version: str,
    ) -> bool:
        """
        Check whether a migration exists.
        """

        self.initialize_migration_registry()

        return (

            source_version,
            target_version,

        ) in self._migrations

    # -----------------------------------------------------

    def get_migration(
        self,
        source_version: str,
        target_version: str,
    ) -> Callable[[Any], Any]:
        """
        Return a migration callable.
        """

        self.initialize_migration_registry()

        key = (
            source_version,
            target_version,
        )

        if key not in self._migrations:

            raise VersionError(

                f"No migration "

                f"{source_version} -> "

                f"{target_version}"

            )

        return self._migrations[key]

    # -----------------------------------------------------

    def list_migrations(
        self,
    ) -> List[Tuple[str, str]]:
        """
        Return all registered migrations.
        """

        self.initialize_migration_registry()

        return sorted(
            self._migrations.keys()
        )

    # -----------------------------------------------------

    def migration_count(
        self,
    ) -> int:
        """
        Number of registered migrations.
        """

        self.initialize_migration_registry()

        return len(
            self._migrations
        )

    # -----------------------------------------------------

    def clear_migrations(
        self,
    ) -> None:
        """
        Remove every registered migration.
        """

        self.initialize_migration_registry()

        self._migrations.clear()

    # -----------------------------------------------------

    def source_versions(
        self,
    ) -> List[str]:
        """
        Return all source versions.
        """

        self.initialize_migration_registry()

        return sorted(

            {

                src

                for src, _

                in self._migrations

            }

        )

    # -----------------------------------------------------

    def target_versions(
        self,
    ) -> List[str]:
        """
        Return all target versions.
        """

        self.initialize_migration_registry()

        return sorted(

            {

                dst

                for _, dst

                in self._migrations

            }

        )

    # -----------------------------------------------------

    def outgoing_migrations(
        self,
        version: str,
    ) -> List[str]:
        """
        Return every direct migration
        starting at the supplied version.
        """

        self.initialize_migration_registry()

        return sorted(

            [

                dst

                for src, dst

                in self._migrations

                if src == version

            ]

        )

    # -----------------------------------------------------

    def incoming_migrations(
        self,
        version: str,
    ) -> List[str]:
        """
        Return every direct migration
        ending at the supplied version.
        """

        self.initialize_migration_registry()

        return sorted(

            [

                src

                for src, dst

                in self._migrations

                if dst == version

            ]

        )

    # -----------------------------------------------------

    def latest_registered_version(
        self,
    ) -> Optional[str]:
        """
        Highest version appearing in the registry.
        """

        self.initialize_migration_registry()

        versions = set()

        for src, dst in self._migrations:

            versions.add(src)
            versions.add(dst)

        if not versions:

            return None

        return max(
            versions,
            key=self.parse_version,
        )

    # -----------------------------------------------------

    def earliest_registered_version(
        self,
    ) -> Optional[str]:
        """
        Lowest version appearing in the registry.
        """

        self.initialize_migration_registry()

        versions = set()

        for src, dst in self._migrations:

            versions.add(src)
            versions.add(dst)

        if not versions:

            return None

        return min(
            versions,
            key=self.parse_version,
        )

    # -----------------------------------------------------

    def migration_exists_for(
        self,
        version: str,
    ) -> bool:
        """
        Determine whether a version participates
        in any migration.
        """

        self.initialize_migration_registry()

        return any(

            version == src

            or

            version == dst

            for src, dst

            in self._migrations

        )

    # -----------------------------------------------------

    def migration_registry_info(
        self,
    ) -> Dict[str, Any]:
        """
        Summary of the migration registry.
        """

        self.initialize_migration_registry()

        return {

            "count":
                self.migration_count(),

            "earliest":
                self.earliest_registered_version(),

            "latest":
                self.latest_registered_version(),

            "sources":
                self.source_versions(),

            "targets":
                self.target_versions(),

        }

    # -----------------------------------------------------

    def migration_registry_summary(
        self,
    ) -> str:
        """
        Human-readable registry summary.
        """

        info = self.migration_registry_info()

        lines = [

            "Migration Registry",

            "------------------",

            f"Registered : {info['count']}",

            f"Earliest   : {info['earliest']}",

            f"Latest     : {info['latest']}",

            "",

            "Mappings:",

        ]

        for src, dst in self.list_migrations():

            lines.append(
                f"  {src} -> {dst}"
            )

        return "\n".join(lines)

    # -----------------------------------------------------

    def migration_graph(
        self,
    ) -> Dict[str, List[str]]:
        """
        Return the migration graph as an
        adjacency list.
        """

        self.initialize_migration_registry()

        graph: Dict[
            str,
            List[str]
        ] = {}

        for src, dst in self._migrations:

            graph.setdefault(
                src,
                []
            ).append(dst)

        for node in graph:

            graph[node].sort(
                key=self.parse_version
            )

        return graph
# ============================================================
# Part 3.3C - Migration Engine
# ============================================================

    def find_migration_path(
        self,
        source_version: str,
        target_version: str,
    ) -> List[Tuple[str, str]]:
        """
        Find the shortest migration path between two versions.

        Returns
        -------
        [
            ("1.0.0", "1.1.0"),
            ("1.1.0", "1.2.0"),
            ...
        ]
        """

        self.initialize_migration_registry()

        if source_version == target_version:
            return []

        graph = self.migration_graph()

        queue = deque(
            [(source_version, [])]
        )

        visited = {source_version}

        while queue:

            current, path = queue.popleft()

            for neighbor in graph.get(current, []):

                if neighbor in visited:
                    continue

                new_path = path + [
                    (current, neighbor)
                ]

                if neighbor == target_version:
                    return new_path

                visited.add(neighbor)

                queue.append(
                    (neighbor, new_path)
                )

        raise VersionError(

            f"No migration path from "

            f"{source_version} to "

            f"{target_version}"

        )

    # -----------------------------------------------------

    def migrate_step(
        self,
        data: Any,
        source_version: str,
        target_version: str,
    ) -> Any:
        """
        Execute a single migration step.
        """

        migration = self.get_migration(
            source_version,
            target_version,
        )

        return migration(data)

    # -----------------------------------------------------

    def migrate(
        self,
        data: Any,
        source_version: str,
        target_version: str,
        *,
        validate: bool = True,
    ) -> Any:
        """
        Execute a complete migration.
        """

        if source_version == target_version:
            return data

        path = self.find_migration_path(
            source_version,
            target_version,
        )

        migrated = data

        for src, dst in path:

            migrated = self.migrate_step(
                migrated,
                src,
                dst,
            )

            if validate:

                self.validate_migrated_data(
                    migrated,
                    dst,
                )

        return migrated

    # -----------------------------------------------------

    def migrate_to_latest(
        self,
        data: Any,
        source_version: str,
    ) -> Any:
        """
        Upgrade data to the latest supported version.
        """

        latest = self.latest_version()

        return self.migrate(

            data,

            source_version,

            latest,

        )

    # -----------------------------------------------------

    def downgrade(
        self,
        data: Any,
        source_version: str,
        target_version: str,
    ) -> Any:
        """
        Downgrade data.

        Reverse migrations must already
        exist in the registry.
        """

        return self.migrate(

            data,

            source_version,

            target_version,

        )

    # -----------------------------------------------------

    def validate_migrated_data(
        self,
        data: Any,
        version: str,
    ) -> bool:
        """
        Basic validation after migration.
        """

        if data is None:

            raise VersionError(

                "Migration produced None."

            )

        if isinstance(data, dict):

            data.setdefault(
                "version",
                version,
            )

        return True

    # -----------------------------------------------------

    def can_migrate(
        self,
        source_version: str,
        target_version: str,
    ) -> bool:
        """
        Determine whether a migration path exists.
        """

        try:

            self.find_migration_path(

                source_version,

                target_version,

            )

            return True

        except VersionError:

            return False

    # -----------------------------------------------------

    def migration_steps(
        self,
        source_version: str,
        target_version: str,
    ) -> int:
        """
        Number of migration steps.
        """

        return len(

            self.find_migration_path(

                source_version,

                target_version,

            )

        )

    # -----------------------------------------------------

    def migration_report(
        self,
        source_version: str,
        target_version: str,
    ) -> Dict[str, Any]:
        """
        Generate a migration report.
        """

        path = self.find_migration_path(

            source_version,

            target_version,

        )

        return {

            "source": source_version,

            "target": target_version,

            "steps": len(path),

            "path": path,

            "possible": True,

        }

    # -----------------------------------------------------

    def migration_summary(
        self,
        source_version: str,
        target_version: str,
    ) -> str:
        """
        Human-readable migration summary.
        """

        report = self.migration_report(

            source_version,

            target_version,

        )

        lines = [

            "Migration Summary",

            "-----------------",

            f"Source : {report['source']}",

            f"Target : {report['target']}",

            f"Steps  : {report['steps']}",

            "",

            "Execution Path:",

        ]

        for src, dst in report["path"]:

            lines.append(

                f"  {src} -> {dst}"

            )

        return "\n".join(lines)

    # -----------------------------------------------------

    def auto_migrate(
        self,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Automatically migrate a versioned object.
        """

        version = data.get(
            "version",
            "1.0.0",
        )

        if version == self.latest_version():

            return data

        return self.migrate_to_latest(

            data,

            version,

        )

    # -----------------------------------------------------

    def migrate_file(
        self,
        source_path: Union[str, Path],
        destination_path: Union[str, Path],
    ) -> IOResult:
        """
        Load, migrate, and save a file.
        """

        obj = self.smart_load(
            source_path
        )

        migrated = self.auto_migrate(
            obj
        )

        return self.smart_save(

            destination_path,

            migrated,

        )

    # -----------------------------------------------------

    def register_identity_migration(
        self,
        version: str,
    ) -> None:
        """
        Register a no-op migration.

        Useful for testing.
        """

        self.register_migration(

            version,

            version,

            lambda data: data,

        )

    # -----------------------------------------------------

    def migration_history(
        self,
        source_version: str,
        target_version: str,
    ) -> List[str]:
        """
        Return visited versions during migration.
        """

        history = [source_version]

        for _, dst in self.find_migration_path(

            source_version,

            target_version,

        ):

            history.append(dst)

        return history

    # -----------------------------------------------------

    def verify_migration_chain(
        self,
        source_version: str,
        target_version: str,
    ) -> bool:
        """
        Verify every migration step exists.
        """

        path = self.find_migration_path(

            source_version,

            target_version,

        )

        return all(

            self.has_migration(src, dst)

            for src, dst in path

        )
# ============================================================
# Part 3.3D - File Version Management
# ============================================================

    def embed_version_metadata(
        self,
        data: Dict[str, Any],
        *,
        version: Optional[str] = None,
        schema_version: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Embed version metadata into a dictionary.

        Existing metadata is updated.
        """

        if version is None:
            version = self.current_version()

        if schema_version is None:
            schema_version = IO_SCHEMA_VERSION

        metadata = data.setdefault("_metadata", {})

        metadata.update({

            "version": version,

            "schema_version": schema_version,

            "created": datetime.now().isoformat(),

            "generator": "maya_faceit.io",

        })

        return data

    # -----------------------------------------------------

    def read_version_metadata(
        self,
        data: Mapping[str, Any],
    ) -> Dict[str, Any]:
        """
        Return embedded metadata.

        Missing values fall back to defaults.
        """

        metadata = dict(
            data.get("_metadata", {})
        )

        metadata.setdefault(
            "version",
            "1.0.0",
        )

        metadata.setdefault(
            "schema_version",
            1,
        )

        return metadata

    # -----------------------------------------------------

    def file_version(
        self,
        data: Mapping[str, Any],
    ) -> str:
        """
        Return the embedded file version.
        """

        return self.read_version_metadata(
            data
        )["version"]

    # -----------------------------------------------------

    def schema_version(
        self,
        data: Mapping[str, Any],
    ) -> int:
        """
        Return schema version.
        """

        return int(

            self.read_version_metadata(
                data
            )["schema_version"]

        )

    # -----------------------------------------------------

    def update_file_version(
        self,
        data: Dict[str, Any],
        version: str,
    ) -> Dict[str, Any]:
        """
        Update only the file version.
        """

        self.validate_version(version)

        metadata = data.setdefault(
            "_metadata",
            {},
        )

        metadata["version"] = version
        metadata["modified"] = (
            datetime.now().isoformat()
        )

        return data

    # -----------------------------------------------------

    def update_schema_version(
        self,
        data: Dict[str, Any],
        schema_version: int,
    ) -> Dict[str, Any]:
        """
        Update schema version.
        """

        metadata = data.setdefault(
            "_metadata",
            {},
        )

        metadata["schema_version"] = (
            int(schema_version)
        )

        metadata["modified"] = (
            datetime.now().isoformat()
        )

        return data

    # -----------------------------------------------------

    def remove_version_metadata(
        self,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Remove embedded metadata.
        """

        data.pop(
            "_metadata",
            None,
        )

        return data

    # -----------------------------------------------------

    def is_versioned_file(
        self,
        data: Mapping[str, Any],
    ) -> bool:
        """
        True if the object contains
        version metadata.
        """

        return "_metadata" in data

    # -----------------------------------------------------

    def is_legacy_file(
        self,
        data: Mapping[str, Any],
    ) -> bool:
        """
        Determine whether a file predates
        the current version.
        """

        return self.version_older(

            self.file_version(data),

            self.current_version(),

        )

    # -----------------------------------------------------

    def requires_migration(
        self,
        data: Mapping[str, Any],
    ) -> bool:
        """
        Determine whether migration is
        required.
        """

        return self.file_version(

            data

        ) != self.current_version()

    # -----------------------------------------------------

    def compatibility_report(
        self,
        data: Mapping[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate a compatibility report.
        """

        version = self.file_version(data)

        return {

            "file_version": version,

            "current_version":
                self.current_version(),

            "schema_version":
                self.schema_version(data),

            "compatible":
                self.compatible_version(version),

            "requires_migration":
                self.requires_migration(data),

            "legacy":
                self.is_legacy_file(data),

        }

    # -----------------------------------------------------

    def versioned_save(
        self,
        path: Union[str, Path],
        data: Dict[str, Any],
        *,
        compression: Optional[
            CompressionType
        ] = None,
    ) -> IOResult:
        """
        Embed metadata and save.
        """

        self.embed_version_metadata(
            data
        )

        return self.smart_save(

            path,

            data,

            compression=compression,

        )

    # -----------------------------------------------------

    def versioned_load(
        self,
        path: Union[str, Path],
        *,
        auto_migrate: bool = True,
    ) -> Dict[str, Any]:
        """
        Load a versioned file.

        Automatically migrates when
        requested.
        """

        data = self.smart_load(path)

        if (
            auto_migrate
            and
            self.requires_migration(data)
        ):

            data = self.auto_migrate(data)

        return data

    # -----------------------------------------------------

    def file_metadata_summary(
        self,
        data: Mapping[str, Any],
    ) -> str:
        """
        Human-readable metadata summary.
        """

        metadata = self.read_version_metadata(
            data
        )

        return (

            f"Version : "

            f"{metadata['version']}\n"

            f"Schema  : "

            f"{metadata['schema_version']}\n"

            f"Created : "

            f"{metadata.get('created', '-')}\n"

            f"Modified: "

            f"{metadata.get('modified', '-')}"

        )

    # -----------------------------------------------------

    def normalize_metadata(
        self,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Ensure metadata is complete and valid.
        """

        metadata = self.read_version_metadata(
            data
        )

        metadata.setdefault(
            "created",
            datetime.now().isoformat(),
        )

        metadata.setdefault(
            "generator",
            "maya_faceit.io",
        )

        data["_metadata"] = metadata

        return data

    # -----------------------------------------------------

    def validate_metadata(
        self,
        data: Mapping[str, Any],
    ) -> bool:
        """
        Validate embedded metadata.
        """

        metadata = self.read_version_metadata(
            data
        )

        self.validate_version(
            metadata["version"]
        )

        if metadata["schema_version"] < 1:

            raise VersionError(

                "Invalid schema version."

            )

        return True

    # -----------------------------------------------------

    def metadata_snapshot(
        self,
        data: Mapping[str, Any],
    ) -> Dict[str, Any]:
        """
        Return a deep copy of version metadata.
        """

        return copy.deepcopy(

            self.read_version_metadata(
                data
            )

        )
# ============================================================
# Part 3.3E - Backup, Rollback & Utilities
# ============================================================

    def migrate_with_backup(
        self,
        source_path: Union[str, Path],
        destination_path: Optional[Union[str, Path]] = None,
        *,
        backup: bool = True,
        auto_migrate: bool = True,
    ) -> IOResult:
        """
        Safely migrate a versioned file.

        A backup is created before any
        modifications are written.
        """

        source_path = self.normalize_path(source_path)

        if destination_path is None:

            destination_path = source_path

        else:

            destination_path = self.normalize_path(
                destination_path
            )

        backup_path = None

        if backup and source_path.exists():

            backup_path = self.create_backup(
                source_path
            )

        try:

            data = self.versioned_load(

                source_path,

                auto_migrate=auto_migrate,

            )

            result = self.versioned_save(

                destination_path,

                data,

            )

            if backup_path:

                result.metadata = result.metadata or {}

                result.metadata["backup"] = str(
                    backup_path
                )

            return result

        except Exception:

            if backup_path and destination_path.exists():

                shutil.copy2(

                    backup_path,

                    destination_path,

                )

            raise

    # -----------------------------------------------------

    def rollback_migration(
        self,
        backup_path: Union[str, Path],
        destination_path: Union[str, Path],
    ) -> IOResult:
        """
        Restore a file from a backup.
        """

        backup_path = self.normalize_path(
            backup_path
        )

        destination_path = self.normalize_path(
            destination_path
        )

        self.validate_file(backup_path)

        shutil.copy2(

            backup_path,

            destination_path,

        )

        return IOResult(

            status=IOStatus.SUCCESS,

            success=True,

            path=destination_path,

            format=FileFormat.BINARY,

        )

    # -----------------------------------------------------

    def dry_run_migration(
        self,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Simulate a migration without
        modifying the original object.
        """

        clone = copy.deepcopy(data)

        migrated = self.auto_migrate(
            clone
        )

        return {

            "original_version":
                self.file_version(data),

            "target_version":
                self.current_version(),

            "changed":
                migrated != data,

            "preview":
                migrated,

        }

    # -----------------------------------------------------

    def batch_migrate(
        self,
        files: Iterable[
            Union[str, Path]
        ],
        *,
        backup: bool = True,
    ) -> List[IOResult]:
        """
        Batch migrate multiple files.
        """

        results = []

        for path in files:

            try:

                results.append(

                    self.migrate_with_backup(

                        path,

                        backup=backup,

                    )

                )

            except Exception as exc:

                results.append(

                    IOResult(

                        status=IOStatus.ERROR,

                        success=False,

                        path=Path(path),

                        error=str(exc),

                    )

                )

        return results

    # -----------------------------------------------------

    def migration_statistics(
        self,
        files: Iterable[
            Union[str, Path]
        ],
    ) -> Dict[str, Any]:
        """
        Collect migration statistics.
        """

        total = 0

        migrated = 0

        already_current = 0

        failed = 0

        for path in files:

            total += 1

            try:

                data = self.smart_load(path)

                if self.requires_migration(data):

                    migrated += 1

                else:

                    already_current += 1

            except Exception:

                failed += 1

        return {

            "total": total,

            "requires_migration":
                migrated,

            "already_current":
                already_current,

            "failed":
                failed,

        }

    # -----------------------------------------------------

    def migration_log_entry(
        self,
        source_version: str,
        target_version: str,
        *,
        success: bool,
        message: str = "",
    ) -> Dict[str, Any]:
        """
        Create a migration log record.
        """

        return {

            "timestamp":
                datetime.now().isoformat(),

            "source":
                source_version,

            "target":
                target_version,

            "success":
                success,

            "message":
                message,

        }

    # -----------------------------------------------------

    def export_migration_report(
        self,
        report_path: Union[str, Path],
        report: Dict[str, Any],
    ) -> IOResult:
        """
        Save a migration report.
        """

        return self.atomic_save_json(

            report_path,

            report,

        )

    # -----------------------------------------------------

    def import_migration_report(
        self,
        report_path: Union[str, Path],
    ) -> Dict[str, Any]:
        """
        Load a migration report.
        """

        return self.load_json(
            report_path
        )

    # -----------------------------------------------------

    def verify_file_version(
        self,
        path: Union[str, Path],
        expected_version: str,
    ) -> bool:
        """
        Verify that a file is at the
        expected version.
        """

        data = self.versioned_load(

            path,

            auto_migrate=False,

        )

        return (

            self.file_version(data)

            ==

            expected_version

        )

    # -----------------------------------------------------

    def upgrade_if_required(
        self,
        path: Union[str, Path],
    ) -> bool:
        """
        Upgrade a file only if necessary.

        Returns
        -------
        True
            Migration performed.

        False
            Already current.
        """

        data = self.versioned_load(

            path,

            auto_migrate=False,

        )

        if not self.requires_migration(
            data
        ):

            return False

        self.migrate_with_backup(path)

        return True

    # -----------------------------------------------------

    def migration_health_check(
        self,
    ) -> Dict[str, Any]:
        """
        Validate migration subsystem.
        """

        registry = self.migration_registry_info()

        return {

            "current_version":
                self.current_version(),

            "schema":
                IO_SCHEMA_VERSION,

            "registered":
                registry["count"],

            "latest_registered":
                registry["latest"],

            "compatible":
                registry["latest"]
                == self.current_version(),

        }

    # -----------------------------------------------------

    def reset_migration_registry(
        self,
    ) -> None:
        """
        Remove every registered migration.
        """

        self.clear_migrations()

    # -----------------------------------------------------

    def migration_engine_summary(
        self,
    ) -> str:
        """
        Human-readable migration engine
        summary.
        """

        health = self.migration_health_check()

        return (
            "Migration Engine\n"
            "----------------\n"
            f"Current Version : "
            f"{health['current_version']}\n"
            f"Schema Version  : "
            f"{health['schema']}\n"
            f"Registered      : "
            f"{health['registered']}\n"
            f"Latest Registry : "
            f"{health['latest_registered']}\n"
            f"Healthy         : "
            f"{health['compatible']}"
        )
# ============================================================
# Part 3.4A - Autosave Foundation
# ============================================================

from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime, timedelta
import threading
import uuid

# ------------------------------------------------------------
# Autosave State
# ------------------------------------------------------------

class AutosaveState(Enum):
    """
    Current state of the autosave manager.
    """

    DISABLED = "disabled"
    IDLE = "idle"
    WAITING = "waiting"
    SAVING = "saving"
    PAUSED = "paused"
    RECOVERING = "recovering"
    ERROR = "error"


# ------------------------------------------------------------
# Autosave Policy
# ------------------------------------------------------------

@dataclass
class AutosavePolicy:
    """
    Configuration controlling autosave behavior.
    """

    enabled: bool = True

    interval_seconds: int = 300

    maximum_backups: int = 20

    compress: bool = True

    atomic: bool = True

    verify_after_save: bool = True

    create_backup: bool = False

    keep_daily: int = 7

    keep_weekly: int = 4

    keep_monthly: int = 12

    autosave_directory: Optional[Path] = None

    filename_prefix: str = "autosave"

    include_timestamp: bool = True

    use_versioning: bool = True


# ------------------------------------------------------------
# Autosave Entry
# ------------------------------------------------------------

@dataclass
class AutosaveEntry:
    """
    Represents one autosave.
    """

    identifier: str = field(
        default_factory=lambda: str(uuid.uuid4())
    )

    filename: str = ""

    path: Optional[Path] = None

    created: datetime = field(
        default_factory=datetime.now
    )

    size: int = 0

    checksum: str = ""

    version: str = ""

    compressed: bool = False

    successful: bool = True

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )


# ------------------------------------------------------------
# Autosave Manager Initialization
# ------------------------------------------------------------

    def initialize_autosave(
        self,
    ) -> None:
        """
        Initialize autosave subsystem.
        """

        self._autosave_policy = AutosavePolicy()

        self._autosave_state = (
            AutosaveState.IDLE
        )

        self._autosave_history: List[
            AutosaveEntry
        ] = []

        self._autosave_callbacks: List[
            Callable[[AutosaveEntry], None]
        ] = []

        self._autosave_timer = None

        self._autosave_last_save = None

        self._autosave_next_save = None

        self._autosave_dirty = False

        self._autosave_lock = threading.RLock()

        self._autosave_failures = 0

        self._autosave_successes = 0

        self._autosave_session_id = (
            str(uuid.uuid4())
        )

    # -----------------------------------------------------

    @property
    def autosave_policy(
        self,
    ) -> AutosavePolicy:
        """
        Return active autosave policy.
        """

        return self._autosave_policy

    # -----------------------------------------------------

    @property
    def autosave_state(
        self,
    ) -> AutosaveState:
        """
        Current autosave state.
        """

        return self._autosave_state

    # -----------------------------------------------------

    def set_autosave_directory(
        self,
        directory: Path,
    ) -> None:
        """
        Set autosave directory.
        """

        directory = self.normalize_path(
            directory
        )

        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._autosave_policy.autosave_directory = (
            directory
        )

    # -----------------------------------------------------

    def autosave_directory(
        self,
    ) -> Path:
        """
        Return autosave directory.
        """

        directory = (
            self._autosave_policy
            .autosave_directory
        )

        if directory is None:

            directory = (
                Path.cwd()
                / "autosaves"
            )

            directory.mkdir(
                parents=True,
                exist_ok=True,
            )

            self._autosave_policy.autosave_directory = (
                directory
            )

        return directory

    # -----------------------------------------------------

    def autosave_filename(
        self,
        extension: str = ".bin",
    ) -> str:
        """
        Generate an autosave filename.
        """

        prefix = (
            self._autosave_policy
            .filename_prefix
        )

        if (
            self._autosave_policy
            .include_timestamp
        ):

            stamp = datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            )

            return (
                f"{prefix}_{stamp}"
                f"{extension}"
            )

        return (
            f"{prefix}{extension}"
        )

    # -----------------------------------------------------

    def autosave_path(
        self,
        extension: str = ".bin",
    ) -> Path:
        """
        Full autosave path.
        """

        return (

            self.autosave_directory()

            /

            self.autosave_filename(
                extension
            )

        )

    # -----------------------------------------------------

    def mark_dirty(
        self,
    ) -> None:
        """
        Mark the session as modified.
        """

        self._autosave_dirty = True

    # -----------------------------------------------------

    def clear_dirty(
        self,
    ) -> None:
        """
        Clear modification flag.
        """

        self._autosave_dirty = False

    # -----------------------------------------------------

    def is_dirty(
        self,
    ) -> bool:
        """
        Whether unsaved changes exist.
        """

        return self._autosave_dirty

    # -----------------------------------------------------

    def last_autosave_time(
        self,
    ) -> Optional[datetime]:
        """
        Return timestamp of last autosave.
        """

        return self._autosave_last_save

    # -----------------------------------------------------

    def next_autosave_time(
        self,
    ) -> Optional[datetime]:
        """
        Scheduled next autosave.
        """

        return self._autosave_next_save

    # -----------------------------------------------------

    def autosave_interval(
        self,
    ) -> timedelta:
        """
        Configured autosave interval.
        """

        return timedelta(

            seconds=

            self._autosave_policy
            .interval_seconds

        )

    # -----------------------------------------------------

    def set_autosave_interval(
        self,
        seconds: int,
    ) -> None:
        """
        Change autosave interval.
        """

        if seconds <= 0:

            raise ValueError(
                "Interval must be positive."
            )

        self._autosave_policy.interval_seconds = (
            seconds
        )

    # -----------------------------------------------------

    def reset_autosave_statistics(
        self,
    ) -> None:
        """
        Reset runtime statistics.
        """

        self._autosave_successes = 0

        self._autosave_failures = 0

        self._autosave_history.clear()

        self._autosave_last_save = None

        self._autosave_next_save = None
# ============================================================
# Part 3.4B - Autosave Scheduling
# ============================================================

    def enable_autosave(self) -> None:
        """
        Enable autosave scheduling.
        """

        with self._autosave_lock:

            self._autosave_policy.enabled = True
            self._autosave_state = AutosaveState.IDLE

            self.schedule_next_autosave()

    # -----------------------------------------------------

    def disable_autosave(self) -> None:
        """
        Disable autosave scheduling.
        """

        with self._autosave_lock:

            self._autosave_policy.enabled = False
            self._autosave_state = AutosaveState.DISABLED

            self.cancel_autosave_timer()

    # -----------------------------------------------------

    def pause_autosave(self) -> None:
        """
        Pause autosave without disabling it.
        """

        with self._autosave_lock:

            if self._autosave_state == AutosaveState.PAUSED:
                return

            self.cancel_autosave_timer()

            self._autosave_state = AutosaveState.PAUSED

    # -----------------------------------------------------

    def resume_autosave(self) -> None:
        """
        Resume autosave scheduling.
        """

        with self._autosave_lock:

            if not self._autosave_policy.enabled:
                return

            self._autosave_state = AutosaveState.IDLE

            self.schedule_next_autosave()

    # -----------------------------------------------------

    def autosave_enabled(self) -> bool:
        """
        Whether autosave is enabled.
        """

        return self._autosave_policy.enabled

    # -----------------------------------------------------

    def schedule_next_autosave(self) -> Optional[datetime]:
        """
        Schedule the next autosave.
        """

        with self._autosave_lock:

            if not self.autosave_enabled():

                return None

            self.cancel_autosave_timer()

            interval = self.autosave_interval()

            self._autosave_next_save = (

                datetime.now()

                + interval

            )

            self._autosave_timer = threading.Timer(

                interval.total_seconds(),

                self._autosave_timer_callback,

            )

            self._autosave_timer.daemon = True

            self._autosave_timer.start()

            self._autosave_state = AutosaveState.WAITING

            return self._autosave_next_save

    # -----------------------------------------------------

    def cancel_autosave_timer(self) -> None:
        """
        Cancel the active timer.
        """

        timer = self._autosave_timer

        if timer is not None:

            timer.cancel()

            self._autosave_timer = None

    # -----------------------------------------------------

    def reschedule_autosave(self) -> None:
        """
        Restart the autosave timer.
        """

        if self.autosave_enabled():

            self.schedule_next_autosave()

    # -----------------------------------------------------

    def remaining_autosave_time(
        self,
    ) -> float:
        """
        Seconds until next autosave.
        """

        if self._autosave_next_save is None:

            return 0.0

        remaining = (

            self._autosave_next_save

            - datetime.now()

        ).total_seconds()

        return max(

            0.0,

            remaining,

        )

    # -----------------------------------------------------

    def autosave_due(self) -> bool:
        """
        Determine whether an autosave
        should occur now.
        """

        if not self.autosave_enabled():

            return False

        if self._autosave_state == AutosaveState.PAUSED:

            return False

        if self._autosave_next_save is None:

            return False

        return datetime.now() >= self._autosave_next_save

    # -----------------------------------------------------

    def should_autosave(self) -> bool:
        """
        Determine whether all autosave
        conditions are satisfied.
        """

        if not self.autosave_enabled():

            return False

        if self._autosave_state in (

            AutosaveState.SAVING,

            AutosaveState.PAUSED,

            AutosaveState.ERROR,

        ):

            return False

        if not self.is_dirty():

            return False

        return self.autosave_due()

    # -----------------------------------------------------

    def force_autosave(self) -> None:
        """
        Trigger an immediate autosave.
        """

        self.cancel_autosave_timer()

        self._autosave_next_save = datetime.now()

        self._autosave_timer_callback()

    # -----------------------------------------------------

    def touch_autosave(self) -> None:
        """
        Reset the autosave countdown
        without performing a save.
        """

        self.schedule_next_autosave()

    # -----------------------------------------------------

    def defer_autosave(
        self,
        seconds: int,
    ) -> None:
        """
        Delay the next autosave.
        """

        if seconds <= 0:

            return

        self.cancel_autosave_timer()

        self._autosave_next_save = (

            datetime.now()

            + timedelta(seconds=seconds)

        )

        self._autosave_timer = threading.Timer(

            seconds,

            self._autosave_timer_callback,

        )

        self._autosave_timer.daemon = True

        self._autosave_timer.start()

    # -----------------------------------------------------

    def autosave_status(
        self,
    ) -> Dict[str, Any]:
        """
        Runtime scheduling information.
        """

        return {

            "enabled":
                self.autosave_enabled(),

            "state":
                self.autosave_state.value,

            "dirty":
                self.is_dirty(),

            "last_save":
                self.last_autosave_time(),

            "next_save":
                self.next_autosave_time(),

            "remaining":
                self.remaining_autosave_time(),

        }

    # -----------------------------------------------------

    def _autosave_timer_callback(
        self,
    ) -> None:
        """
        Internal timer callback.
        """

        if self.should_autosave():

            self.perform_autosave()

        elif self.autosave_enabled():

            self.schedule_next_autosave()

    # -----------------------------------------------------

    def autosave_schedule_summary(
        self,
    ) -> str:
        """
        Human-readable scheduling summary.
        """

        status = self.autosave_status()

        return (
            "Autosave Scheduler\n"
            "------------------\n"
            f"Enabled   : {status['enabled']}\n"
            f"State     : {status['state']}\n"
            f"Dirty     : {status['dirty']}\n"
            f"Last Save : {status['last_save']}\n"
            f"Next Save : {status['next_save']}\n"
            f"Remaining : {status['remaining']:.1f} sec"
        )
# ============================================================
# Part 3.4C - Autosave Execution
# ============================================================

    def perform_autosave(
        self,
        obj: Optional[Any] = None,
    ) -> Optional[IOResult]:
        """
        Execute an autosave operation.

        Parameters
        ----------
        obj
            Optional object to save. If omitted,
            the active runtime object is requested.
        """

        with self._autosave_lock:

            if not self.autosave_enabled():

                return None

            if self._autosave_state == AutosaveState.SAVING:

                return None

            self._autosave_state = AutosaveState.SAVING

        try:

            if obj is None:

                obj = self.current_project_data()

            if obj is None:

                raise AutosaveError(
                    "Nothing available for autosave."
                )

            result = self.execute_autosave(obj)

            self._autosave_successes += 1

            self._autosave_failures = 0

            self._autosave_last_save = (
                datetime.now()
            )

            self.clear_dirty()

            self.schedule_next_autosave()

            self._autosave_state = (
                AutosaveState.IDLE
            )

            return result

        except Exception:

            self._autosave_failures += 1

            self._autosave_state = (
                AutosaveState.ERROR
            )

            raise

    # -----------------------------------------------------

    def execute_autosave(
        self,
        obj: Any,
    ) -> IOResult:
        """
        Internal autosave pipeline.
        """

        path = self.autosave_path(
            ".bin"
        )

        if (

            isinstance(obj, dict)

            and

            self._autosave_policy.use_versioning

        ):

            obj = self.embed_version_metadata(
                copy.deepcopy(obj)
            )

        result = self.smart_save(

            path,

            obj,

            compression=(

                self.default_compression()

                if self._autosave_policy.compress

                else CompressionType.NONE

            ),

            atomic=self._autosave_policy.atomic,

            create_backup=(
                self._autosave_policy.create_backup
            ),

        )

        entry = self.create_autosave_entry(
            result
        )

        self.record_autosave(entry)

        if self._autosave_policy.verify_after_save:

            self.verify_autosave(entry)

        self.fire_autosave_callbacks(
            entry
        )

        self.cleanup_autosaves()

        return result

    # -----------------------------------------------------

    def create_autosave_entry(
        self,
        result: IOResult,
    ) -> AutosaveEntry:
        """
        Create a history entry.
        """

        path = Path(result.path)

        return AutosaveEntry(

            filename=path.name,

            path=path,

            created=datetime.now(),

            size=path.stat().st_size,

            checksum=self.sha256(path),

            version=self.current_version(),

            compressed=(
                self._autosave_policy.compress
            ),

            successful=result.success,

        )

    # -----------------------------------------------------

    def record_autosave(
        self,
        entry: AutosaveEntry,
    ) -> None:
        """
        Record autosave history.
        """

        self._autosave_history.append(
            entry
        )

    # -----------------------------------------------------

    def verify_autosave(
        self,
        entry: AutosaveEntry,
    ) -> bool:
        """
        Verify autosave integrity.
        """

        if not entry.path.exists():

            raise AutosaveError(
                "Autosave file missing."
            )

        checksum = self.sha256(
            entry.path
        )

        if checksum != entry.checksum:

            raise AutosaveError(
                "Autosave checksum mismatch."
            )

        return True

    # -----------------------------------------------------

    def fire_autosave_callbacks(
        self,
        entry: AutosaveEntry,
    ) -> None:
        """
        Notify listeners.
        """

        for callback in list(

            self._autosave_callbacks

        ):

            try:

                callback(entry)

            except Exception:

                continue

    # -----------------------------------------------------

    def cleanup_autosaves(
        self,
    ) -> None:
        """
        Remove old autosaves exceeding
        the configured limit.
        """

        limit = (

            self._autosave_policy

            .maximum_backups

        )

        history = sorted(

            self._autosave_history,

            key=lambda x: x.created,

        )

        while len(history) > limit:

            oldest = history.pop(0)

            if (

                oldest.path

                and

                oldest.path.exists()

            ):

                oldest.path.unlink()

            self._autosave_history.remove(
                oldest
            )

    # -----------------------------------------------------

    def autosave_exists(
        self,
        entry: AutosaveEntry,
    ) -> bool:
        """
        Determine whether an autosave file
        still exists.
        """

        return (

            entry.path is not None

            and

            entry.path.exists()

        )

    # -----------------------------------------------------

    def autosave_count(
        self,
    ) -> int:
        """
        Number of recorded autosaves.
        """

        return len(

            self._autosave_history

        )

    # -----------------------------------------------------

    def latest_autosave(
        self,
    ) -> Optional[AutosaveEntry]:
        """
        Most recent autosave.
        """

        if not self._autosave_history:

            return None

        return max(

            self._autosave_history,

            key=lambda e: e.created,

        )

    # -----------------------------------------------------

    def autosave_success_rate(
        self,
    ) -> float:
        """
        Runtime success percentage.
        """

        total = (

            self._autosave_successes

            +

            self._autosave_failures

        )

        if total == 0:

            return 100.0

        return (

            self._autosave_successes

            / total

        ) * 100.0

    # -----------------------------------------------------

    def autosave_statistics(
        self,
    ) -> Dict[str, Any]:
        """
        Execution statistics.
        """

        return {

            "successes":
                self._autosave_successes,

            "failures":
                self._autosave_failures,

            "history":
                len(self._autosave_history),

            "success_rate":
                self.autosave_success_rate(),

            "last_save":
                self._autosave_last_save,

        }

    # -----------------------------------------------------

    def autosave_execution_summary(
        self,
    ) -> str:
        """
        Human-readable execution summary.
        """

        stats = self.autosave_statistics()

        return (
            "Autosave Execution\n"
            "------------------\n"
            f"Successes   : {stats['successes']}\n"
            f"Failures    : {stats['failures']}\n"
            f"History     : {stats['history']}\n"
            f"Success %   : {stats['success_rate']:.2f}\n"
            f"Last Save   : {stats['last_save']}"
        )
# ============================================================
# Part 3.4D - Autosave Recovery
# ============================================================

    def discover_autosaves(
        self,
    ) -> List[AutosaveEntry]:
        """
        Scan the autosave directory and rebuild the
        autosave registry.
        """

        entries: List[AutosaveEntry] = []

        directory = self.autosave_directory()

        if not directory.exists():

            return entries

        for path in sorted(
            directory.iterdir(),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        ):

            if not path.is_file():

                continue

            try:

                entry = AutosaveEntry(

                    filename=path.name,

                    path=path,

                    created=datetime.fromtimestamp(
                        path.stat().st_mtime
                    ),

                    size=path.stat().st_size,

                    checksum=self.sha256(path),

                    version=self.current_version(),

                    compressed=(
                        path.suffix
                        in {
                            ".gz",
                            ".bz2",
                            ".xz",
                            ".zip",
                        }
                    ),

                )

                entries.append(entry)

            except Exception:

                continue

        self._autosave_history = entries

        return entries

    # -----------------------------------------------------

    def latest_recoverable_autosave(
        self,
    ) -> Optional[AutosaveEntry]:
        """
        Return the newest valid autosave.
        """

        entries = self.discover_autosaves()

        if not entries:

            return None

        return entries[0]

    # -----------------------------------------------------

    def recover_latest_autosave(
        self,
    ) -> Any:
        """
        Load the newest autosave.
        """

        entry = self.latest_recoverable_autosave()

        if entry is None:

            raise AutosaveError(
                "No autosaves available."
            )

        self._autosave_state = (
            AutosaveState.RECOVERING
        )

        try:

            data = self.smart_load(
                entry.path
            )

            self._autosave_state = (
                AutosaveState.IDLE
            )

            return data

        except Exception:

            self._autosave_state = (
                AutosaveState.ERROR
            )

            raise

    # -----------------------------------------------------

    def recover_autosave(
        self,
        entry: AutosaveEntry,
    ) -> Any:
        """
        Recover a specific autosave.
        """

        if not self.autosave_exists(entry):

            raise AutosaveError(
                "Autosave does not exist."
            )

        return self.smart_load(
            entry.path
        )

    # -----------------------------------------------------

    def restore_autosave(
        self,
        entry: AutosaveEntry,
        destination: Union[str, Path],
    ) -> IOResult:
        """
        Restore an autosave to a destination.
        """

        destination = self.normalize_path(
            destination
        )

        shutil.copy2(
            entry.path,
            destination,
        )

        return IOResult(

            status=IOStatus.SUCCESS,

            success=True,

            path=destination,

            format=FileFormat.BINARY,

        )

    # -----------------------------------------------------

    def verify_autosave_history(
        self,
    ) -> Dict[str, bool]:
        """
        Verify every autosave on disk.
        """

        results = {}

        for entry in self.discover_autosaves():

            try:

                results[entry.filename] = (
                    self.verify_autosave(
                        entry
                    )
                )

            except Exception:

                results[entry.filename] = False

        return results

    # -----------------------------------------------------

    def remove_autosave(
        self,
        entry: AutosaveEntry,
    ) -> bool:
        """
        Remove one autosave.
        """

        if (
            entry.path
            and
            entry.path.exists()
        ):

            entry.path.unlink()

        if entry in self._autosave_history:

            self._autosave_history.remove(
                entry
            )

        return True

    # -----------------------------------------------------

    def purge_autosaves(
        self,
    ) -> int:
        """
        Remove every autosave.
        """

        removed = 0

        for entry in list(
            self._autosave_history
        ):

            try:

                self.remove_autosave(
                    entry
                )

                removed += 1

            except Exception:

                pass

        return removed

    # -----------------------------------------------------

    def cleanup_expired_autosaves(
        self,
        *,
        older_than_days: int = 30,
    ) -> int:
        """
        Remove autosaves older than the
        specified age.
        """

        cutoff = datetime.now() - timedelta(
            days=older_than_days
        )

        removed = 0

        for entry in list(
            self._autosave_history
        ):

            if entry.created < cutoff:

                try:

                    self.remove_autosave(
                        entry
                    )

                    removed += 1

                except Exception:

                    pass

        return removed

    # -----------------------------------------------------

    def recovery_report(
        self,
    ) -> Dict[str, Any]:
        """
        Generate a recovery report.
        """

        entries = self.discover_autosaves()

        latest = (
            entries[0]
            if entries
            else None
        )

        return {

            "available":

                len(entries),

            "latest":

                latest.filename
                if latest
                else None,

            "latest_time":

                latest.created.isoformat()
                if latest
                else None,

            "directory":

                str(
                    self.autosave_directory()
                ),

            "state":

                self.autosave_state.value,

        }

    # -----------------------------------------------------

    def crash_recovery_available(
        self,
    ) -> bool:
        """
        Determine whether crash recovery
        data exists.
        """

        return (

            self.latest_recoverable_autosave()

            is not None

        )

    # -----------------------------------------------------

    def perform_crash_recovery(
        self,
    ) -> Any:
        """
        Perform automatic crash recovery.
        """

        if not self.crash_recovery_available():

            raise AutosaveError(
                "No recovery data found."
            )

        return self.recover_latest_autosave()

    # -----------------------------------------------------

    def recovery_summary(
        self,
    ) -> str:
        """
        Human-readable recovery summary.
        """

        report = self.recovery_report()

        return (
            "Autosave Recovery\n"
            "-----------------\n"
            f"Available : "
            f"{report['available']}\n"
            f"Latest    : "
            f"{report['latest']}\n"
            f"Created   : "
            f"{report['latest_time']}\n"
            f"Directory : "
            f"{report['directory']}\n"
            f"State     : "
            f"{report['state']}"
        )
# ============================================================
# Part 3.4E - Monitoring & Utilities
# ============================================================

    # -----------------------------------------------------
    # Callback Registration
    # -----------------------------------------------------

    def add_autosave_callback(
        self,
        callback: Callable[[AutosaveEntry], None],
    ) -> None:
        """
        Register an autosave callback.
        """

        if callback not in self._autosave_callbacks:

            self._autosave_callbacks.append(
                callback
            )

    # -----------------------------------------------------

    def remove_autosave_callback(
        self,
        callback: Callable[[AutosaveEntry], None],
    ) -> bool:
        """
        Remove a registered callback.
        """

        if callback in self._autosave_callbacks:

            self._autosave_callbacks.remove(
                callback
            )

            return True

        return False

    # -----------------------------------------------------

    def clear_autosave_callbacks(
        self,
    ) -> None:
        """
        Remove all registered callbacks.
        """

        self._autosave_callbacks.clear()

    # -----------------------------------------------------
    # History
    # -----------------------------------------------------

    def autosave_history(
        self,
    ) -> List[AutosaveEntry]:
        """
        Return autosave history.
        """

        return list(
            self._autosave_history
        )

    # -----------------------------------------------------

    def autosave_history_count(
        self,
    ) -> int:
        """
        Number of autosave records.
        """

        return len(
            self._autosave_history
        )

    # -----------------------------------------------------

    def clear_autosave_history(
        self,
    ) -> None:
        """
        Clear in-memory history.
        """

        self._autosave_history.clear()

    # -----------------------------------------------------

    def successful_autosaves(
        self,
    ) -> List[AutosaveEntry]:
        """
        Return successful autosaves.
        """

        return [

            entry

            for entry in self._autosave_history

            if entry.successful

        ]

    # -----------------------------------------------------

    def failed_autosaves(
        self,
    ) -> List[AutosaveEntry]:
        """
        Return failed autosaves.
        """

        return [

            entry

            for entry in self._autosave_history

            if not entry.successful

        ]

    # -----------------------------------------------------
    # Health Monitoring
    # -----------------------------------------------------

    def autosave_health(
        self,
    ) -> Dict[str, Any]:
        """
        Health information for the autosave system.
        """

        latest = self.latest_autosave()

        return {

            "enabled":
                self.autosave_enabled(),

            "state":
                self.autosave_state.value,

            "healthy":
                self._autosave_failures == 0,

            "last_save":

                latest.created.isoformat()

                if latest

                else None,

            "history":
                len(self._autosave_history),

            "successes":
                self._autosave_successes,

            "failures":
                self._autosave_failures,

            "success_rate":
                self.autosave_success_rate(),

        }

    # -----------------------------------------------------

    def autosave_is_healthy(
        self,
    ) -> bool:
        """
        True when the autosave subsystem
        is operating normally.
        """

        return (

            self._autosave_failures == 0

            and

            self.autosave_enabled()

        )

    # -----------------------------------------------------
    # Diagnostics
    # -----------------------------------------------------

    def autosave_diagnostics(
        self,
    ) -> Dict[str, Any]:
        """
        Complete autosave diagnostics.
        """

        return {

            "policy":
                asdict(
                    self._autosave_policy
                ),

            "health":
                self.autosave_health(),

            "scheduler":
                self.autosave_status(),

            "execution":
                self.autosave_statistics(),

            "recovery":
                self.recovery_report(),

        }

    # -----------------------------------------------------

    def autosave_report(
        self,
    ) -> Dict[str, Any]:
        """
        Comprehensive autosave report.
        """

        return {

            "generated":

                datetime.now().isoformat(),

            "session":

                self._autosave_session_id,

            "diagnostics":

                self.autosave_diagnostics(),

            "history_count":

                len(self._autosave_history),

        }

    # -----------------------------------------------------

    def export_autosave_report(
        self,
        path: Union[str, Path],
    ) -> IOResult:
        """
        Export diagnostics report.
        """

        return self.save_json(

            path,

            self.autosave_report(),

        )

    # -----------------------------------------------------
    # Batch Utilities
    # -----------------------------------------------------

    def batch_autosave(
        self,
        objects: Iterable[Any],
    ) -> List[IOResult]:
        """
        Autosave multiple objects.
        """

        results = []

        for obj in objects:

            try:

                results.append(

                    self.perform_autosave(
                        obj
                    )

                )

            except Exception as exc:

                results.append(

                    IOResult(

                        success=False,

                        status=IOStatus.ERROR,

                        error=str(exc),

                    )

                )

        return results

    # -----------------------------------------------------

    def autosave_summary(
        self,
    ) -> str:
        """
        Human-readable autosave summary.
        """

        health = self.autosave_health()

        return (
            "Autosave Manager\n"
            "================\n"
            f"Enabled      : {health['enabled']}\n"
            f"State        : {health['state']}\n"
            f"Healthy      : {health['healthy']}\n"
            f"History      : {health['history']}\n"
            f"Successes    : {health['successes']}\n"
            f"Failures     : {health['failures']}\n"
            f"Success Rate : "
            f"{health['success_rate']:.2f}%\n"
            f"Last Save    : "
            f"{health['last_save']}"
        )

    # -----------------------------------------------------
    # Context Manager
    # -----------------------------------------------------

    @contextmanager
    def autosave_paused(
        self,
    ):
        """
        Temporarily pause autosave.

        Example
        -------
        with io.autosave_paused():
            perform_large_operation()
        """

        previous_state = self.autosave_enabled()

        self.pause_autosave()

        try:

            yield

        finally:

            if previous_state:

                self.resume_autosave()

    # -----------------------------------------------------

    def shutdown_autosave(
        self,
    ) -> None:
        """
        Shutdown the autosave subsystem.
        """

        self.cancel_autosave_timer()

        self.clear_autosave_callbacks()

        self._autosave_state = (
            AutosaveState.DISABLED
        )
# ============================================================
# Part 3.5A - High-Level I/O APIs
# ============================================================

    def load(
        self,
        path: Union[str, Path],
        *,
        auto_migrate: bool = True,
    ) -> Any:
        """
        High-level load API.

        Automatically detects file format and
        optionally performs version migration.
        """

        data = self.smart_load(path)

        if (
            auto_migrate
            and
            isinstance(data, dict)
            and
            self.is_versioned_file(data)
            and
            self.requires_migration(data)
        ):

            data = self.auto_migrate(data)

        return data

    # -----------------------------------------------------

    def save(
        self,
        path: Union[str, Path],
        data: Any,
        *,
        compression: Optional[CompressionType] = None,
        versioned: bool = True,
    ) -> IOResult:
        """
        High-level save API.
        """

        payload = data

        if (
            versioned
            and
            isinstance(payload, dict)
        ):

            payload = copy.deepcopy(payload)

            self.embed_version_metadata(
                payload
            )

        return self.smart_save(

            path,

            payload,

            compression=compression,

        )

    # -----------------------------------------------------

    def import_file(
        self,
        path: Union[str, Path],
    ) -> Any:
        """
        Generic import API.
        """

        return self.load(path)

    # -----------------------------------------------------

    def export_file(
        self,
        path: Union[str, Path],
        data: Any,
    ) -> IOResult:
        """
        Generic export API.
        """

        return self.save(
            path,
            data,
        )

    # -----------------------------------------------------

    def load_project(
        self,
        path: Union[str, Path],
    ) -> Dict[str, Any]:
        """
        Load a project file.
        """

        project = self.load(path)

        if not isinstance(project, dict):

            raise IOError(
                "Project must be a dictionary."
            )

        return project

    # -----------------------------------------------------

    def save_project(
        self,
        path: Union[str, Path],
        project: Dict[str, Any],
    ) -> IOResult:
        """
        Save a project.
        """

        return self.save(

            path,

            project,

            versioned=True,

        )

    # -----------------------------------------------------

    def load_preset(
        self,
        path: Union[str, Path],
    ) -> Dict[str, Any]:
        """
        Load a preset.
        """

        preset = self.load(path)

        if not isinstance(
            preset,
            dict,
        ):

            raise IOError(
                "Preset must be a dictionary."
            )

        return preset

    # -----------------------------------------------------

    def save_preset(
        self,
        path: Union[str, Path],
        preset: Dict[str, Any],
    ) -> IOResult:
        """
        Save a preset.
        """

        return self.save(

            path,

            preset,

            versioned=True,

        )

    # -----------------------------------------------------

    def load_runtime_snapshot(
        self,
        path: Union[str, Path],
    ) -> Dict[str, Any]:
        """
        Load a runtime snapshot.
        """

        snapshot = self.load(path)

        if not isinstance(
            snapshot,
            dict,
        ):

            raise IOError(
                "Invalid runtime snapshot."
            )

        return snapshot

    # -----------------------------------------------------

    def save_runtime_snapshot(
        self,
        path: Union[str, Path],
        snapshot: Dict[str, Any],
    ) -> IOResult:
        """
        Save a runtime snapshot.
        """

        return self.save(

            path,

            snapshot,

            versioned=True,

        )

    # -----------------------------------------------------

    def load_mapping(
        self,
        path: Union[str, Path],
    ) -> Dict[str, Any]:
        """
        Load an ARKit mapping.
        """

        mapping = self.load(path)

        if not isinstance(
            mapping,
            dict,
        ):

            raise IOError(
                "Invalid mapping."
            )

        return mapping

    # -----------------------------------------------------

    def save_mapping(
        self,
        path: Union[str, Path],
        mapping: Dict[str, Any],
    ) -> IOResult:
        """
        Save an ARKit mapping.
        """

        return self.save(

            path,

            mapping,

            versioned=True,

        )

    # -----------------------------------------------------

    def duplicate_file(
        self,
        source: Union[str, Path],
        destination: Union[str, Path],
    ) -> IOResult:
        """
        Duplicate a managed file.
        """

        data = self.load(source)

        return self.save(
            destination,
            data,
        )

    # -----------------------------------------------------

    def convert_file(
        self,
        source: Union[str, Path],
        destination: Union[str, Path],
    ) -> IOResult:
        """
        Convert between supported formats.
        """

        data = self.load(
            source,
        )

        return self.save(
            destination,
            data,
        )

    # -----------------------------------------------------

    def quick_export(
        self,
        data: Any,
        directory: Union[str, Path],
        filename: str,
    ) -> IOResult:
        """
        Export using a directory and filename.
        """

        directory = self.normalize_path(
            directory
        )

        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        return self.save(

            directory / filename,

            data,

        )

    # -----------------------------------------------------

    def quick_import(
        self,
        directory: Union[str, Path],
        filename: str,
    ) -> Any:
        """
        Import using a directory and filename.
        """

        directory = self.normalize_path(
            directory
        )

        return self.load(
            directory / filename
        )

    # -----------------------------------------------------

    def open_recent(
        self,
    ) -> Any:
        """
        Open the most recently used file.

        Requires the application to maintain
        '_recent_file'.
        """

        if not hasattr(
            self,
            "_recent_file",
        ):

            raise IOError(
                "No recent file available."
            )

        return self.load(
            self._recent_file
        )

    # -----------------------------------------------------

    def save_recent(
        self,
        data: Any,
    ) -> IOResult:
        """
        Save to the most recently used file.
        """

        if not hasattr(
            self,
            "_recent_file",
        ):

            raise IOError(
                "No recent file available."
            )

        return self.save(
            self._recent_file,
            data,
        )

    # -----------------------------------------------------

    def remember_recent_file(
        self,
        path: Union[str, Path],
    ) -> None:
        """
        Store the most recently used file.
        """

        self._recent_file = (
            self.normalize_path(path)
        )
# ============================================================
# Part 3.5B - Session Management
# ============================================================

    def initialize(self) -> None:
        """
        Initialize the I/O manager and all supported subsystems.

        This method is safe to call multiple times.
        """

        if getattr(self, "_initialized", False):
            return

        self.initialize_migration_registry()
        self.initialize_autosave()

        self._session_started = datetime.now()
        self._session_identifier = str(uuid.uuid4())
        self._initialized = True
        self._shutdown = False

    # -----------------------------------------------------

    def shutdown(self) -> None:
        """
        Gracefully shut down the I/O manager.
        """

        if not getattr(self, "_initialized", False):
            return

        try:
            self.flush()

        finally:
            self.shutdown_autosave()

            self._shutdown = True
            self._initialized = False

    # -----------------------------------------------------

    def reset(self) -> None:
        """
        Reset the runtime state while preserving configuration.
        """

        self.cancel_autosave_timer()

        self.clear_autosave_history()
        self.clear_autosave_callbacks()

        self._autosave_successes = 0
        self._autosave_failures = 0

        self._recent_file = None

        self._session_started = datetime.now()
        self._session_identifier = str(uuid.uuid4())

        self._autosave_state = AutosaveState.IDLE

    # -----------------------------------------------------

    def reload(self) -> None:
        """
        Reload the manager.

        Equivalent to shutdown followed by initialize.
        """

        self.shutdown()
        self.initialize()

    # -----------------------------------------------------

    def close(self) -> None:
        """
        Alias for shutdown().
        """

        self.shutdown()

    # -----------------------------------------------------

    def flush(self) -> None:
        """
        Flush pending runtime data.

        If autosave is enabled and unsaved changes exist,
        perform one final autosave.
        """

        if (
            self.autosave_enabled()
            and
            self.is_dirty()
        ):
            try:
                self.perform_autosave()
            except Exception:
                pass

    # -----------------------------------------------------

    def cleanup(self) -> None:
        """
        Cleanup temporary runtime resources.
        """

        self.cancel_autosave_timer()

        self.cleanup_expired_autosaves()

    # -----------------------------------------------------

    def restart_autosave(self) -> None:
        """
        Restart autosave scheduling.
        """

        self.cancel_autosave_timer()

        if self.autosave_enabled():

            self.schedule_next_autosave()

    # -----------------------------------------------------

    def session_duration(self) -> timedelta:
        """
        Return elapsed session duration.
        """

        started = getattr(
            self,
            "_session_started",
            datetime.now(),
        )

        return datetime.now() - started

    # -----------------------------------------------------

    def session_identifier(self) -> str:
        """
        Return the current session identifier.
        """

        return getattr(
            self,
            "_session_identifier",
            "",
        )

    # -----------------------------------------------------

    def session_active(self) -> bool:
        """
        Whether the manager is currently active.
        """

        return (
            getattr(self, "_initialized", False)
            and
            not getattr(self, "_shutdown", False)
        )

    # -----------------------------------------------------

    def session_summary(self) -> Dict[str, Any]:
        """
        Runtime session information.
        """

        return {

            "session_id":
                self.session_identifier(),

            "started":
                self._session_started,

            "duration":
                str(self.session_duration()),

            "initialized":
                getattr(
                    self,
                    "_initialized",
                    False,
                ),

            "shutdown":
                getattr(
                    self,
                    "_shutdown",
                    False,
                ),

            "autosave":
                self.autosave_enabled(),

            "dirty":
                self.is_dirty(),

            "recent_file":
                str(self._recent_file)
                if getattr(
                    self,
                    "_recent_file",
                    None,
                )
                else None,

        }

    # -----------------------------------------------------

    @contextmanager
    def session(self):
        """
        Session context manager.

        Example
        -------
        with io.session():
            ...
        """

        self.initialize()

        try:

            yield self

        finally:

            self.shutdown()

    # -----------------------------------------------------

    def ensure_initialized(self) -> None:
        """
        Ensure the manager has been initialized.
        """

        if not getattr(
            self,
            "_initialized",
            False,
        ):
            self.initialize()

    # -----------------------------------------------------

    def require_active_session(self) -> None:
        """
        Raise if no active session exists.
        """

        if not self.session_active():

            raise RuntimeError(
                "I/O manager session is not active."
            )

    # -----------------------------------------------------

    def session_report(self) -> str:
        """
        Human-readable session report.
        """

        info = self.session_summary()

        return (
            "I/O Session\n"
            "===========\n"
            f"Session ID   : {info['session_id']}\n"
            f"Started      : {info['started']}\n"
            f"Duration     : {info['duration']}\n"
            f"Initialized  : {info['initialized']}\n"
            f"Shutdown     : {info['shutdown']}\n"
            f"Autosave     : {info['autosave']}\n"
            f"Dirty        : {info['dirty']}\n"
            f"Recent File  : {info['recent_file']}"
        )

    # -----------------------------------------------------

    def dispose(self) -> None:
        """
        Dispose of the manager.

        Alias for shutdown() to support
        common resource-management APIs.
        """

        self.shutdown()
# ============================================================
# Part 3.5C - Diagnostics & Validation
# ============================================================

    def validate_configuration(self) -> bool:
        """
        Validate the current I/O manager configuration.

        Raises
        ------
        ValueError
            If any configuration value is invalid.
        """

        policy = self.autosave_policy

        if policy.interval_seconds <= 0:
            raise ValueError(
                "Autosave interval must be greater than zero."
            )

        if policy.maximum_backups < 1:
            raise ValueError(
                "maximum_backups must be at least 1."
            )

        if policy.autosave_directory is not None:

            directory = Path(policy.autosave_directory)

            if (
                directory.exists()
                and
                not directory.is_dir()
            ):
                raise ValueError(
                    "Autosave path is not a directory."
                )

        return True

    # -----------------------------------------------------

    def validate_environment(self) -> Dict[str, bool]:
        """
        Validate the runtime environment.
        """

        results = {

            "configuration":
                False,

            "autosave_directory":
                False,

            "migration":
                False,

            "compression":
                False,

            "hashing":
                False,

        }

        try:

            results["configuration"] = (
                self.validate_configuration()
            )

        except Exception:

            pass

        try:

            directory = self.autosave_directory()

            directory.mkdir(
                parents=True,
                exist_ok=True,
            )

            results[
                "autosave_directory"
            ] = directory.exists()

        except Exception:

            pass

        try:

            self.migration_health_check()

            results["migration"] = True

        except Exception:

            pass

        try:

            self.default_compression()

            results["compression"] = True

        except Exception:

            pass

        try:

            hashlib.sha256(b"test")

            results["hashing"] = True

        except Exception:

            pass

        return results

    # -----------------------------------------------------

    def self_test(
        self,
    ) -> Dict[str, Any]:
        """
        Execute a lightweight self-test of the
        I/O subsystem.
        """

        report = {

            "timestamp":
                datetime.now().isoformat(),

            "tests": {},

            "passed": True,

        }

        tests = report["tests"]

        for name, func in (

            ("environment",
             self.validate_environment),

            ("configuration",
             self.validate_configuration),

            ("migration",
             self.migration_health_check),

            ("autosave",
             self.autosave_health),

        ):

            try:

                func()

                tests[name] = "PASS"

            except Exception as exc:

                tests[name] = str(exc)

                report["passed"] = False

        return report

    # -----------------------------------------------------

    def diagnostics(
        self,
    ) -> Dict[str, Any]:
        """
        Collect diagnostics from all major
        subsystems.
        """

        return {

            "session":
                self.session_summary(),

            "autosave":
                self.autosave_health(),

            "migration":
                self.migration_health_check(),

            "environment":
                self.validate_environment(),

            "statistics":
                self.autosave_statistics(),

        }

    # -----------------------------------------------------

    def runtime_summary(
        self,
    ) -> Dict[str, Any]:
        """
        Runtime status summary.
        """

        return {

            "initialized":
                getattr(
                    self,
                    "_initialized",
                    False,
                ),

            "session_active":
                self.session_active(),

            "autosave_enabled":
                self.autosave_enabled(),

            "dirty":
                self.is_dirty(),

            "current_version":
                self.current_version(),

            "schema_version":
                IO_SCHEMA_VERSION,

        }

    # -----------------------------------------------------

    def feature_report(
        self,
    ) -> Dict[str, bool]:
        """
        Report supported features.
        """

        return {

            "json": True,

            "yaml": True,

            "csv": True,

            "binary": True,

            "compression": True,

            "atomic_save": True,

            "migration": True,

            "versioning": True,

            "autosave": True,

            "checksums": True,

            "backups": True,

        }

    # -----------------------------------------------------

    def environment_report(
        self,
    ) -> Dict[str, Any]:
        """
        Report runtime environment details.
        """

        return {

            "python":
                sys.version,

            "platform":
                platform.platform(),

            "cwd":
                str(Path.cwd()),

            "session":

                self.session_identifier(),

            "started":

                str(self._session_started),

        }

    # -----------------------------------------------------

    def health_check(
        self,
    ) -> bool:
        """
        Overall subsystem health.
        """

        return (

            self.validate_configuration()

            and

            self.autosave_is_healthy()

            and

            self.migration_health_check()[
                "compatible"
            ]

        )

    # -----------------------------------------------------

    def diagnostics_report(
        self,
    ) -> str:
        """
        Human-readable diagnostics report.
        """

        runtime = self.runtime_summary()

        health = self.health_check()

        return (
            "I/O Diagnostics\n"
            "===============\n"
            f"Healthy        : {health}\n"
            f"Initialized    : {runtime['initialized']}\n"
            f"Session Active : {runtime['session_active']}\n"
            f"Autosave       : {runtime['autosave_enabled']}\n"
            f"Dirty          : {runtime['dirty']}\n"
            f"Version        : {runtime['current_version']}\n"
            f"Schema         : {runtime['schema_version']}"
        )

    # -----------------------------------------------------

    def verify_installation(
        self,
    ) -> bool:
        """
        Verify that the I/O subsystem is
        correctly installed.
        """

        report = self.self_test()

        return report["passed"]

    # -----------------------------------------------------

    def assert_healthy(
        self,
    ) -> None:
        """
        Raise if the subsystem is unhealthy.
        """

        if not self.health_check():

            raise RuntimeError(
                "I/O subsystem health check failed."
            )
# ============================================================
# Part 3.5D - Statistics & Reporting
# ============================================================

    def io_statistics(
        self,
    ) -> Dict[str, Any]:
        """
        Return aggregate I/O statistics.
        """

        autosave = self.autosave_statistics()

        return {

            "session_id":
                self.session_identifier(),

            "session_duration":
                str(
                    self.session_duration()
                ),

            "autosave":

                autosave,

            "migration":

                self.migration_health_check(),

            "history":

                self.autosave_history_count(),

            "dirty":

                self.is_dirty(),

        }

    # -----------------------------------------------------

    def operation_history(
        self,
    ) -> List[Dict[str, Any]]:
        """
        Return a simplified history of all
        recorded autosave operations.
        """

        history = []

        for entry in self.autosave_history():

            history.append({

                "id":
                    entry.identifier,

                "filename":
                    entry.filename,

                "created":
                    entry.created.isoformat(),

                "size":
                    entry.size,

                "successful":
                    entry.successful,

                "version":
                    entry.version,

            })

        return history

    # -----------------------------------------------------

    def export_statistics(
        self,
        path: Union[str, Path],
    ) -> IOResult:
        """
        Export runtime statistics as JSON.
        """

        payload = {

            "generated":

                datetime.now().isoformat(),

            "statistics":

                self.io_statistics(),

            "history":

                self.operation_history(),

        }

        return self.save_json(
            path,
            payload,
        )

    # -----------------------------------------------------

    def import_statistics(
        self,
        path: Union[str, Path],
    ) -> Dict[str, Any]:
        """
        Import previously exported statistics.
        """

        return self.load_json(
            path
        )

    # -----------------------------------------------------

    def statistics_summary(
        self,
    ) -> Dict[str, Any]:
        """
        Compact statistics summary.
        """

        stats = self.io_statistics()

        autosave = stats["autosave"]

        return {

            "uptime":

                stats["session_duration"],

            "autosaves":

                autosave["successes"],

            "failures":

                autosave["failures"],

            "success_rate":

                autosave["success_rate"],

            "history":

                stats["history"],

        }

    # -----------------------------------------------------

    def report(
        self,
    ) -> Dict[str, Any]:
        """
        Complete subsystem report.
        """

        return {

            "timestamp":

                datetime.now().isoformat(),

            "runtime":

                self.runtime_summary(),

            "session":

                self.session_summary(),

            "diagnostics":

                self.diagnostics(),

            "statistics":

                self.io_statistics(),

            "history":

                self.operation_history(),

            "features":

                self.feature_report(),

        }

    # -----------------------------------------------------

    def export_report(
        self,
        path: Union[str, Path],
    ) -> IOResult:
        """
        Export the complete subsystem report.
        """

        return self.save_json(

            path,

            self.report(),

        )

    # -----------------------------------------------------

    def report_as_text(
        self,
    ) -> str:
        """
        Human-readable report.
        """

        summary = self.statistics_summary()

        return (
            "I/O Manager Report\n"
            "==================\n"
            f"Uptime          : "
            f"{summary['uptime']}\n"
            f"Autosaves       : "
            f"{summary['autosaves']}\n"
            f"Failures        : "
            f"{summary['failures']}\n"
            f"Success Rate    : "
            f"{summary['success_rate']:.2f}%\n"
            f"History Entries : "
            f"{summary['history']}"
        )

    # -----------------------------------------------------

    def print_report(
        self,
    ) -> None:
        """
        Print the current report.
        """

        print(
            self.report_as_text()
        )

    # -----------------------------------------------------

    def export_history(
        self,
        path: Union[str, Path],
    ) -> IOResult:
        """
        Export operation history.
        """

        return self.save_json(

            path,

            self.operation_history(),

        )

    # -----------------------------------------------------

    def clear_statistics(
        self,
    ) -> None:
        """
        Reset runtime statistics while preserving
        configuration.
        """

        self.reset_autosave_statistics()

    # -----------------------------------------------------

    def statistics_available(
        self,
    ) -> bool:
        """
        Return True if runtime statistics
        are available.
        """

        return (

            self.autosave_history_count()

            >

            0

        )

    # -----------------------------------------------------

    def statistics_report(
        self,
    ) -> str:
        """
        Detailed statistics report.
        """

        stats = self.io_statistics()

        auto = stats["autosave"]

        return (
            "Statistics\n"
            "==========\n"
            f"Session ID     : "
            f"{stats['session_id']}\n"
            f"Duration       : "
            f"{stats['session_duration']}\n"
            f"Autosaves      : "
            f"{auto['successes']}\n"
            f"Failures       : "
            f"{auto['failures']}\n"
            f"Success Rate   : "
            f"{auto['success_rate']:.2f}%\n"
            f"History        : "
            f"{stats['history']}\n"
            f"Dirty          : "
            f"{stats['dirty']}"
        )

    # -----------------------------------------------------

    def generate_report(
        self,
        *,
        include_history: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate a configurable report.
        """

        report = {

            "generated":

                datetime.now().isoformat(),

            "runtime":

                self.runtime_summary(),

            "statistics":

                self.io_statistics(),

        }

        if include_history:

            report["history"] = (

                self.operation_history()

            )

        return report
# ============================================================
# Part 3.5E - Utilities & Factory APIs
# ============================================================

    # -----------------------------------------------------
    # Object Utilities
    # -----------------------------------------------------

    def clone(self) -> "IOManager":
        """
        Create a deep copy of this manager.

        Runtime-only resources such as locks and timers
        are reinitialized in the cloned instance.
        """

        clone = copy.deepcopy(self)

        clone._autosave_lock = threading.RLock()
        clone._autosave_timer = None
        clone._initialized = False
        clone._shutdown = False

        clone.initialize()

        return clone

    # -----------------------------------------------------

    def copy_configuration(
        self,
        other: "IOManager",
    ) -> None:
        """
        Copy configuration from another IOManager.
        """

        self._autosave_policy = copy.deepcopy(
            other._autosave_policy
        )

        self._recent_file = getattr(
            other,
            "_recent_file",
            None,
        )

    # -----------------------------------------------------

    def default_settings(self) -> Dict[str, Any]:
        """
        Return the default configuration.
        """

        return {

            "autosave": asdict(
                AutosavePolicy()
            ),

            "compression":
                getattr(
                    self,
                    "DEFAULT_COMPRESSION",
                    None,
                ),

            "schema_version":
                IO_SCHEMA_VERSION,

        }

    # -----------------------------------------------------

    def apply_default_settings(self) -> None:
        """
        Restore default configuration.
        """

        self._autosave_policy = AutosavePolicy()

    # -----------------------------------------------------
    # Factory APIs
    # -----------------------------------------------------

    @classmethod
    def create_manager(
        cls,
        **kwargs: Any,
    ) -> "IOManager":
        """
        Factory method for constructing
        an initialized IOManager.
        """

        manager = cls(**kwargs)

        manager.initialize()

        return manager

    # -----------------------------------------------------

    @classmethod
    def from_configuration(
        cls,
        config: Dict[str, Any],
    ) -> "IOManager":
        """
        Create an IOManager from a configuration
        dictionary.
        """

        manager = cls()

        manager.initialize()

        policy = config.get(
            "autosave",
            {},
        )

        for key, value in policy.items():

            if hasattr(
                manager._autosave_policy,
                key,
            ):

                setattr(
                    manager._autosave_policy,
                    key,
                    value,
                )

        return manager

    # -----------------------------------------------------
    # Singleton Access
    # -----------------------------------------------------

    _instance: Optional["IOManager"] = None

    @classmethod
    def instance(cls) -> "IOManager":
        """
        Return the shared singleton instance.
        """

        if cls._instance is None:

            cls._instance = cls.create_manager()

        return cls._instance

    # -----------------------------------------------------

    @classmethod
    def destroy_instance(cls) -> None:
        """
        Destroy the singleton instance.
        """

        if cls._instance is not None:

            cls._instance.shutdown()

            cls._instance = None

    # -----------------------------------------------------
    # Metadata
    # -----------------------------------------------------

    @property
    def version(self) -> str:
        """
        Current I/O module version.
        """

        return IO_VERSION

    # -----------------------------------------------------

    @property
    def schema_version(self) -> str:
        """
        Current schema version.
        """

        return IO_SCHEMA_VERSION

    # -----------------------------------------------------

    @property
    def initialized(self) -> bool:
        """
        Whether the manager is initialized.
        """

        return getattr(
            self,
            "_initialized",
            False,
        )

    # -----------------------------------------------------

    def metadata(self) -> Dict[str, Any]:
        """
        Return module metadata.
        """

        return {

            "module":
                self.__class__.__name__,

            "version":
                self.version,

            "schema":
                self.schema_version,

            "initialized":
                self.initialized,

            "session":
                self.session_identifier(),

        }

    # -----------------------------------------------------
    # Magic Methods
    # -----------------------------------------------------

    def __repr__(self) -> str:
        """
        Developer representation.
        """

        return (
            f"{self.__class__.__name__}("
            f"version={self.version!r}, "
            f"initialized={self.initialized}, "
            f"autosave={self.autosave_enabled()})"
        )

    # -----------------------------------------------------

    def __str__(self) -> str:
        """
        User-friendly representation.
        """

        return (
            f"{self.__class__.__name__} "
            f"(v{self.version})"
        )

    # -----------------------------------------------------

    def __enter__(self) -> "IOManager":
        """
        Context manager entry.
        """

        self.initialize()

        return self

    # -----------------------------------------------------

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> bool:
        """
        Context manager exit.
        """

        self.shutdown()

        return False

    # -----------------------------------------------------

    def __del__(self) -> None:
        """
        Best-effort cleanup during garbage collection.
        """

        try:
            self.shutdown()
        except Exception:
            pass