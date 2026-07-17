"""
maya_faceit.blendshapes.arkit_mapper.channels

Definitions for Apple's ARKit 52 facial blendshape channels.

This module provides:
    - ARKitChannel enum
    - Facial region grouping
    - Validation helpers
    - Query utilities

Target
------
Maya 2026
Python 3.11
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List


# ============================================================
# Facial Regions
# ============================================================

class ARKitRegion(Enum):
    """Facial regions used for grouping ARKit channels."""

    BROW = "brow"
    EYE = "eye"
    CHEEK = "cheek"
    NOSE = "nose"
    JAW = "jaw"
    MOUTH = "mouth"
    TONGUE = "tongue"


# ============================================================
# ARKit 52 Channels
# ============================================================

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

        return [channel.value for channel in cls]

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

    @classmethod
    def region(cls, channel: "ARKitChannel") -> ARKitRegion:
        """Return the facial region for a channel."""

        return CHANNEL_REGION_MAP[channel]


# ============================================================
# Region Lookup
# ============================================================

CHANNEL_REGION_MAP: Dict[ARKitChannel, ARKitRegion] = {

    # Brow
    ARKitChannel.BROW_DOWN_LEFT: ARKitRegion.BROW,
    ARKitChannel.BROW_DOWN_RIGHT: ARKitRegion.BROW,
    ARKitChannel.BROW_INNER_UP: ARKitRegion.BROW,
    ARKitChannel.BROW_OUTER_UP_LEFT: ARKitRegion.BROW,
    ARKitChannel.BROW_OUTER_UP_RIGHT: ARKitRegion.BROW,

    # Cheeks
    ARKitChannel.CHEEK_PUFF: ARKitRegion.CHEEK,
    ARKitChannel.CHEEK_SQUINT_LEFT: ARKitRegion.CHEEK,
    ARKitChannel.CHEEK_SQUINT_RIGHT: ARKitRegion.CHEEK,

    # Eyes
    ARKitChannel.EYE_BLINK_LEFT: ARKitRegion.EYE,
    ARKitChannel.EYE_BLINK_RIGHT: ARKitRegion.EYE,
    ARKitChannel.EYE_LOOK_DOWN_LEFT: ARKitRegion.EYE,
    ARKitChannel.EYE_LOOK_DOWN_RIGHT: ARKitRegion.EYE,
    ARKitChannel.EYE_LOOK_IN_LEFT: ARKitRegion.EYE,
    ARKitChannel.EYE_LOOK_IN_RIGHT: ARKitRegion.EYE,
    ARKitChannel.EYE_LOOK_OUT_LEFT: ARKitRegion.EYE,
    ARKitChannel.EYE_LOOK_OUT_RIGHT: ARKitRegion.EYE,
    ARKitChannel.EYE_LOOK_UP_LEFT: ARKitRegion.EYE,
    ARKitChannel.EYE_LOOK_UP_RIGHT: ARKitRegion.EYE,
    ARKitChannel.EYE_SQUINT_LEFT: ARKitRegion.EYE,
    ARKitChannel.EYE_SQUINT_RIGHT: ARKitRegion.EYE,
    ARKitChannel.EYE_WIDE_LEFT: ARKitRegion.EYE,
    ARKitChannel.EYE_WIDE_RIGHT: ARKitRegion.EYE,

    # Jaw
    ARKitChannel.JAW_FORWARD: ARKitRegion.JAW,
    ARKitChannel.JAW_LEFT: ARKitRegion.JAW,
    ARKitChannel.JAW_OPEN: ARKitRegion.JAW,
    ARKitChannel.JAW_RIGHT: ARKitRegion.JAW,

    # Mouth
    ARKitChannel.MOUTH_CLOSE: ARKitRegion.MOUTH,
    ARKitChannel.MOUTH_DIMPLE_LEFT: ARKitRegion.MOUTH,
    ARKitChannel.MOUTH_DIMPLE_RIGHT: ARKitRegion.MOUTH,
    ARKitChannel.MOUTH_FROWN_LEFT: ARKitRegion.MOUTH,
    ARKitChannel.MOUTH_FROWN_RIGHT: ARKitRegion.MOUTH,
    ARKitChannel.MOUTH_FUNNEL: ARKitRegion.MOUTH,
    ARKitChannel.MOUTH_LEFT: ARKitRegion.MOUTH,
    ARKitChannel.MOUTH_LOWER_DOWN_LEFT: ARKitRegion.MOUTH,
    ARKitChannel.MOUTH_LOWER_DOWN_RIGHT: ARKitRegion.MOUTH,
    ARKitChannel.MOUTH_PRESS_LEFT: ARKitRegion.MOUTH,
    ARKitChannel.MOUTH_PRESS_RIGHT: ARKitRegion.MOUTH,
    ARKitChannel.MOUTH_PUCKER: ARKitRegion.MOUTH,
    ARKitChannel.MOUTH_RIGHT: ARKitRegion.MOUTH,
    ARKitChannel.MOUTH_ROLL_LOWER: ARKitRegion.MOUTH,
    ARKitChannel.MOUTH_ROLL_UPPER: ARKitRegion.MOUTH,
    ARKitChannel.MOUTH_SHRUG_LOWER: ARKitRegion.MOUTH,
    ARKitChannel.MOUTH_SHRUG_UPPER: ARKitRegion.MOUTH,
    ARKitChannel.MOUTH_SMILE_LEFT: ARKitRegion.MOUTH,
    ARKitChannel.MOUTH_SMILE_RIGHT: ARKitRegion.MOUTH,
    ARKitChannel.MOUTH_STRETCH_LEFT: ARKitRegion.MOUTH,
    ARKitChannel.MOUTH_STRETCH_RIGHT: ARKitRegion.MOUTH,
    ARKitChannel.MOUTH_UPPER_UP_LEFT: ARKitRegion.MOUTH,
    ARKitChannel.MOUTH_UPPER_UP_RIGHT: ARKitRegion.MOUTH,

    # Nose
    ARKitChannel.NOSE_SNEER_LEFT: ARKitRegion.NOSE,
    ARKitChannel.NOSE_SNEER_RIGHT: ARKitRegion.NOSE,

    # Tongue
    ARKitChannel.TONGUE_OUT: ARKitRegion.TONGUE,
}


# ============================================================
# Helper Functions
# ============================================================

def channels_by_region(region: ARKitRegion) -> List[ARKitChannel]:
    """Return all channels belonging to a facial region."""

    return [
        channel
        for channel, reg in CHANNEL_REGION_MAP.items()
        if reg == region
    ]


def grouped_channels() -> Dict[ARKitRegion, List[ARKitChannel]]:
    """Return channels grouped by facial region."""

    return {
        region: channels_by_region(region)
        for region in ARKitRegion
    }