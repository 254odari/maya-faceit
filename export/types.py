# -*- coding: utf-8 -*-
"""
export/types.py

Enums and dataclasses for the export system.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple


# =============================================================================
# ENUMS
# =============================================================================

class ExportFormat(Enum):
    """Supported export formats."""
    FBX = "fbx"
    USD = "usd"
    ABC = "abc"
    JSON = "json"
    MAYA_ASCII = "ma"
    MAYA_BINARY = "mb"


class ExportMode(Enum):
    """Scope of export."""
    SELECTION = "selection"
    SCENE = "scene"
    CUSTOM = "custom"


class EngineType(Enum):
    """Target game engine."""
    UNREAL = "unreal"
    UNITY = "unity"
    METAHUMAN = "metahuman"
    CUSTOM = "custom"


class PackageType(Enum):
    """Packaging type."""
    ZIP = "zip"
    FOLDER = "folder"
    NONE = "none"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class ExportSettings:
    """Global export settings."""
    format: ExportFormat = ExportFormat.FBX
    mode: ExportMode = ExportMode.SELECTION
    filepath: str = ""
    objects: List[str] = field(default_factory=list)
    start_frame: int = 0
    end_frame: int = 0
    frame_rate: float = 24.0
    include_textures: bool = True
    include_animation: bool = True
    include_controls: bool = True
    include_blendshapes: bool = True
    include_skin: bool = True
    optimize: bool = True
    engine: EngineType = EngineType.CUSTOM
    engine_script: str = ""  # Custom engine script path
    package_type: PackageType = PackageType.NONE
    package_name: str = ""
    overwrite: bool = False
    verbose: bool = False
    undo_chunk_name: str = "Export Operation"


@dataclass
class ExportResult:
    """Result of a single export operation."""
    success: bool = True
    format: ExportFormat = ExportFormat.FBX
    filepath: str = ""
    objects_exported: int = 0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExportReport:
    """Complete export report."""
    success: bool = True
    results: List[ExportResult] = field(default_factory=list)
    elapsed_time_ms: float = 0.0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)