"""
tools/mesh/types.py

Type definitions, Enums, and Data Models for the mesh processing subsystem.
Centralized location for all mesh-related types used across the maya_faceit plugin.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple, Union

import maya.api.OpenMaya as om # type: ignore


# =============================================================================
# ENUMERATIONS
# =============================================================================

class MeshOperation(Enum):
    """Supported high-level mesh operations."""
    MERGE = auto()
    SEPARATE = auto()
    COMBINE = auto()
    EXTRACT = auto()
    DUPLICATE = auto()
    DELETE = auto()
    TRIANGULATE = auto()
    QUADRANGULATE = auto()
    BRIDGE = auto()
    EXTRUDE = auto()
    BEVEL = auto()
    CHAMFER = auto()
    POKE = auto()
    MULTI_CUT = auto()
    COLLAPSE = auto()
    REMESH = auto()
    POLY_REDUCE = auto()
    CLEANUP = auto()
    OPTIMIZE = auto()


class NormalMode(Enum):
    """Normal calculation modes."""
    HARD = auto()
    SOFT = auto()
    AVERAGE = auto()
    UNLOCK = auto()
    LOCK = auto()
    RECALCULATE = auto()
    TRANSFER = auto()


class UVProjection(Enum):
    """UV projection types."""
    AUTOMATIC = auto()
    PLANAR = auto()
    CYLINDRICAL = auto()
    SPHERICAL = auto()
    CAMERA = auto()
    UNWRAP = auto()
    LAYOUT = auto()


class ComponentType(Enum):
    """Mesh component types."""
    VERTEX = auto()
    EDGE = auto()
    FACE = auto()
    UV = auto()


class IssueSeverity(Enum):
    """Validation issue severity levels."""
    ERROR = auto()
    WARNING = auto()
    INFO = auto()


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class MeshSettings:
    """Configuration settings for mesh operations."""
    preserve_uvs: bool = True
    preserve_normals: bool = True
    preserve_history: bool = False
    cleanup_after_operation: bool = True
    maintain_symmetry: bool = False
    symmetry_tolerance: float = 0.001
    freeze_transforms: bool = False
    delete_history_on_finish: bool = False
    use_undo_chunk: bool = True


@dataclass
class MeshStatistics:
    """Comprehensive mesh statistics."""
    vertices: int = 0
    edges: int = 0
    faces: int = 0
    triangles: int = 0
    ngons: int = 0
    quads: int = 0
    isolated_vertices: int = 0
    duplicate_vertices: int = 0
    non_manifold_edges: int = 0
    lamina_faces: int = 0
    zero_area_faces: int = 0
    zero_length_edges: int = 0
    open_borders: int = 0
    uv_shells: int = 0
    uv_overlaps: int = 0
    
    surface_area: float = 0.0
    volume: float = 0.0
    bounding_box: Tuple[float, float, float, float, float, float] = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    
    # Performance / quality metrics
    average_edge_length: float = 0.0
    max_edge_length: float = 0.0
    density_variance: float = 0.0


@dataclass
class MeshIssue:
    """Represents a single validation issue."""
    severity: IssueSeverity
    issue_type: str
    description: str
    component_type: Optional[ComponentType] = None
    component_ids: List[int] = field(default_factory=list)
    mesh_name: str = ""
    suggestion: Optional[str] = None


@dataclass
class MeshReport:
    """Operation report with statistics and issues."""
    operation: str
    success: bool = True
    elapsed_time: float = 0.0
    meshes_processed: int = 0
    
    statistics: Optional[MeshStatistics] = None
    issues: List[MeshIssue] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    repaired_count: int = 0
    operations_performed: List[str] = field(default_factory=list)
    
    # Optional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TopologyFingerprint:
    """Unique signature for mesh topology (used for compatibility checks)."""
    vertex_count: int
    face_count: int
    edge_count: int
    hash_value: str
    boundary_loops: int
    genus: int = 0
    is_manifold: bool = True
    
    # Optional detailed signature
    face_size_distribution: Dict[int, int] = field(default_factory=dict)


# =============================================================================
# TYPE ALIASES
# =============================================================================

MeshSelection = Union[str, List[str]]                    # Mesh name(s)
ComponentSelection = List[int]                           # Component indices
MObject = om.MObject
DagPath = om.MDagPath
PointArray = om.MPointArray
FloatArray = om.MFloatArray

# Common return types
AnalysisResult = Dict[str, Any]
ValidationResult = Tuple[bool, List[MeshIssue]]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def default_mesh_settings() -> MeshSettings:
    """Return default mesh operation settings."""
    return MeshSettings()


def create_empty_statistics() -> MeshStatistics:
    """Return empty statistics object."""
    return MeshStatistics()


__all__ = [
    # Enums
    "MeshOperation",
    "NormalMode",
    "UVProjection",
    "ComponentType",
    "IssueSeverity",
    
    # Data Models
    "MeshSettings",
    "MeshStatistics",
    "MeshIssue",
    "MeshReport",
    "TopologyFingerprint",
    
    # Type aliases
    "MeshSelection",
    "ComponentSelection",
    "MObject",
    "DagPath",
    "AnalysisResult",
    "ValidationResult",
    
    # Helpers
    "default_mesh_settings",
    "create_empty_statistics",
]