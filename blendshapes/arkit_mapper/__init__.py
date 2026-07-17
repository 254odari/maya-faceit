"""
maya_faceit.blendshapes.arkit_mapper

ARKit mapping package.

Provides conversion between Apple's ARKit 52 blendshape
coefficients and Maya Faceit's internal BlendShape system.

Target
------
Maya 2026
Python 3.11
"""

from .channels import ARKitChannel

from .mapping import (
    RigTarget,
    ARKitMapping,
    MappingResult,
)

from .mapper import (
    ARKitMapper,
    arkit_mapper,
)

__all__ = [
    "ARKitChannel",
    "RigTarget",
    "ARKitMapping",
    "MappingResult",
    "ARKitMapper",
    "arkit_mapper",
]