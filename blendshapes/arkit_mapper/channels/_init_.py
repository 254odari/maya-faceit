"""
channels

Definitions for Apple's ARKit 52 facial blendshape channels.

This module provides:
    - ARKitChannel enum
    - ARKitRegion enum
    - Region grouping
    - Validation helpers
    - Query utilities
"""

from .enums import ARKitChannel, ARKitRegion
from .regions import CHANNEL_REGION_MAP
from .utils import channels_by_region, grouped_channels

__all__ = [
    "ARKitChannel",
    "ARKitRegion",
    "CHANNEL_REGION_MAP",
    "channels_by_region",
    "grouped_channels",
]