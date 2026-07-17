# -*- coding: utf-8 -*-
"""
tools/relax/types.py

Enums and dataclasses for the relaxation toolkit.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple, Set


# =============================================================================
# ENUMS
# =============================================================================

class RelaxMode(Enum):
    """Type of relaxation."""
    MESH = "mesh"
    VERTEX = "vertex"
    SURFACE = "surface"
    WEIGHT = "weight"
    UV = "uv"
    REGION = "region"


class RelaxAlgorithm(Enum):
    """Relaxation algorithm."""
    LAPLACIAN = "laplacian"
    HC = "hc"                     # Humphrey's Classes (HC) algorithm
    TAUBIN = "taubin"             # Taubin smoothing (volume preserving)


class FalloffMode(Enum):
    """Falloff mode for vertex weighting."""
    LINEAR = "linear"
    SMOOTH = "smooth"             # Smoothstep
    GAUSSIAN = "gaussian"
    NONE = "none"


class WeightType(Enum):
    """Type of weights to relax."""
    SKIN = "skin"
    BLENDSHAPE = "blendshape"
    ARKIT = "arkit"
    CORRECTIVE = "corrective"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class RelaxSettings:
    """Settings for a relaxation operation."""
    iterations: int = 10
    strength: float = 0.5                 # 0-1, strength per iteration
    preserve_volume: bool = True
    preserve_border: bool = True
    preserve_symmetry: bool = False
    algorithm: RelaxAlgorithm = RelaxAlgorithm.HC
    falloff_mode: FalloffMode = FalloffMode.LINEAR
    falloff_radius: float = 1.0
    mask_attribute: Optional[str] = None  # vertex color or paint mask
    use_selection: bool = False
    verbose: bool = False
    undo_chunk_name: str = "Relax Operation"


@dataclass
class RelaxReport:
    """Report of relaxation operation."""
    success: bool = True
    mode: RelaxMode = RelaxMode.MESH
    processed_vertices: int = 0
    iterations: int = 0
    average_displacement: float = 0.0
    max_displacement: float = 0.0
    time_ms: float = 0.0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Validation result."""
    valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)