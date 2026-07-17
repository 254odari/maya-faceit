"""
maya_faceit.expression.serializer

Import/Export Facial Expressions.

This module provides serialization and deserialization of expression definitions
and libraries to/from various formats: JSON, Binary, YAML (optional),
Faceit project format, ARKit format, FBX metadata, and custom extensions.

It is used by the ExpressionManager for saving/loading libraries, and can also
be called directly for individual expression export.

Responsibilities:
- Serialize ExpressionEntry and ExpressionDefinition to dict/JSON/binary.
- Deserialize from JSON/binary/YAML back to objects.
- Export/import expression libraries to/from files.
- Support multiple formats with format detection.
- Validate imported data and handle versioning.

Author: Maya FaceIT Team
"""

from __future__ import annotations

import base64
import copy
import json
import logging
import pickle
import struct
import time
from dataclasses import asdict
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple, BinaryIO, TextIO

# Import dependencies (with fallbacks)
try:
    from .library import ExpressionEntry, ExpressionMetadata, ExpressionLibrary
    from .generator import ExpressionDefinition, ExpressionType
    from ..blendshapes.blendshape_utils import sanitize_name, normalize_weights
    HAS_DEPS = True
except ImportError:
    # Fallback for development
    class ExpressionEntry:
        def __init__(self, definition=None, metadata=None):
            self.definition = definition
            self.metadata = metadata
        def to_dict(self): return {}
        @classmethod
        def from_dict(cls, data): return cls()
    class ExpressionMetadata:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
    class ExpressionDefinition:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
    class ExpressionType:
        BASIC = "basic"
        CUSTOM = "custom"
        ARKIT = "arkit"
    class ExpressionLibrary:
        def add(self, definition, **kwargs): pass
        def list_entries(self): return []
    def sanitize_name(name): return name
    def normalize_weights(weights): return weights
    HAS_DEPS = False

# Try optional YAML
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

logger = logging.getLogger(__name__)

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"

# ---- Exceptions ----

class SerializationError(Exception):
    """Base exception for serialization errors."""
    pass

class UnsupportedFormatError(SerializationError):
    """Raised when a format is not supported."""
    pass

class ValidationError(SerializationError):
    """Raised when data validation fails."""
    pass

class ImportError(SerializationError):
    """Raised when import fails."""
    pass


# ---- Constants ----

SERIALIZER_VERSION = "1.0.0"
MAGIC_BYTES = b"FACEEXP"  # 7 bytes
BINARY_VERSION = 1

SUPPORTED_FORMATS = {
    "json": {"ext": [".json"], "type": "json"},
    "binary": {"ext": [".facexp", ".bin"], "type": "binary"},
    "yaml": {"ext": [".yaml", ".yml"], "type": "yaml"},
    "faceit": {"ext": [".faceit"], "type": "json"},  # Faceit project uses JSON with specific schema
    "arkit": {"ext": [".arkit"], "type": "json"},
    "fbx_metadata": {"ext": [".fbx"], "type": "json"},  # Placeholder
}


# ---- Serialization Engines ----

class SerializationEngine:
    """
    Base class for serialization engines.
    """

    FORMAT_NAME = "base"

    @classmethod
    def serialize(cls, data: Any) -> Any:
        """Serialize data to a format-specific representation."""
        raise NotImplementedError

    @classmethod
    def deserialize(cls, data: Any) -> Any:
        """Deserialize from format-specific representation."""
        raise NotImplementedError

    @classmethod
    def save_to_file(cls, data: Any, filepath: Union[str, Path]) -> None:
        """Save serialized data to a file."""
        raise NotImplementedError

    @classmethod
    def load_from_file(cls, filepath: Union[str, Path]) -> Any:
        """Load serialized data from a file."""
        raise NotImplementedError


class JsonEngine(SerializationEngine):
    """JSON serialization engine."""

    FORMAT_NAME = "json"

    @classmethod
    def serialize(cls, data: Any, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(data, indent=indent, ensure_ascii=False, default=cls._json_default)

    @classmethod
    def deserialize(cls, data: str) -> Any:
        """Deserialize from JSON string."""
        return json.loads(data)

    @classmethod
    def save_to_file(cls, data: Any, filepath: Union[str, Path]) -> None:
        path = Path(filepath)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=cls._json_default)

    @classmethod
    def load_from_file(cls, filepath: Union[str, Path]) -> Any:
        path = Path(filepath)
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def _json_default(obj: Any) -> Any:
        """Default JSON serializer for non-serializable objects."""
        if hasattr(obj, 'to_dict'):
            return obj.to_dict()
        if isinstance(obj, Enum):
            return obj.value
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


class YamlEngine(SerializationEngine):
    """YAML serialization engine (optional)."""

    FORMAT_NAME = "yaml"

    @classmethod
    def serialize(cls, data: Any) -> str:
        if not HAS_YAML:
            raise SerializationError("PyYAML is not installed. Install with: pip install pyyaml")
        return yaml.dump(data, default_flow_style=False, allow_unicode=True)

    @classmethod
    def deserialize(cls, data: str) -> Any:
        if not HAS_YAML:
            raise SerializationError("PyYAML is not installed.")
        return yaml.safe_load(data)

    @classmethod
    def save_to_file(cls, data: Any, filepath: Union[str, Path]) -> None:
        if not HAS_YAML:
            raise SerializationError("PyYAML is not installed.")
        path = Path(filepath)
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

    @classmethod
    def load_from_file(cls, filepath: Union[str, Path]) -> Any:
        if not HAS_YAML:
            raise SerializationError("PyYAML is not installed.")
        path = Path(filepath)
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)


class BinaryEngine(SerializationEngine):
    """Binary serialization engine using pickle with a header."""

    FORMAT_NAME = "binary"

    @classmethod
    def serialize(cls, data: Any) -> bytes:
        # We wrap with a header: magic bytes + version + length + pickle data
        pickle_data = pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)
        length = len(pickle_data)
        header = struct.pack('>7s I I', MAGIC_BYTES, BINARY_VERSION, length)
        return header + pickle_data

    @classmethod
    def deserialize(cls, data: bytes) -> Any:
        # Validate header
        magic = data[:7]
        if magic != MAGIC_BYTES:
            raise SerializationError("Invalid binary format: magic bytes mismatch.")
        version = struct.unpack('>I', data[7:11])[0]
        if version != BINARY_VERSION:
            raise SerializationError(f"Unsupported binary version: {version}")
        length = struct.unpack('>I', data[11:15])[0]
        pickle_data = data[15:15+length]
        return pickle.loads(pickle_data)

    @classmethod
    def save_to_file(cls, data: Any, filepath: Union[str, Path]) -> None:
        path = Path(filepath)
        with open(path, 'wb') as f:
            f.write(cls.serialize(data))

    @classmethod
    def load_from_file(cls, filepath: Union[str, Path]) -> Any:
        path = Path(filepath)
        with open(path, 'rb') as f:
            data = f.read()
        return cls.deserialize(data)


# ---- Expression Serializer ----

class ExpressionSerializer:
    """
    High-level serializer for expression libraries and entries.

    Provides methods to serialize/deserialize to/from various formats,
    and to save/load from files.
    """

    # Registry of engines
    _engines = {
        "json": JsonEngine,
        "yaml": YamlEngine,
        "binary": BinaryEngine,
    }

    # Map file extensions to format names
    _ext_to_format = {
        ".json": "json",
        ".facexp": "binary",
        ".bin": "binary",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".faceit": "json",  # Faceit project uses JSON
        ".arkit": "json",
    }

    @classmethod
    def register_engine(cls, format_name: str, engine_class: type) -> None:
        """Register a custom serialization engine."""
        cls._engines[format_name] = engine_class

    @classmethod
    def get_format_from_extension(cls, filepath: Union[str, Path]) -> Optional[str]:
        """Determine format from file extension."""
        ext = Path(filepath).suffix.lower()
        return cls._ext_to_format.get(ext)

    # ---- Serialization of Library Entries ----

    @classmethod
    def serialize_entry(
        cls,
        entry: ExpressionEntry,
        format: str = "json",
        include_metadata: bool = True,
    ) -> Union[str, bytes]:
        """
        Serialize a single ExpressionEntry.

        Args:
            entry: ExpressionEntry to serialize.
            format: 'json', 'binary', 'yaml'.
            include_metadata: If True, include metadata in output.

        Returns:
            Serialized data (string or bytes).
        """
        engine = cls._get_engine(format)
        data = entry.to_dict() if include_metadata else entry.definition.to_dict()
        return engine.serialize(data)

    @classmethod
    def deserialize_entry(
        cls,
        data: Union[str, bytes],
        format: str = "json",
    ) -> ExpressionEntry:
        """
        Deserialize an ExpressionEntry.

        Args:
            data: Serialized data (string or bytes).
            format: 'json', 'binary', 'yaml'.

        Returns:
            ExpressionEntry.
        """
        engine = cls._get_engine(format)
        parsed = engine.deserialize(data)
        return cls._dict_to_entry(parsed)

    # ---- Serialization of Libraries ----

    @classmethod
    def serialize_library(
        cls,
        library: ExpressionLibrary,
        format: str = "json",
        include_builtin: bool = False,
    ) -> Union[str, bytes]:
        """
        Serialize an entire ExpressionLibrary.

        Args:
            library: ExpressionLibrary to serialize.
            format: 'json', 'binary', 'yaml'.
            include_builtin: If True, include built-in expressions.

        Returns:
            Serialized data.
        """
        engine = cls._get_engine(format)
        entries = library.list_entries()
        if not include_builtin:
            entries = [e for e in entries if e.metadata.source != "builtin"]
        data = {
            "version": SERIALIZER_VERSION,
            "format": format,
            "created": time.ctime(),
            "entries": [e.to_dict() for e in entries],
        }
        return engine.serialize(data)

    @classmethod
    def deserialize_library(
        cls,
        data: Union[str, bytes],
        format: str = "json",
        library: Optional[ExpressionLibrary] = None,
        overwrite: bool = False,
    ) -> ExpressionLibrary:
        """
        Deserialize and populate an ExpressionLibrary.

        Args:
            data: Serialized data.
            format: 'json', 'binary', 'yaml'.
            library: Optional existing library to populate (creates new if None).
            overwrite: If True, overwrite existing entries with same name.

        Returns:
            Populated ExpressionLibrary.
        """
        engine = cls._get_engine(format)
        parsed = engine.deserialize(data)

        # Validate top-level structure
        if "entries" not in parsed:
            # Try to interpret as a single entry
            try:
                entry = cls._dict_to_entry(parsed)
                if library is None:
                    library = ExpressionLibrary()
                library.add(entry.definition, **asdict(entry.metadata))
                return library
            except:
                raise ValidationError("Invalid library data: missing 'entries' field.")

        if library is None:
            library = ExpressionLibrary()
        for entry_data in parsed["entries"]:
            entry = cls._dict_to_entry(entry_data)
            # Check for duplicate
            existing = library.get(entry.metadata.name)
            if existing and not overwrite:
                logger.warning(f"Entry '{entry.metadata.name}' already exists; skipping.")
                continue
            if existing and overwrite:
                library.remove(entry.metadata.name)
            library.add(entry.definition, **asdict(entry.metadata))
        return library

    # ---- File I/O ----

    @classmethod
    def save_entry_to_file(
        cls,
        entry: ExpressionEntry,
        filepath: Union[str, Path],
        format: Optional[str] = None,
    ) -> None:
        """
        Save a single expression entry to a file.

        Args:
            entry: ExpressionEntry to save.
            filepath: Output file path.
            format: Format to use (auto-detected from extension if None).
        """
        if format is None:
            format = cls.get_format_from_extension(filepath)
            if format is None:
                raise UnsupportedFormatError(f"Cannot determine format from extension: {filepath}")
        engine = cls._get_engine(format)
        data = entry.to_dict()
        engine.save_to_file(data, filepath)

    @classmethod
    def load_entry_from_file(
        cls,
        filepath: Union[str, Path],
        format: Optional[str] = None,
    ) -> ExpressionEntry:
        """
        Load a single expression entry from a file.

        Args:
            filepath: Input file path.
            format: Format to use (auto-detected from extension if None).

        Returns:
            ExpressionEntry.
        """
        if format is None:
            format = cls.get_format_from_extension(filepath)
            if format is None:
                raise UnsupportedFormatError(f"Cannot determine format from extension: {filepath}")
        engine = cls._get_engine(format)
        data = engine.load_from_file(filepath)
        return cls._dict_to_entry(data)

    @classmethod
    def save_library_to_file(
        cls,
        library: ExpressionLibrary,
        filepath: Union[str, Path],
        format: Optional[str] = None,
        include_builtin: bool = False,
    ) -> None:
        """
        Save an ExpressionLibrary to a file.

        Args:
            library: ExpressionLibrary to save.
            filepath: Output file path.
            format: Format to use (auto-detected from extension if None).
            include_builtin: If True, include built-in expressions.
        """
        if format is None:
            format = cls.get_format_from_extension(filepath)
            if format is None:
                raise UnsupportedFormatError(f"Cannot determine format from extension: {filepath}")
        engine = cls._get_engine(format)
        entries = library.list_entries()
        if not include_builtin:
            entries = [e for e in entries if e.metadata.source != "builtin"]
        data = {
            "version": SERIALIZER_VERSION,
            "format": format,
            "created": time.ctime(),
            "entries": [e.to_dict() for e in entries],
        }
        engine.save_to_file(data, filepath)

    @classmethod
    def load_library_from_file(
        cls,
        filepath: Union[str, Path],
        format: Optional[str] = None,
        library: Optional[ExpressionLibrary] = None,
        overwrite: bool = False,
    ) -> ExpressionLibrary:
        """
        Load an ExpressionLibrary from a file.

        Args:
            filepath: Input file path.
            format: Format to use (auto-detected from extension if None).
            library: Optional existing library to populate.
            overwrite: If True, overwrite existing entries.

        Returns:
            Populated ExpressionLibrary.
        """
        if format is None:
            format = cls.get_format_from_extension(filepath)
            if format is None:
                raise UnsupportedFormatError(f"Cannot determine format from extension: {filepath}")
        engine = cls._get_engine(format)
        data = engine.load_from_file(filepath)
        return cls.deserialize_library(data, format, library, overwrite)

    # ---- Helper Methods ----

    @classmethod
    def _get_engine(cls, format: str) -> type:
        """Get engine class for format."""
        engine = cls._engines.get(format.lower())
        if engine is None:
            raise UnsupportedFormatError(f"Unsupported format: {format}")
        return engine

    @classmethod
    def _dict_to_entry(cls, data: Dict[str, Any]) -> ExpressionEntry:
        """Convert a dictionary to an ExpressionEntry."""
        # Try to parse as full entry
        if "definition" in data and "metadata" in data:
            return ExpressionEntry.from_dict(data)
        # Try to parse as definition only
        if "coefficients" in data:
            # Assume it's a definition
            defn = ExpressionDefinition(
                name=data.get("name", "Unnamed"),
                coefficients=data.get("coefficients", {}),
                expression_type=ExpressionType(data.get("type", "custom")),
                description=data.get("description", ""),
                tags=data.get("tags", []),
                metadata=data.get("metadata", {}),
            )
            # Create default metadata
            import uuid
            from datetime import datetime
            meta = ExpressionMetadata(
                id=str(uuid.uuid4()),
                name=defn.name,
                created=datetime.utcnow().isoformat(),
                modified=datetime.utcnow().isoformat(),
                author="imported",
                tags=defn.tags,
                category=defn.metadata.get("category", "Imported"),
                source="imported",
            )
            return ExpressionEntry(definition=defn, metadata=meta)
        raise ValidationError("Invalid entry data: missing 'definition' or 'coefficients'.")


# ---- Convenience Functions ----

def save(
    data: Union[ExpressionEntry, ExpressionLibrary, List[ExpressionEntry]],
    filepath: Union[str, Path],
    format: Optional[str] = None,
    **kwargs,
) -> None:
    """
    Save expression data to a file.

    Args:
        data: ExpressionEntry, ExpressionLibrary, or list of entries.
        filepath: Output path.
        format: Format (auto-detected if None).
        **kwargs: Additional options (e.g., include_builtin).
    """
    if isinstance(data, ExpressionEntry):
        ExpressionSerializer.save_entry_to_file(data, filepath, format)
    elif isinstance(data, ExpressionLibrary):
        ExpressionSerializer.save_library_to_file(data, filepath, format, kwargs.get("include_builtin", False))
    elif isinstance(data, list):
        # Assume list of entries; create a temporary library
        lib = ExpressionLibrary()
        for entry in data:
            lib.add(entry.definition, **asdict(entry.metadata))
        ExpressionSerializer.save_library_to_file(lib, filepath, format, kwargs.get("include_builtin", False))
    else:
        raise TypeError(f"Unsupported data type: {type(data)}")


def load(
    filepath: Union[str, Path],
    format: Optional[str] = None,
    library: Optional[ExpressionLibrary] = None,
    overwrite: bool = False,
) -> Union[ExpressionEntry, ExpressionLibrary]:
    """
    Load expression data from a file.

    Returns:
        If the file contains a single entry, returns ExpressionEntry.
        If it contains a library, returns ExpressionLibrary (or populated library).
    """
    # Try to detect if it's a library or a single entry by first parsing
    # We'll attempt to load as a library first, and if that fails, as an entry.
    try:
        # Try as library
        lib = ExpressionSerializer.load_library_from_file(filepath, format, library, overwrite)
        # If the library has exactly one entry and we didn't pass a library,
        # we might want to return the entry directly? But to be safe, return library.
        return lib
    except ValidationError:
        # Try as entry
        return ExpressionSerializer.load_entry_from_file(filepath, format)


def serialize(
    data: Union[ExpressionEntry, ExpressionLibrary, List[ExpressionEntry]],
    format: str = "json",
    **kwargs,
) -> Union[str, bytes]:
    """
    Serialize expression data to a string or bytes.

    Args:
        data: ExpressionEntry, ExpressionLibrary, or list of entries.
        format: 'json', 'binary', 'yaml'.
        **kwargs: Additional options.

    Returns:
        Serialized data.
    """
    if isinstance(data, ExpressionEntry):
        return ExpressionSerializer.serialize_entry(data, format, kwargs.get("include_metadata", True))
    elif isinstance(data, ExpressionLibrary):
        return ExpressionSerializer.serialize_library(data, format, kwargs.get("include_builtin", False))
    elif isinstance(data, list):
        lib = ExpressionLibrary()
        for entry in data:
            lib.add(entry.definition, **asdict(entry.metadata))
        return ExpressionSerializer.serialize_library(lib, format, kwargs.get("include_builtin", False))
    else:
        raise TypeError(f"Unsupported data type: {type(data)}")


def deserialize(
    data: Union[str, bytes],
    format: str = "json",
    library: Optional[ExpressionLibrary] = None,
    overwrite: bool = False,
) -> Union[ExpressionEntry, ExpressionLibrary]:
    """
    Deserialize expression data.

    Args:
        data: Serialized string or bytes.
        format: 'json', 'binary', 'yaml'.
        library: Optional library to populate.
        overwrite: Whether to overwrite existing entries.

    Returns:
        ExpressionEntry or ExpressionLibrary.
    """
    # Try to interpret as a library first
    try:
        return ExpressionSerializer.deserialize_library(data, format, library, overwrite)
    except ValidationError:
        # Try as single entry
        return ExpressionSerializer.deserialize_entry(data, format)


# ---- Public API ----

__all__ = [
    "ExpressionSerializer",
    "SerializationError",
    "UnsupportedFormatError",
    "ValidationError",
    "ImportError",
    "save",
    "load",
    "serialize",
    "deserialize",
    "SUPPORTED_FORMATS",
]