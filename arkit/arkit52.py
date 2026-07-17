"""
arkit52.py

Official Apple ARKit 52 Blendshape Specification.

This module contains the canonical definition of the 52 ARKit
facial blendshapes used throughout the maya_faceit project.

Responsibilities
----------------
• Blendshape definitions
• Facial regions
• Categories
• Symmetry information
• Validation tables
• Lookup utilities
• Metadata

This module intentionally contains no Maya-specific code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple, Set, Optional

MODULE_NAME = "arkit52"
MODULE_VERSION = "1.0.0"
ARKIT_VERSION = "Apple ARKit 52"
BLENDSHAPE_COUNT = 52

# ---- 2. ARKit Blendshape List (52) ----
ARKIT_BLENDSHAPES = [
    "browDownLeft",
    "browDownRight",
    "browInnerUp",
    "browOuterUpLeft",
    "browOuterUpRight",
    "cheekPuff",
    "cheekSquintLeft",
    "cheekSquintRight",
    "eyeBlinkLeft",
    "eyeBlinkRight",
    "eyeLookDownLeft",
    "eyeLookDownRight",
    "eyeLookInLeft",
    "eyeLookInRight",
    "eyeLookOutLeft",
    "eyeLookOutRight",
    "eyeLookUpLeft",
    "eyeLookUpRight",
    "eyeSquintLeft",
    "eyeSquintRight",
    "eyeWideLeft",
    "eyeWideRight",
    "jawForward",
    "jawLeft",
    "jawOpen",
    "jawRight",
    "mouthClose",
    "mouthDimpleLeft",
    "mouthDimpleRight",
    "mouthFrownLeft",
    "mouthFrownRight",
    "mouthFunnel",
    "mouthLeft",
    "mouthLowerDownLeft",
    "mouthLowerDownRight",
    "mouthPressLeft",
    "mouthPressRight",
    "mouthPucker",
    "mouthRight",
    "mouthRollLower",
    "mouthRollUpper",
    "mouthShrugLower",
    "mouthShrugUpper",
    "mouthSmileLeft",
    "mouthSmileRight",
    "mouthStretchLeft",
    "mouthStretchRight",
    "mouthUpperUpLeft",
    "mouthUpperUpRight",
    "noseSneerLeft",
    "noseSneerRight",
    "tongueOut",
]

ARKIT_SET = set(ARKIT_BLENDSHAPES)
ARKIT_INDEX = {name: i for i, name in enumerate(ARKIT_BLENDSHAPES)}

# ---- 4. Facial Regions ----
FACIAL_REGIONS = {
    "Brows": [
        "browDownLeft",
        "browDownRight",
        "browInnerUp",
        "browOuterUpLeft",
        "browOuterUpRight",
    ],
    "Eyes": [
        "eyeBlinkLeft",
        "eyeBlinkRight",
        "eyeLookDownLeft",
        "eyeLookDownRight",
        "eyeLookInLeft",
        "eyeLookInRight",
        "eyeLookOutLeft",
        "eyeLookOutRight",
        "eyeLookUpLeft",
        "eyeLookUpRight",
        "eyeSquintLeft",
        "eyeSquintRight",
        "eyeWideLeft",
        "eyeWideRight",
    ],
    "Cheeks": [
        "cheekPuff",
        "cheekSquintLeft",
        "cheekSquintRight",
    ],
    "Jaw": [
        "jawForward",
        "jawLeft",
        "jawOpen",
        "jawRight",
    ],
    "Mouth": [
        "mouthClose",
        "mouthDimpleLeft",
        "mouthDimpleRight",
        "mouthFrownLeft",
        "mouthFrownRight",
        "mouthFunnel",
        "mouthLeft",
        "mouthLowerDownLeft",
        "mouthLowerDownRight",
        "mouthPressLeft",
        "mouthPressRight",
        "mouthPucker",
        "mouthRight",
        "mouthRollLower",
        "mouthRollUpper",
        "mouthShrugLower",
        "mouthShrugUpper",
        "mouthSmileLeft",
        "mouthSmileRight",
        "mouthStretchLeft",
        "mouthStretchRight",
        "mouthUpperUpLeft",
        "mouthUpperUpRight",
    ],
    "Nose": [
        "noseSneerLeft",
        "noseSneerRight",
    ],
    "Tongue": [
        "tongueOut",
    ],
}

# ---- 5. Left/Right Symmetry ----
LEFT_RIGHT_PAIRS = {
    "browDownLeft": "browDownRight",
    "browOuterUpLeft": "browOuterUpRight",
    "cheekSquintLeft": "cheekSquintRight",
    "eyeBlinkLeft": "eyeBlinkRight",
    "eyeLookDownLeft": "eyeLookDownRight",
    "eyeLookInLeft": "eyeLookInRight",
    "eyeLookOutLeft": "eyeLookOutRight",
    "eyeLookUpLeft": "eyeLookUpRight",
    "eyeSquintLeft": "eyeSquintRight",
    "eyeWideLeft": "eyeWideRight",
    "jawLeft": "jawRight",
    "mouthDimpleLeft": "mouthDimpleRight",
    "mouthFrownLeft": "mouthFrownRight",
    "mouthLowerDownLeft": "mouthLowerDownRight",
    "mouthPressLeft": "mouthPressRight",
    "mouthSmileLeft": "mouthSmileRight",
    "mouthStretchLeft": "mouthStretchRight",
    "mouthUpperUpLeft": "mouthUpperUpRight",
    "noseSneerLeft": "noseSneerRight",
}

# Also add reverse mapping
LEFT_RIGHT_PAIRS.update({v: k for k, v in list(LEFT_RIGHT_PAIRS.items())})

# ---- 6. Expression Categories ----
EXPRESSION_CATEGORIES = {
    "Movement": [
        "browDownLeft",
        "browDownRight",
        "browInnerUp",
        "browOuterUpLeft",
        "browOuterUpRight",
        "cheekPuff",
        "cheekSquintLeft",
        "cheekSquintRight",
        "jawForward",
        "jawLeft",
        "jawOpen",
        "jawRight",
        "noseSneerLeft",
        "noseSneerRight",
        "tongueOut",
    ],
    "EyeMovement": [
        "eyeLookDownLeft",
        "eyeLookDownRight",
        "eyeLookInLeft",
        "eyeLookInRight",
        "eyeLookOutLeft",
        "eyeLookOutRight",
        "eyeLookUpLeft",
        "eyeLookUpRight",
    ],
    "LipShapes": [
        "mouthClose",
        "mouthDimpleLeft",
        "mouthDimpleRight",
        "mouthFrownLeft",
        "mouthFrownRight",
        "mouthFunnel",
        "mouthLeft",
        "mouthLowerDownLeft",
        "mouthLowerDownRight",
        "mouthPressLeft",
        "mouthPressRight",
        "mouthPucker",
        "mouthRight",
        "mouthRollLower",
        "mouthRollUpper",
        "mouthShrugLower",
        "mouthShrugUpper",
        "mouthSmileLeft",
        "mouthSmileRight",
        "mouthStretchLeft",
        "mouthStretchRight",
        "mouthUpperUpLeft",
        "mouthUpperUpRight",
    ],
    "EyeClosure": [
        "eyeBlinkLeft",
        "eyeBlinkRight",
        "eyeSquintLeft",
        "eyeSquintRight",
        "eyeWideLeft",
        "eyeWideRight",
    ],
}

# ---- 7. Default Values ----
DEFAULT_VALUE = 0.0
MIN_WEIGHT = 0.0
MAX_WEIGHT = 1.0
SUPPORTED_WEIGHT_RANGE = (0.0, 1.0)

# ---- 8. Validation Constants ----
# (no additional constants needed beyond MIN/MAX)

# ---- 9. Search & Lookup Utilities ----
def is_valid(name: str) -> bool:
    """Return True if name is a known ARKit blendshape."""
    return name in ARKIT_SET

def region(name: str) -> Optional[str]:
    """Return the facial region (e.g. 'Brows') for the given blendshape, or None if invalid."""
    for reg, names in FACIAL_REGIONS.items():
        if name in names:
            return reg
    return None

def is_left(name: str) -> bool:
    """Return True if the blendshape is a left-side shape."""
    return name.endswith("Left") or "Left" in name and name not in ("jawLeft", "mouthLeft")  # careful
    # better: check if it has a right counterpart in LEFT_RIGHT_PAIRS and is the left key.
    # We'll use a more robust approach:
    if name in LEFT_RIGHT_PAIRS:
        # if it is a left shape, its mirror will be right; we can check convention
        # Actually LEFT_RIGHT_PAIRS includes both directions, so we need to identify lefts.
        # Use common suffix:
        return name.endswith("Left") or "Left" in name and name not in ("jawLeft", "mouthLeft")  # these are okay
    return False

# Let's simplify: create a set of left names from the keys of LEFT_RIGHT_PAIRS that end with Left
LEFT_NAMES = {name for name in LEFT_RIGHT_PAIRS.keys() if name.endswith("Left")}
RIGHT_NAMES = {name for name in LEFT_RIGHT_PAIRS.keys() if name.endswith("Right")}

def is_left(name: str) -> bool:
    return name in LEFT_NAMES

def is_right(name: str) -> bool:
    return name in RIGHT_NAMES

def mirror(name: str) -> Optional[str]:
    """Return the mirror (opposite side) blendshape, or None if no mirror."""
    return LEFT_RIGHT_PAIRS.get(name)

def category(name: str) -> Optional[str]:
    """Return the expression category (e.g. 'Movement') for the given blendshape, or None."""
    for cat, names in EXPRESSION_CATEGORIES.items():
        if name in names:
            return cat
    return None

# ---- 10. Statistics ----
def statistics() -> Dict[str, int]:
    """Return a dictionary with counts for blendshapes, regions, and pairs."""
    return {
        "blendshape_count": len(ARKIT_BLENDSHAPES),
        "regions": len(FACIAL_REGIONS),
        "pairs": len(LEFT_RIGHT_PAIRS) // 2,  # because we have both directions
    }

# ---- 11. Public API ----
__all__ = [
    "MODULE_NAME",
    "MODULE_VERSION",
    "ARKIT_VERSION",
    "BLENDSHAPE_COUNT",
    "ARKIT_BLENDSHAPES",
    "ARKIT_SET",
    "ARKIT_INDEX",
    "FACIAL_REGIONS",
    "LEFT_RIGHT_PAIRS",
    "EXPRESSION_CATEGORIES",
    "DEFAULT_VALUE",
    "MIN_WEIGHT",
    "MAX_WEIGHT",
    "SUPPORTED_WEIGHT_RANGE",
    "is_valid",
    "region",
    "is_left",
    "is_right",
    "mirror",
    "category",
    "statistics",
]