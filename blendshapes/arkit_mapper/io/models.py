# -*- coding: utf-8 -*-
"""Dataclasses for the ARKit Mapper I/O subsystem."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .enums import ChecksumAlgorithm, FileFormat, CompressionType, BackupMode, MigrationStrategy, IOStatus
from .constants import IO_VERSION, IO_SCHEMA_VERSION

@dataclass(slots=True)
class IOConfig:
    encoding: str = "utf-8"
    indent: int = 4
    backup_mode: BackupMode = BackupMode.BEFORE_SAVE
    compression: CompressionType = CompressionType.NONE
    checksum_algorithm: ChecksumAlgorithm = ChecksumAlgorithm.SHA256
    migration_strategy: MigrationStrategy = MigrationStrategy.SAFE
    overwrite_existing: bool = True
    create_directories: bool = True
    validate_before_save: bool = True
    atomic_writes: bool = True
    auto_backup: bool = True
    timeout: float = 10.0


@dataclass(slots=True)
class IOResult:
    status: IOStatus
    success: bool
    path: Optional[Path] = None
    format: Optional[FileFormat] = None
    message: str = ""
    data: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    elapsed_time: float = 0.0


@dataclass(slots=True)
class FileMetadata:
    path: Path
    format: FileFormat
    size: int = 0
    created: Optional[datetime] = None
    modified: Optional[datetime] = None
    checksum: Optional[str] = None
    version: str = IO_VERSION


@dataclass(slots=True)
class BackupInfo:
    original: Path
    backup: Path
    created: datetime = field(default_factory=datetime.now)
    size: int = 0


@dataclass(slots=True)
class ProjectSnapshot:
    version: str = IO_VERSION
    created: datetime = field(default_factory=datetime.now)
    mappings: Dict[str, Any] = field(default_factory=dict)
    presets: Dict[str, Any] = field(default_factory=dict)
    statistics: Dict[str, Any] = field(default_factory=dict)
    runtime: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)