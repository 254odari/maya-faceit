# -*- coding: utf-8 -*-
"""
tools/mirror/settings.py

Configuration for the mirror engine.
"""

from dataclasses import dataclass, field
from typing import Optional, List
from .types import MirrorAxis, MirrorBehavior, MirrorScope


@dataclass
class MirrorSettings:
    """Global settings for a mirror operation."""
    axis: MirrorAxis = MirrorAxis.X
    behavior: MirrorBehavior = MirrorBehavior.SWAP
    mirror_translate: bool = True
    mirror_rotate: bool = True
    mirror_scale: bool = False
    mirror_custom_attributes: bool = True
    mirror_visibility: bool = False
    mirror_limits: bool = False
    mirror_sdk: bool = False
    mirror_shapes: bool = True
    mirror_blendshape_weights: bool = True
    mirror_mesh_vertices: bool = True
    mirror_uvs: bool = True
    animation_scope: MirrorScope = MirrorScope.TIMELINE
    animation_start: Optional[int] = None
    animation_end: Optional[int] = None
    include_selected_only: bool = False
    preserve_original: bool = False   # If True, duplicates before mirroring
    ignore_locked: bool = True
    ignore_hidden: bool = True
    tolerance: float = 1e-5