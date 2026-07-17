# -*- coding: utf-8 -*-
"""
tools/controllers/types.py

Enums, dataclasses, and typed dictionaries for the controller toolkit.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple

# =============================================================================
# ENUMS
# =============================================================================

class ControllerType(Enum):
    """Type of controller."""
    BUTTON = "button"
    CIRCLE = "circle"
    SQUARE = "square"
    TRIANGLE = "triangle"
    ARROW = "arrow"
    CROSS = "cross"
    DIAMOND = "diamond"
    JOYSTICK = "joystick"
    SLIDER = "slider"
    CUSTOM = "custom"
    NURBS = "nurbs"

class ControllerState(Enum):
    """State of a controller."""
    NORMAL = "normal"
    SELECTED = "selected"
    HOVER = "hover"
    LOCKED = "locked"
    DISABLED = "disabled"
    HIDDEN = "hidden"

class ControllerShape(Enum):
    """Predefined controller shapes."""
    CIRCLE = "circle"
    SQUARE = "square"
    TRIANGLE = "triangle"
    DIAMOND = "diamond"
    ARROW = "arrow"
    CROSS = "cross"
    STAR = "star"
    CUSTOM = "custom"

class ControllerAxis(Enum):
    """Axis for controller orientation."""
    X = "x"
    Y = "y"
    Z = "z"
    NONE = "none"

class ControllerAttribute(Enum):
    """Common controller attributes."""
    TRANSLATE_X = "tx"
    TRANSLATE_Y = "ty"
    TRANSLATE_Z = "tz"
    ROTATE_X = "rx"
    ROTATE_Y = "ry"
    ROTATE_Z = "rz"
    SCALE_X = "sx"
    SCALE_Y = "sy"
    SCALE_Z = "sz"
    VISIBILITY = "visibility"

# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class ControllerInfo:
    """Information about a controller node."""
    name: str
    long_name: str = ""
    type: ControllerType = ControllerType.CUSTOM
    shape: ControllerShape = ControllerShape.CIRCLE
    side: Optional[str] = None  # 'L', 'R', 'C'
    parent: Optional[str] = None
    children: List[str] = field(default_factory=list)
    attributes: List[str] = field(default_factory=list)
    custom_attributes: Dict[str, Any] = field(default_factory=dict)
    color: Tuple[float, float, float] = (0.5, 0.5, 0.5)
    locked: bool = False
    hidden: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ControllerPair:
    """A pair of symmetric controllers."""
    source: str
    target: str
    source_side: Optional[str] = None
    target_side: Optional[str] = None
    confidence: float = 1.0

@dataclass
class ControllerStats:
    """Statistics for a controller or group."""
    total: int = 0
    locked: int = 0
    hidden: int = 0
    selected: int = 0
    animated: int = 0
    has_custom_attrs: int = 0