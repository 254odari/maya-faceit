"""
utils.py

Utility functions for querying ARKit channels.
"""

from typing import Dict, List

from .enums import ARKitChannel, ARKitRegion
from .regions import CHANNEL_REGION_MAP


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