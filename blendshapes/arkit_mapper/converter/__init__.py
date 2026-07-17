"""
converter

ARKit ⇄ Rig conversion engine.

Features
--------
- One-to-many mappings
- Calibration support
- Merge modes (MAX, ADD, AVERAGE, OVERRIDE)
- Forward conversion (ARKit → Rig)
- Reverse conversion (Rig → ARKit)
- Runtime compilation cache
- Maya-independent
"""

from .enums import MergeMode
from .models import CompiledMapping, ConverterStatistics
from .core import ARKitConverter

__all__ = [
    "MergeMode",
    "CompiledMapping",
    "ConverterStatistics",
    "ARKitConverter",
]