"""
maya_faceit.animation

Professional animation toolkit for Maya.

This package provides a comprehensive set of tools for timeline management,
keyframe editing, animation curves, animation layers, constraints, baking,
and scene cleanup. It is designed for facial rigs, character rigs, motion
capture, and ARKit workflows.

The package is Maya‑independent in its interface, but relies on Maya's Python
API for implementation. It is intended to be used by other modules in the
maya_faceit plugin and by external tools.

Modules
-------
- timeline.py      : Central time management (playback, frames, markers)
- keyframes.py     : Keyframe editing and manipulation
- curves.py        : Animation curve operations (evaluation, optimization)
- layers.py        : Animation layer management (creation, blending, baking)
- constraints.py   : Constraint creation, editing, and baking
- baking.py        : Animation baking engine (constraints, SDK, facial)
- cleanup.py       : Scene and animation cleanup (optimization, validation)

All public APIs are re‑exported from this module for convenient access.
"""

from __future__ import annotations

import logging
import sys
from typing import Dict, List, Optional, Any

# ---- Part 1: Version & Metadata -----------------------------------------

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"
__license__ = "MIT"

PACKAGE_NAME = "maya_faceit.animation"
VERSION = __version__
AUTHOR = __author__
LICENSE = __license__
SUPPORTED_MAYA_VERSIONS = (2022, 2023, 2024, 2025, 2026)
SUPPORTED_PYTHON_VERSIONS = (3.9, 3.10, 3.11)

# ---- Part 2: Configure Logging ------------------------------------------

logger = logging.getLogger(__name__)

# ---- Part 3: Public Imports ---------------------------------------------

# 3.1 Timeline
from .timeline import (
    TimelineManager,
    TimelineRange,
    TimelineMarker,
    TimelineBookmark,
    TimelineSnapshot,
    TimelineDiagnostics,
    TimelineStatistics,
    TimeUnit,
    PlaybackMode,
    TimelineState,
    get_current_frame,
    set_current_frame,
    get_frame_range,
    set_frame_range,
)

# 3.2 Keyframes
from .keyframes import (
    KeyframeManager,
    Keyframe,
    KeySelection,
    KeyClipboard,
    KeyStatistics,
    KeyReport,
    KeyInterpolation,
    KeySelectionMode,
    TransformMode,
)

# 3.3 Curves
from .curves import (
    CurveManager,
    AnimationCurve,
    CurveSample,
    CurveSegment,
    CurveStatistics as CurveStats,
    CurveReport as CurveReportObj,
    CurveSelection,
    CurveClipboard,
    CurveType,
    InterpolationMode,
    FilterMode,
    TangentType,
)

# 3.4 Layers
from .layers import (
    AnimationLayerManager,
    AnimationLayer,
    LayerSettings,
    LayerStatistics,
    LayerReport,
    LayerState,
    BlendMode,
    LayerType,
)

# 3.5 Constraints
from .constraints import (
    ConstraintManager,
    Constraint,
    ConstraintTarget,
    ConstraintSettings,
    ConstraintStatistics,
    ConstraintReport,
    ConstraintType,
    MaintainOffset,
    ConstraintState,
)

# 3.6 Baking
from .baking import (
    AnimationBaker,
    BatchBaker,
    BakeSettings,
    BakeRange,
    BakeResult,
    BakeStatistics,
    BakeReport,
    BakeTask,
    BakeQueue,
    BakeMode,
    BakeTarget,
    RotationInterpolation,
)

# 3.7 Cleanup
from .cleanup import (
    AnimationCleanupManager,
    CleanupSettings,
    CleanupTask,
    CleanupResult,
    CleanupStatistics,
    ValidationIssue,
    ValidationReport,
    CleanupReport,
    CleanupType,
    OptimizationLevel,
    ValidationState,
    get_cleanup_presets,
)

# 3.8 Re‑export commonly used exceptions
from .timeline import TimelineError, InvalidFrameError, InvalidRangeError
from .keyframes import KeyframeError, KeyframeSelectionError, KeyframeOperationError
from .curves import CurveError, CurveNotFoundError, CurveOperationError
from .layers import LayerError, LayerNotFoundError, LayerOperationError
from .constraints import ConstraintError, ConstraintNotFoundError, ConstraintCreationError
from .baking import BakingError, BakingCancelledError, InvalidBakeTargetError, BakeValidationError
from .cleanup import CleanupError, CleanupValidationError, CleanupOperationError, CleanupCancelledError

# ---- Part 4: Factory Functions ------------------------------------------

def create_timeline() -> TimelineManager:
    """Create a new TimelineManager instance."""
    return TimelineManager()


def create_keyframes() -> KeyframeManager:
    """Create a new KeyframeManager instance."""
    return KeyframeManager()


def create_curves() -> CurveManager:
    """Create a new CurveManager instance."""
    return CurveManager()


def create_layers() -> AnimationLayerManager:
    """Create a new AnimationLayerManager instance."""
    return AnimationLayerManager()


def create_constraints() -> ConstraintManager:
    """Create a new ConstraintManager instance."""
    return ConstraintManager()


def create_baker(settings: Optional[BakeSettings] = None) -> AnimationBaker:
    """
    Create a new AnimationBaker instance.
    Optionally pass default bake settings.
    """
    baker = AnimationBaker()
    if settings:
        baker._settings = settings  # This is a hack; we can set after creation.
        # Better: we should provide a proper way to set default settings.
        # We'll just create and return.
    return baker


def create_cleanup(settings: Optional[CleanupSettings] = None) -> AnimationCleanupManager:
    """Create a new AnimationCleanupManager instance."""
    manager = AnimationCleanupManager()
    if settings:
        manager._settings = settings
    return manager


# ---- Part 5: Package Information ---------------------------------------

def package_info() -> Dict[str, Any]:
    """
    Return package metadata and environment information.

    Returns:
        dict: Package name, version, author, modules, Maya version, Python version.
    """
    import maya.cmds as cmds
    maya_version = cmds.about(version=True) if hasattr(cmds, 'about') else "Unknown"

    return {
        "package": PACKAGE_NAME,
        "version": VERSION,
        "author": AUTHOR,
        "license": LICENSE,
        "modules": [
            "timeline",
            "keyframes",
            "curves",
            "layers",
            "constraints",
            "baking",
            "cleanup",
        ],
        "maya_version": maya_version,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "supported_maya": SUPPORTED_MAYA_VERSIONS,
        "supported_python": SUPPORTED_PYTHON_VERSIONS,
    }


# ---- Part 6: Compatibility Helpers --------------------------------------

def is_supported_maya(version: Optional[str] = None) -> bool:
    """
    Check if the current or given Maya version is supported.
    """
    if version is None:
        import maya.cmds as cmds
        version_str = cmds.about(version=True)
        # Extract major version number
        import re
        match = re.search(r'(\d{4})', version_str)
        if match:
            major = int(match.group(1))
            return major in SUPPORTED_MAYA_VERSIONS
        return False
    # If version is provided, parse it
    try:
        major = int(version.split('.')[0])
        return major in SUPPORTED_MAYA_VERSIONS
    except:
        return False


def is_supported_python() -> bool:
    """
    Check if the current Python version is supported.
    """
    return sys.version_info[:2] in SUPPORTED_PYTHON_VERSIONS


def check_environment() -> Dict[str, bool]:
    """
    Perform a quick environment check.
    Returns a dictionary with status for Maya and Python.
    """
    return {
        "maya_supported": is_supported_maya(),
        "python_supported": is_supported_python(),
    }


# ---- Part 7: Registration / Initialization -----------------------------

# (Optional) Module initialization flag
_initialized = False


def initialize_animation() -> None:
    """
    Perform any necessary one-time initialization for the animation package.
    This can include registering callbacks, clearing caches, or setting up
    progress bars. This function is idempotent and can be called multiple times.
    """
    global _initialized
    if _initialized:
        return
    logger.info("Initializing animation package")
    # Any global setup can go here
    _initialized = True


def shutdown_animation() -> None:
    """
    Perform any necessary cleanup before the package is unloaded.
    """
    global _initialized
    if not _initialized:
        return
    logger.info("Shutting down animation package")
    # Cleanup resources, remove callbacks, etc.
    _initialized = False


# ---- Part 8: Public API (__all__) ---------------------------------------

__all__ = [
    # ---- Managers ----
    "TimelineManager",
    "KeyframeManager",
    "CurveManager",
    "AnimationLayerManager",
    "ConstraintManager",
    "AnimationBaker",
    "BatchBaker",
    "AnimationCleanupManager",

    # ---- Timeline ----
    "TimelineRange",
    "TimelineMarker",
    "TimelineBookmark",
    "TimelineSnapshot",
    "TimelineDiagnostics",
    "TimelineStatistics",
    "TimeUnit",
    "PlaybackMode",
    "TimelineState",
    "get_current_frame",
    "set_current_frame",
    "get_frame_range",
    "set_frame_range",

    # ---- Keyframes ----
    "Keyframe",
    "KeySelection",
    "KeyClipboard",
    "KeyStatistics",
    "KeyReport",
    "KeyInterpolation",
    "KeySelectionMode",
    "TransformMode",

    # ---- Curves ----
    "AnimationCurve",
    "CurveSample",
    "CurveSegment",
    "CurveStats",
    "CurveReportObj",
    "CurveSelection",
    "CurveClipboard",
    "CurveType",
    "InterpolationMode",
    "FilterMode",
    "TangentType",

    # ---- Layers ----
    "AnimationLayer",
    "LayerSettings",
    "LayerStatistics",
    "LayerReport",
    "LayerState",
    "BlendMode",
    "LayerType",

    # ---- Constraints ----
    "Constraint",
    "ConstraintTarget",
    "ConstraintSettings",
    "ConstraintStatistics",
    "ConstraintReport",
    "ConstraintType",
    "MaintainOffset",
    "ConstraintState",

    # ---- Baking ----
    "BakeSettings",
    "BakeRange",
    "BakeResult",
    "BakeStatistics",
    "BakeReport",
    "BakeTask",
    "BakeQueue",
    "BakeMode",
    "BakeTarget",
    "RotationInterpolation",

    # ---- Cleanup ----
    "CleanupSettings",
    "CleanupTask",
    "CleanupResult",
    "CleanupStatistics",
    "ValidationIssue",
    "ValidationReport",
    "CleanupReport",
    "CleanupType",
    "OptimizationLevel",
    "ValidationState",
    "get_cleanup_presets",

    # ---- Exceptions ----
    "TimelineError",
    "InvalidFrameError",
    "InvalidRangeError",
    "KeyframeError",
    "KeyframeSelectionError",
    "KeyframeOperationError",
    "CurveError",
    "CurveNotFoundError",
    "CurveOperationError",
    "LayerError",
    "LayerNotFoundError",
    "LayerOperationError",
    "ConstraintError",
    "ConstraintNotFoundError",
    "ConstraintCreationError",
    "BakingError",
    "BakingCancelledError",
    "InvalidBakeTargetError",
    "BakeValidationError",
    "CleanupError",
    "CleanupValidationError",
    "CleanupOperationError",
    "CleanupCancelledError",

    # ---- Factories ----
    "create_timeline",
    "create_keyframes",
    "create_curves",
    "create_layers",
    "create_constraints",
    "create_baker",
    "create_cleanup",

    # ---- Package info ----
    "package_info",
    "is_supported_maya",
    "is_supported_python",
    "check_environment",
    "initialize_animation",
    "shutdown_animation",

    # ---- Metadata ----
    "PACKAGE_NAME",
    "VERSION",
    "AUTHOR",
    "LICENSE",
    "SUPPORTED_MAYA_VERSIONS",
    "SUPPORTED_PYTHON_VERSIONS",
]

# ---- Part 9: Module Initialization (optional) -------------------------

# Auto-initialize when package is imported?
# We'll leave it to the user to call initialize_animation explicitly.
# This keeps the import side-effect-free.

logger.debug("animation package loaded")