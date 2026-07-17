# -*- coding: utf-8 -*-
"""
tools/mirror
~~~~~~~~~~~~

Central mirroring engine for Maya FaceIT.

This package provides the `MirrorTools` class for mirroring controllers,
poses, animation, blendshapes, meshes, UVs, and selections.

Usage:
    from maya_faceit.tools.mirror import MirrorTools
    mirror = MirrorTools()
    mirror.mirror_selected()
"""

from .types import (
    MirrorAxis,
    MirrorMode,
    MirrorBehavior,
    MirrorScope,
    MirrorPair,
    MirrorStatistics,
    MirrorReport,
)
from .settings import MirrorSettings

# Import the main MirrorTools class from the legacy module (to maintain backward compatibility)
try:
    from ..mirror import MirrorTools
except ImportError:
    # Fallback: define a placeholder if the module is not found
    # (this should not happen in a normal installation)
    class MirrorTools:
        """Placeholder: full implementation in tools.mirror."""
        def __init__(self, *args, **kwargs):
            raise NotImplementedError(
                "The full MirrorTools implementation is in tools.mirror. "
                "Please import from there or ensure the module is available."
            )

__all__ = [
    # Types
    "MirrorAxis",
    "MirrorMode",
    "MirrorBehavior",
    "MirrorScope",
    "MirrorPair",
    "MirrorStatistics",
    "MirrorReport",
    # Settings
    "MirrorSettings",
    # Main class
    "MirrorTools",
]