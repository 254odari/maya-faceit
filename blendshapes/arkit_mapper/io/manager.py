# -*- coding: utf-8 -*-
"""IOManager – composed from all mixins."""

from pathlib import Path
from typing import Optional

from .path_mixin import PathMixin
from .validation_mixin import ValidationMixin
from .json_mixin import JSONMixin
from .yaml_mixin import YAMLMixin
from .csv_mixin import CSVMixin
from .binary_mixin import BinaryMixin
from .checksum_mixin import ChecksumMixin
from .compression_mixin import CompressionMixin
from .archive_mixin import ArchiveMixin
from .atomic_mixin import AtomicMixin
from .migration_mixin import MigrationMixin
from .backup_mixin import BackupMixin
from .autosave_mixin import AutosaveMixin
from .session_mixin import SessionMixin
from .high_level_mixin import HighLevelMixin
from .diagnostics_mixin import DiagnosticsMixin
from .statistics_mixin import StatisticsMixin
from .utils_mixin import UtilsMixin
from .mapping_io import MappingIO
from .preset_io import PresetIO
from .runtime_io import RuntimeIO
from .project_io import ProjectIO
from .models import IOConfig


class IOManager(
    PathMixin,
    ValidationMixin,
    JSONMixin,
    YAMLMixin,
    CSVMixin,
    BinaryMixin,
    ChecksumMixin,
    CompressionMixin,
    ArchiveMixin,
    AtomicMixin,
    MigrationMixin,
    BackupMixin,
    AutosaveMixin,
    SessionMixin,
    HighLevelMixin,
    DiagnosticsMixin,
    StatisticsMixin,
    UtilsMixin,
    MappingIO,
    PresetIO,
    RuntimeIO,
    ProjectIO,
):
    """Central I/O manager for the ARKit Mapper.

    Provides a unified interface for all I/O operations:
    - File system utilities (path, validation, atomic writes)
    - Serialization (JSON, YAML, CSV, binary)
    - Checksums, compression, archives
    - Version migration and backups
    - Autosave and session management
    - Domain-specific I/O for mappings, presets, runtime, projects
    - High-level APIs, diagnostics, statistics
    """

    _instance = None

    def __init__(self, config: Optional[IOConfig] = None):
        self.config = config or IOConfig()
        self._history = []
        self._recent_file = None
        self._init_session()
        self._init_migration_registry()
        self._init_autosave()

    # The mixins provide all methods. No additional code needed here.