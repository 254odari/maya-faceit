"""
enums.py

ARKit enum definitions.
"""

from enum import Enum
from typing import List, Dict, Optional, Set


class ARKitRegion(Enum):
    """Facial regions used for grouping ARKit channels."""

    BROW = "brow"
    EYE = "eye"
    CHEEK = "cheek"
    NOSE = "nose"
    JAW = "jaw"
    MOUTH = "mouth"
    TONGUE = "tongue"


class ARKitChannel(str, Enum):
    """
    Official ARKit blendshape coefficient names.
    """

    # --------------------------------------------------------
    # Brow (5)
    # --------------------------------------------------------

    BROW_DOWN_LEFT = "browDownLeft"
    BROW_DOWN_RIGHT = "browDownRight"
    BROW_INNER_UP = "browInnerUp"
    BROW_OUTER_UP_LEFT = "browOuterUpLeft"
    BROW_OUTER_UP_RIGHT = "browOuterUpRight"

    # --------------------------------------------------------
    # Cheeks (3)
    # --------------------------------------------------------

    CHEEK_PUFF = "cheekPuff"
    CHEEK_SQUINT_LEFT = "cheekSquintLeft"
    CHEEK_SQUINT_RIGHT = "cheekSquintRight"

    # --------------------------------------------------------
    # Eyes (14)
    # --------------------------------------------------------

    EYE_BLINK_LEFT = "eyeBlinkLeft"
    EYE_BLINK_RIGHT = "eyeBlinkRight"

    EYE_LOOK_DOWN_LEFT = "eyeLookDownLeft"
    EYE_LOOK_DOWN_RIGHT = "eyeLookDownRight"

    EYE_LOOK_IN_LEFT = "eyeLookInLeft"
    EYE_LOOK_IN_RIGHT = "eyeLookInRight"

    EYE_LOOK_OUT_LEFT = "eyeLookOutLeft"
    EYE_LOOK_OUT_RIGHT = "eyeLookOutRight"

    EYE_LOOK_UP_LEFT = "eyeLookUpLeft"
    EYE_LOOK_UP_RIGHT = "eyeLookUpRight"

    EYE_SQUINT_LEFT = "eyeSquintLeft"
    EYE_SQUINT_RIGHT = "eyeSquintRight"

    EYE_WIDE_LEFT = "eyeWideLeft"
    EYE_WIDE_RIGHT = "eyeWideRight"

    # --------------------------------------------------------
    # Jaw (4)
    # --------------------------------------------------------

    JAW_FORWARD = "jawForward"
    JAW_LEFT = "jawLeft"
    JAW_OPEN = "jawOpen"
    JAW_RIGHT = "jawRight"

    # --------------------------------------------------------
    # Mouth (23)
    # --------------------------------------------------------

    MOUTH_CLOSE = "mouthClose"

    MOUTH_DIMPLE_LEFT = "mouthDimpleLeft"
    MOUTH_DIMPLE_RIGHT = "mouthDimpleRight"

    MOUTH_FROWN_LEFT = "mouthFrownLeft"
    MOUTH_FROWN_RIGHT = "mouthFrownRight"

    MOUTH_FUNNEL = "mouthFunnel"

    MOUTH_LEFT = "mouthLeft"

    MOUTH_LOWER_DOWN_LEFT = "mouthLowerDownLeft"
    MOUTH_LOWER_DOWN_RIGHT = "mouthLowerDownRight"

    MOUTH_PRESS_LEFT = "mouthPressLeft"
    MOUTH_PRESS_RIGHT = "mouthPressRight"

    MOUTH_PUCKER = "mouthPucker"

    MOUTH_RIGHT = "mouthRight"

    MOUTH_ROLL_LOWER = "mouthRollLower"
    MOUTH_ROLL_UPPER = "mouthRollUpper"

    MOUTH_SHRUG_LOWER = "mouthShrugLower"
    MOUTH_SHRUG_UPPER = "mouthShrugUpper"

    MOUTH_SMILE_LEFT = "mouthSmileLeft"
    MOUTH_SMILE_RIGHT = "mouthSmileRight"

    MOUTH_STRETCH_LEFT = "mouthStretchLeft"
    MOUTH_STRETCH_RIGHT = "mouthStretchRight"

    MOUTH_UPPER_UP_LEFT = "mouthUpperUpLeft"
    MOUTH_UPPER_UP_RIGHT = "mouthUpperUpRight"

    # --------------------------------------------------------
    # Nose (2)
    # --------------------------------------------------------

    NOSE_SNEER_LEFT = "noseSneerLeft"
    NOSE_SNEER_RIGHT = "noseSneerRight"

    # --------------------------------------------------------
    # Tongue (1)
    # --------------------------------------------------------

    TONGUE_OUT = "tongueOut"

    # ========================================================
    # Helpers
    # ========================================================

    @classmethod
    def names(cls) -> List[str]:
        """Return all ARKit channel names."""
        return [c.value for c in cls]

    @classmethod
    def values(cls) -> List["ARKitChannel"]:
        """Return all enum members."""
        return list(cls)

    @classmethod
    def count(cls) -> int:
        """Return the number of supported channels."""
        return len(cls)

    @classmethod
    def is_valid(cls, name: str) -> bool:
        """Return True if the supplied name is a valid ARKit channel."""
        return name in cls.names()

    @classmethod
    def from_name(cls, name: str) -> "ARKitChannel":
        """Return an enum from its ARKit name."""
        for channel in cls:
            if channel.value == name:
                return channel
        raise ValueError(f"Unknown ARKit channel: {name}")