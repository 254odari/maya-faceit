# -*- coding: utf-8 -*-
"""
tools/symmetry/types.py

Enums and dataclasses for symmetry analysis.
"""
import time
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple, Path


# =============================================================================
# ENUMS
# =============================================================================

class SymmetryAxis(Enum):
    """Axis along which symmetry is defined."""
    X = "x"
    Y = "y"
    Z = "z"


class SymmetryStatus(Enum):
    """Symmetry status of a component."""
    SYMMETRIC = "symmetric"
    ASYMMETRIC = "asymmetric"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


class MatchMethod(Enum):
    """Method used for matching symmetric pairs."""
    NAME = "name"
    POSITION = "position"
    TOPOLOGY = "topology"
    UV = "uv"
    HYBRID = "hybrid"


class SymmetryScope(Enum):
    """Scope of symmetry analysis."""
    FULL = "full"
    REGION = "region"
    SELECTION = "selection"
    CUSTOM = "custom"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class SymmetrySettings:
    """Settings for symmetry analysis and operations."""
    axis: SymmetryAxis = SymmetryAxis.X
    tolerance: float = 0.0001
    max_distance: float = 0.1
    auto_repair: bool = False
    use_topology: bool = True
    use_name_matching: bool = True
    use_position_matching: bool = False
    use_uv_matching: bool = False
    match_threshold: float = 0.75
    scope: SymmetryScope = SymmetryScope.FULL
    cache_enabled: bool = True
    cache_directory: Optional[Path] = None
    verbose: bool = False


@dataclass
class SymmetryPlane:
    """Definition of a symmetry plane."""
    axis: SymmetryAxis
    center: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    normal: Tuple[float, float, float] = (1.0, 0.0, 0.0)
    confidence: float = 1.0
    method: str = "world_origin"


@dataclass
class VertexPair:
    """A pair of symmetric vertices."""
    vertex1: int
    vertex2: int
    distance: float = 0.0
    confidence: float = 1.0


@dataclass
class ControllerPair:
    """A pair of symmetric controllers."""
    source: str
    target: str
    method: MatchMethod = MatchMethod.NAME
    confidence: float = 1.0


@dataclass
class JointPair:
    """A pair of symmetric joints."""
    source: str
    target: str
    confidence: float = 1.0


@dataclass
class BlendshapePair:
    """A pair of symmetric blendshape targets."""
    source: str
    target: str
    confidence: float = 1.0


@dataclass
class SymmetryMap:
    """Container for all symmetry mappings."""
    mesh: str = ""
    vertices: List[VertexPair] = field(default_factory=list)
    controllers: List[ControllerPair] = field(default_factory=list)
    joints: List[JointPair] = field(default_factory=list)
    blendshapes: List[BlendshapePair] = field(default_factory=list)
    vertex_count: int = 0
    symmetric_vertex_count: int = 0
    asymmetric_vertex_count: int = 0
    plane: Optional[SymmetryPlane] = None
    settings: SymmetrySettings = field(default_factory=SymmetrySettings)
    created: str = field(default_factory=lambda: time.ctime())
    checksum: str = ""


@dataclass
class SymmetryReport:
    """Report of symmetry analysis."""
    mesh: str = ""
    plane: Optional[SymmetryPlane] = None
    vertex_count: int = 0
    symmetric_vertices: int = 0
    asymmetric_vertices: int = 0
    symmetric_percentage: float = 0.0
    controller_count: int = 0
    symmetric_controllers: int = 0
    asymmetric_controllers: int = 0
    joint_count: int = 0
    symmetric_joints: int = 0
    asymmetric_joints: int = 0
    blendshape_count: int = 0
    symmetric_blendshapes: int = 0
    asymmetric_blendshapes: int = 0
    confidence: float = 0.0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Result of a symmetry validation."""
    valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)