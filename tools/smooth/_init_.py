# -*- coding: utf-8 -*-
"""
tools/smooth
~~~~~~~~~~~~

Central smoothing engine for Maya FaceIT.

Provides a consistent API for smoothing geometry, weights, normals,
curves, and UVs using multiple algorithms.

Usage:
    from maya_faceit.tools.smooth import SmoothEngine
    smooth = SmoothEngine()
    smooth.mesh("pCube1", iterations=10)
    smooth.weights("skinCluster1", iterations=5)
"""

from .types import (
    SmoothMode,
    SmoothAlgorithm,
    SmoothBoundary,
    SmoothFalloff,
    SmoothSettings,
    SmoothReport,
    SmoothStatistics,
)
from .settings import DEFAULT_SMOOTH_SETTINGS
from .engine import SmoothEngine, smooth

__all__ = [
    # Types
    "SmoothMode",
    "SmoothAlgorithm",
    "SmoothBoundary",
    "SmoothFalloff",
    "SmoothSettings",
    "SmoothReport",
    "SmoothStatistics",
    # Settings
    "DEFAULT_SMOOTH_SETTINGS",
    # Engine
    "SmoothEngine",
    "smooth",
]