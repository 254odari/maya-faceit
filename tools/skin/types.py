# -*- coding: utf-8 -*-
"""
tools/skin/types.py

Enums and dataclasses for the skin toolkit.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple


# =============================================================================
# ENUMS
# =============================================================================

class SkinType(Enum):
    """Type of skin deformation."""
    STANDARD = "standard"
    DUAL_QUATERNION = "dual_quaternion"
    GPU = "gpu"


class SkinState(Enum):
    """State of a skinCluster."""
    NORMAL = "normal"
    BOUND = "bound"
    PARTIAL = "partial"
    INVALID = "invalid"


class NormalizeMode(Enum):
    """Weight normalization mode."""
    TOTAL = "total"              # Normalize total weight to 1.0 per vertex
    PER_VERTEX = "per_vertex"    # Same as TOTAL
    PER_INFLUENCE = "per_influence"  # Normalize each influence's total to 1.0
    NONE = "none"               # No normalization


class PruneMode(Enum):
    """Mode for pruning weights."""
    BY_VALUE = "value"          # Remove weights below threshold
    BY_RANK = "rank"            # Keep only top N influences
    BY_BOTH = "both"           # Both value and rank


class InfluenceType(Enum):
    """Type of influence."""
    JOINT = "joint"
    CONTROLLER = "controller"
    OTHER = "other"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class InfluenceInfo:
    """Information about a skin influence."""
    name: str
    type: InfluenceType = InfluenceType.JOINT
    index: int = -1
    weight_total: float = 0.0
    affected_vertices: int = 0
    max_weight: float = 0.0
    locked: bool = False


@dataclass
class SkinInfo:
    """Information about a skinCluster."""
    name: str
    mesh: str
    influences: List[InfluenceInfo] = field(default_factory=list)
    vertex_count: int = 0
    max_influences: int = 5
    skin_type: SkinType = SkinType.STANDARD
    normalized: bool = True
    state: SkinState = SkinState.NORMAL
    bind_pose: Optional[List[float]] = None


@dataclass
class WeightStatistics:
    """Statistics for a vertex or skin."""
    minimum: float = 0.0
    maximum: float = 1.0
    average: float = 0.0
    median: float = 0.0
    std_dev: float = 0.0
    sum: float = 0.0
    count: int = 0
    zero_count: int = 0
    active_count: int = 0
    normalized: bool = False


@dataclass
class SkinReport:
    """Report of a skin operation."""
    success: bool = True
    operation: str = ""
    skin_name: str = ""
    processed_vertices: int = 0
    modified_weights: int = 0
    added_influences: int = 0
    removed_influences: int = 0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)