# -*- coding: utf-8 -*-
"""
tools/skin
~~~~~~~~~~

Skinning toolkit for Maya FaceIT.

Provides:
- SkinCluster creation and management
- Weight editing (normalize, smooth, clamp, prune)
- Influence management (add, remove, reorder)
- Weight mirroring and transfer
- Validation

Usage:
    from maya_faceit.tools.skin import SkinEngine
    skin = SkinEngine()
    skin.create(mesh, influences)
    skin.normalize(mesh)
    skin.mirror(mesh)
"""

from .types import (
    SkinType,
    SkinState,
    NormalizeMode,
    PruneMode,
    InfluenceType,
    SkinInfo,
    InfluenceInfo,
    WeightStatistics,
    SkinReport,
)
from .settings import SkinSettings, DEFAULT_SKIN_SETTINGS
from .engine import SkinEngine, skin
from .editor import SkinEditor
from .weights import WeightTools
from .influences import InfluenceTools
from .mirror import SkinMirror
from .transfer import SkinTransfer
from .validation import SkinValidator

__all__ = [
    # Types
    "SkinType",
    "SkinState",
    "NormalizeMode",
    "PruneMode",
    "InfluenceType",
    "SkinInfo",
    "InfluenceInfo",
    "WeightStatistics",
    "SkinReport",
    # Settings
    "SkinSettings",
    "DEFAULT_SKIN_SETTINGS",
    # Main Engine
    "SkinEngine",
    "skin",
    # Subsystems
    "SkinEditor",
    "WeightTools",
    "InfluenceTools",
    "SkinMirror",
    "SkinTransfer",
    "SkinValidator",
]