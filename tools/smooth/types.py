# -*- coding: utf-8 -*-
"""
tools/smooth/types.py

Enums and dataclasses for the smooth toolkit.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple


# =============================================================================
# ENUMS
# =============================================================================

class SmoothMode(Enum):
    """Type of data to smooth."""
    MESH = "mesh"
    WEIGHT = "weight"
    CURVE = "curve"
    NORMAL = "normal"
    UV = "uv"
    REGION = "region"


class SmoothAlgorithm(Enum):
    """Smoothing algorithm."""
    LAPLACIAN = "laplacian"
    HC = "hc"                     # Humphrey's Classes
    TAUBIN = "taubin"             # Taubin smoothing
    GAUSSIAN = "gaussian"
    BILATERAL = "bilateral"
    CATMULL_CLARK = "catmull_clark"  # Subdivision-like


class SmoothBoundary(Enum):
    """Boundary handling mode."""
    PRESERVE = "preserve"          # Keep boundary vertices fixed
    RELAX = "relax"                # Apply smoothing to boundaries too
    FIXED = "fixed"                # Treat boundaries as fixed (same as preserve)


class SmoothFalloff(Enum):
    """Falloff mode for vertex weighting."""
    LINEAR = "linear"
    SMOOTH = "smooth"              # Smoothstep
    GAUSSIAN = "gaussian"
    CONSTANT = "constant"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class SmoothSettings:
    """Settings for a smoothing operation."""
    iterations: int = 5
    strength: float = 0.5
    preserve_border: bool = True
    preserve_volume: bool = False
    preserve_symmetry: bool = False
    algorithm: SmoothAlgorithm = SmoothAlgorithm.LAPLACIAN
    boundary: SmoothBoundary = SmoothBoundary.PRESERVE
    falloff: SmoothFalloff = SmoothFalloff.LINEAR
    falloff_radius: float = 1.0
    mask_attribute: Optional[str] = None
    use_selection: bool = False
    verbose: bool = False
    undo_chunk_name: str = "Smooth Operation"


@dataclass
class SmoothStatistics:
    """Statistics of a smoothing operation."""
    processed_count: int = 0
    iterations: int = 0
    average_delta: float = 0.0
    max_delta: float = 0.0
    time_ms: float = 0.0


@dataclass
class SmoothReport:
    """Report of a smoothing operation."""
    success: bool = True
    mode: SmoothMode = SmoothMode.MESH
    statistics: SmoothStatistics = field(default_factory=SmoothStatistics)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SmoothValidation:
    """Validation result."""
    valid: bool = True
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)