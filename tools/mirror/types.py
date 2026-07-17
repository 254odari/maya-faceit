# -*- coding: utf-8 -*-
"""
tools/mirror/types.py

Enums and dataclasses for the mirror engine.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any


# =============================================================================
# ENUMS
# =============================================================================

class MirrorAxis(Enum):
    """Axis along which to mirror."""
    X = "x"
    Y = "y"
    Z = "z"


class MirrorMode(Enum):
    """Type of data to mirror."""
    TRANSFORM = "transform"
    POSE = "pose"
    ANIMATION = "animation"
    BLENDSHAPE = "blendshape"
    MESH = "mesh"
    UV = "uv"
    CONTROLLER = "controller"
    SELECTION = "selection"


class MirrorBehavior(Enum):
    """Behavior when mirroring: copy, swap, or average."""
    COPY = "copy"           # Copy source to target (overwrite)
    SWAP = "swap"           # Swap between left and right
    AVERAGE = "average"     # Average values between left and right


class MirrorScope(Enum):
    """Scope for animation mirroring."""
    TIMELINE = "timeline"
    SELECTED_KEYS = "selected_keys"
    CURRENT_FRAME = "current_frame"
    LAYERS = "layers"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class MirrorPair:
    """A pair of objects to mirror between."""
    source: str
    target: str
    source_side: Optional[str] = None   # 'L', 'R', or None
    target_side: Optional[str] = None


@dataclass
class MirrorStatistics:
    """Statistics collected during a mirror operation."""
    total_nodes: int = 0
    mirrored_nodes: int = 0
    skipped_nodes: int = 0
    failed_nodes: int = 0
    duration_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)