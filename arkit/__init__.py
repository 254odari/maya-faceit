"""
maya_faceit.blendshapes.arkit

Apple ARKit facial animation toolkit.

This package provides a comprehensive set of tools for working with Apple ARKit
facial blendshapes in a Maya‑independent manner. It is the core of the
maya_faceit facial animation pipeline.

Modules
-------
- arkit52.py          : Canonical ARKit blendshape definitions.
- mapper.py           : Runtime mapping from ARKit coefficients to rig weights.
- remapper.py         : Transform one mapping definition into another.
- validator.py        : Validate all ARKit data (coefficients, mappings, poses, etc.).
- pose_generator.py   : Procedural generation of facial poses.
- pose_library.py     : Persistent repository and management of poses.
- expression_sets.py  : High‑level expression templates (emotions, visemes, etc.).
- calibration.py      : Personalization and normalization of performer data.

The package is designed to be used by other modules (such as Maya adapters)
without exposing internal implementation details.
"""

from __future__ import annotations

import logging

# ---- Part 1: Version and Metadata ----------------------------------------

PACKAGE_NAME = "maya_faceit.blendshapes.arkit"
VERSION = "1.0.0"
AUTHOR = "Maya FaceIT Team"
LICENSE = "MIT"
ARKIT_VERSION = "Apple ARKit 52"

# ---- Part 2: Configure Logging (optional, but good practice) ------------

logger = logging.getLogger(__name__)

# ---- Part 3: Import Public APIs from Submodules ------------------------

# 3.1 Constants from arkit52
from .arkit52 import (
    ARKIT_BLENDSHAPES,
    ARKIT_SET,
    ARKIT_INDEX,
    BLENDSHAPE_COUNT,
    DEFAULT_VALUE,
    MIN_WEIGHT,
    MAX_WEIGHT,
    SUPPORTED_WEIGHT_RANGE,
    LEFT_RIGHT_PAIRS,
    FACIAL_REGIONS,
    EXPRESSION_CATEGORIES,
)

# 3.2 Mapping Engine
from .mapper import (
    ARKitMapper,
    MappingRule,
    CompiledMapping,
    EvaluationResult,
    MappingDefinitionError,
    EvaluationError,
)

# 3.3 Remapper
from .remapper import (
    ARKitRemapper,
    RenameRule,
    MirrorRule,
    RemapResult,
    RemapStatistics,
    RemapDefinitionError,
)

# 3.4 Validator
from .validator import (
    ARKitValidator,
    ValidationLevel,
    ValidationReport,
    ValidationIssue,
    ARKitValidationError,
)

# 3.5 Pose Generator
from .pose_generator import (
    PoseGenerator,
    Pose,
    PoseFrame,
    PoseSequence,
    ExpressionTemplate,
    PoseBlend,
    ARKitPoseGeneratorError,
    ExpressionTemplateError,
    PoseBlendError,
)

# 3.6 Pose Library
from .pose_library import (
    PoseLibrary,
    PoseEntry,
    PoseMetadata,
    LibraryStatistics,
    LibraryDiagnostics,
    ARKitPoseLibraryError,
    PoseNotFoundError,
    DuplicatePoseError,
    InvalidPoseError,
    SerializationError,
)

# 3.7 Expression Sets
from .expression_sets import (
    ExpressionSets,
    Expression,
    ExpressionMetadata,
    ExpressionGroup,
    ExpressionRegistry,
    BuiltinExpressions,
    ARKitExpressionError,
    ExpressionNotFoundError,
    DuplicateExpressionError,
)

# 3.8 Calibration
from .calibration import (
    CalibrationManager,
    CalibrationProfile,
    ChannelCalibration,
    GainCurve,
    ARKitCalibrationError,
    CalibrationProfileError,
    CalibrationDataError,
    CalibrationStateError,
)

# ---- Part 4: Convenience Factory Functions -----------------------------

def create_mapper(mapping_def=None, mirror_map=None, normalize=False, **kwargs):
    """
    Create an ARKitMapper instance with optional initial mapping.

    Returns:
        ARKitMapper
    """
    return ARKitMapper(mapping_def, mirror_map, normalize, **kwargs)


def create_validator(collect_stats=True):
    """
    Create an ARKitValidator instance.

    Args:
        collect_stats: whether to accumulate statistics.

    Returns:
        ARKitValidator
    """
    return ARKitValidator(collect_stats=collect_stats)


def create_pose_library(root_path=None, builtin_path=None, load_on_init=True, use_validator=True):
    """
    Create a PoseLibrary instance.

    Returns:
        PoseLibrary
    """
    return PoseLibrary(root_path, builtin_path, load_on_init, use_validator)


def create_calibration():
    """
    Create a CalibrationManager instance.

    Returns:
        CalibrationManager
    """
    return CalibrationManager()


def create_expression_sets(load_builtin=True):
    """
    Create an ExpressionSets instance.

    Returns:
        ExpressionSets
    """
    return ExpressionSets(load_builtin=load_builtin)


# ---- Part 5: Package Information ---------------------------------------

def package_info():
    """
    Return a dictionary containing package metadata.

    Returns:
        dict: {
            'package': str,
            'version': str,
            'author': str,
            'license': str,
            'blendshape_count': int,
            'modules': list[str]
        }
    """
    return {
        "package": PACKAGE_NAME,
        "version": VERSION,
        "author": AUTHOR,
        "license": LICENSE,
        "blendshape_count": BLENDSHAPE_COUNT,
        "modules": [
            "arkit52",
            "mapper",
            "remapper",
            "validator",
            "pose_generator",
            "pose_library",
            "expression_sets",
            "calibration",
        ],
    }


# ---- Part 6: Public API (__all__) ---------------------------------------

__all__ = [
    # ---- Constants ----
    "ARKIT_BLENDSHAPES",
    "ARKIT_SET",
    "ARKIT_INDEX",
    "BLENDSHAPE_COUNT",
    "DEFAULT_VALUE",
    "MIN_WEIGHT",
    "MAX_WEIGHT",
    "SUPPORTED_WEIGHT_RANGE",
    "LEFT_RIGHT_PAIRS",
    "FACIAL_REGIONS",
    "EXPRESSION_CATEGORIES",
    "VERSION",
    "ARKIT_VERSION",

    # ---- Mapper ----
    "ARKitMapper",
    "MappingRule",
    "CompiledMapping",
    "EvaluationResult",
    "MappingDefinitionError",
    "EvaluationError",

    # ---- Remapper ----
    "ARKitRemapper",
    "RenameRule",
    "MirrorRule",
    "RemapResult",
    "RemapStatistics",
    "RemapDefinitionError",

    # ---- Validator ----
    "ARKitValidator",
    "ValidationLevel",
    "ValidationReport",
    "ValidationIssue",
    "ARKitValidationError",

    # ---- Pose Generator ----
    "PoseGenerator",
    "Pose",
    "PoseFrame",
    "PoseSequence",
    "ExpressionTemplate",
    "PoseBlend",
    "ARKitPoseGeneratorError",
    "ExpressionTemplateError",
    "PoseBlendError",

    # ---- Pose Library ----
    "PoseLibrary",
    "PoseEntry",
    "PoseMetadata",
    "LibraryStatistics",
    "LibraryDiagnostics",
    "ARKitPoseLibraryError",
    "PoseNotFoundError",
    "DuplicatePoseError",
    "InvalidPoseError",
    "SerializationError",

    # ---- Expression Sets ----
    "ExpressionSets",
    "Expression",
    "ExpressionMetadata",
    "ExpressionGroup",
    "ExpressionRegistry",
    "BuiltinExpressions",
    "ARKitExpressionError",
    "ExpressionNotFoundError",
    "DuplicateExpressionError",

    # ---- Calibration ----
    "CalibrationManager",
    "CalibrationProfile",
    "ChannelCalibration",
    "GainCurve",
    "ARKitCalibrationError",
    "CalibrationProfileError",
    "CalibrationDataError",
    "CalibrationStateError",

    # ---- Factories ----
    "create_mapper",
    "create_validator",
    "create_pose_library",
    "create_calibration",
    "create_expression_sets",

    # ---- Utilities ----
    "package_info",
]

# ---- Part 7: Version info for setuptools (optional) --------------------

try:
    from _version import version as __version__
except ImportError:
    __version__ = VERSION

# End of __init__.py