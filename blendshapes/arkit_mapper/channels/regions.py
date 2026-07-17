"""
regions.py

Region mapping for ARKit channels.
"""

from typing import Dict

from .enums import ARKitChannel, ARKitRegion


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