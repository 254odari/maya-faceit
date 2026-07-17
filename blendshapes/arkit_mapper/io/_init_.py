# -*- coding: utf-8 -*-
"""I/O subsystem for the ARKit Mapper.

This package provides a unified interface for loading, saving, importing,
exporting, migrating, and managing ARKit mapping data, presets, runtime
snapshots, and complete projects.

Usage:
    from maya_faceit.blendshapes.arkit_mapper.io import IOManager
    io = IOManager()
    mappings = io.load_mapping("my_mappings.json")
"""

from .constants import *
from .enums import *
from .models import *
from .manager import IOManager

# Also import the mixins for direct use if needed (though typically not required)
from .mapping_io import MappingIO
from .preset_io import PresetIO
from .runtime_io import RuntimeIO
from .project_io import ProjectIO

__all__ = [
    # Constants
    "IO_VERSION",
    "IO_VERSION_MAJOR",
    "IO_VERSION_MINOR",
    "IO_VERSION_PATCH",
    "IO_SCHEMA_VERSION",
    "DEFAULT_ENCODING",
    "DEFAULT_INDENT",
    "DEFAULT_BACKUP_SUFFIX",
    "DEFAULT_PROJECT_EXTENSION",
    "DEFAULT_MAPPING_EXTENSION",
    "DEFAULT_PRESET_EXTENSION",
    "DEFAULT_STATS_EXTENSION",
    "DEFAULT_RUNTIME_EXTENSION",
    "DEFAULT_JSON_EXTENSION",
    "DEFAULT_YAML_EXTENSION",
    "DEFAULT_CSV_EXTENSION",
    "DEFAULT_BINARY_EXTENSION",
    "DEFAULT_COMPRESSED_EXTENSION",
    "DEFAULT_TEMP_EXTENSION",
    "DEFAULT_TIMEOUT",
    "DEFAULT_BUFFER_SIZE",
    # Enums
    "FileFormat",
    "CompressionType",
    "BackupMode",
    "MigrationStrategy",
    "ChecksumAlgorithm",
    "IOStatus",
    # Models
    "IOConfig",
    "IOResult",
    "FileMetadata",
    "BackupInfo",
    "ProjectSnapshot",
    "AutosaveState",
    "AutosavePolicy",
    "AutosaveEntry",
    # Mixins (mostly internal, but may be used for extension)
    "MappingIO",
    "PresetIO",
    "RuntimeIO",
    "ProjectIO",
    # Main class
    "IOManager",
]