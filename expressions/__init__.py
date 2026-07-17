"""
maya_faceit.expression

Expression management package for Maya FaceIT.

This package provides a complete system for creating, editing, managing, and
previewing facial expressions. It includes:
- ExpressionManager: High-level controller.
- ExpressionGenerator: Generate expressions from built-in or custom definitions.
- ExpressionEditor: Edit expressions (rename, duplicate, delete, update).
- ExpressionInterpolator: Blend and interpolate expressions.
- ExpressionMirror: Mirror expressions left/right.
- ExpressionLibrary: Persistent storage and organization.
- ExpressionSerializer: Import/export to JSON, binary, YAML.
- ExpressionPreview: Viewport preview and thumbnail generation.
- PresetManager: Built-in preset expressions.

Dependencies:
- blendshapes package for blendshape operations.
- arkit package for ARKit mapping.

Author: Maya FaceIT Team
"""

from __future__ import annotations

import logging

# Version
__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"
__license__ = "MIT"

PACKAGE_NAME = "maya_faceit.expression"
VERSION = __version__
AUTHOR = __author__

# ---- Public Imports ----

# Manager (high-level API)
from .manager import (
    ExpressionManager,
    ExpressionManagerError,
)

# Generator
from .generator import (
    ExpressionGenerator,
    ExpressionDefinition,
    ExpressionResult,
    ExpressionType,
    GenerationMode,
    ExpressionError,
    ExpressionNotFoundError,
    ExpressionGenerationError,
)

# Editor
from .editor import (
    ExpressionEditor,
    ExpressionEditorError,
    ExpressionEditorValidationError,
)

# Interpolation
from .interpolation import (
    ExpressionInterpolator,
    InterpolationMode,
    InterpolationError,
    ease_in,
    ease_out,
    ease_in_out,
    cubic_bezier,
)

# Mirror
from .mirror import (
    ExpressionMirror,
    ExpressionMirrorError,
)

# Library
from .library import (
    ExpressionLibrary,
    ExpressionEntry,
    ExpressionMetadata,
    ExpressionLibraryError,
    ExpressionNotFoundError as LibraryNotFoundError,
    DuplicateExpressionError,
    LibraryIOError,
)

# Presets
from .presets import (
    PresetManager,
    PresetError,
)

# Serializer
from .serializer import (
    ExpressionSerializer,
    SerializationError,
    UnsupportedFormatError,
    ValidationError as SerializerValidationError,
    ImportError as SerializerImportError,
    save,
    load,
    serialize,
    deserialize,
)

# Preview
from .preview import (
    ExpressionPreview,
    PreviewMode,
    PreviewError,
)

# ---- Factory Functions ----

def create_expression_manager() -> ExpressionManager:
    """
    Create a new ExpressionManager instance with default settings.

    Returns:
        ExpressionManager: A fully configured expression manager.
    """
    return ExpressionManager()


def create_expression_library() -> ExpressionLibrary:
    """
    Create a new ExpressionLibrary instance.

    Returns:
        ExpressionLibrary: A new expression library.
    """
    return ExpressionLibrary()


def create_preset_manager() -> PresetManager:
    """
    Create a new PresetManager instance.

    Returns:
        PresetManager: A new preset manager.
    """
    return PresetManager()


# ---- Package Information ----

def package_info() -> dict:
    """
    Return package metadata and information.

    Returns:
        dict: Package name, version, author, and submodules.
    """
    return {
        "package": PACKAGE_NAME,
        "version": VERSION,
        "author": AUTHOR,
        "license": __license__,
        "submodules": [
            "manager",
            "generator",
            "editor",
            "interpolation",
            "mirror",
            "library",
            "presets",
            "serializer",
            "preview",
        ],
    }


# ---- Public API ----

__all__ = [
    # ---- Managers ----
    "ExpressionManager",
    "ExpressionGenerator",
    "ExpressionEditor",
    "ExpressionInterpolator",
    "ExpressionMirror",
    "ExpressionLibrary",
    "ExpressionSerializer",
    "ExpressionPreview",
    "PresetManager",

    # ---- Data Classes ----
    "ExpressionDefinition",
    "ExpressionResult",
    "ExpressionType",
    "GenerationMode",
    "ExpressionEntry",
    "ExpressionMetadata",
    "InterpolationMode",
    "PreviewMode",

    # ---- Exceptions ----
    "ExpressionManagerError",
    "ExpressionError",
    "ExpressionNotFoundError",
    "ExpressionGenerationError",
    "ExpressionEditorError",
    "ExpressionEditorValidationError",
    "InterpolationError",
    "ExpressionMirrorError",
    "ExpressionLibraryError",
    "LibraryNotFoundError",
    "DuplicateExpressionError",
    "LibraryIOError",
    "PresetError",
    "SerializationError",
    "UnsupportedFormatError",
    "SerializerValidationError",
    "SerializerImportError",
    "PreviewError",

    # ---- Utility Functions ----
    "save",
    "load",
    "serialize",
    "deserialize",
    "ease_in",
    "ease_out",
    "ease_in_out",
    "cubic_bezier",

    # ---- Factories ----
    "create_expression_manager",
    "create_expression_library",
    "create_preset_manager",

    # ---- Package Info ----
    "package_info",

    # ---- Metadata ----
    "PACKAGE_NAME",
    "VERSION",
    "AUTHOR",
    "__version__",
]

# ---- Module Initialization ----

logger = logging.getLogger(__name__)
logger.debug("Expression package loaded.")