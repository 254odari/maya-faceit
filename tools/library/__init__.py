# -*- coding: utf-8 -*-
"""
tools/library
~~~~~~~~~~~~~

Library for reusable controller shapes and facial presets.

Provides:
- Built-in controller shape library (shapes.py)
- Expression/pose presets (presets.py)
- Serialization (serializer.py)
"""

from .shapes import (
    ShapeLibrary,
    ShapeRegistry,
    get_shape,
    list_shapes,
    create_shape,
    register_shape,
    load_shape_from_file,
    export_shape,
    SHAPES,
)
from .presets import (
    PresetLibrary,
    Preset,
    PresetCategory,
    get_preset,
    list_presets,
    apply_preset,
    save_preset,
    delete_preset,
    load_preset_from_file,
    export_preset,
)
from .serializer import (
    LibrarySerializer,
    serialize_library,
    deserialize_library,
    load_library_from_file,
    save_library_to_file,
)

__all__ = [
    # Shapes
    "ShapeLibrary",
    "ShapeRegistry",
    "get_shape",
    "list_shapes",
    "create_shape",
    "register_shape",
    "load_shape_from_file",
    "export_shape",
    "SHAPES",
    # Presets
    "PresetLibrary",
    "Preset",
    "PresetCategory",
    "get_preset",
    "list_presets",
    "apply_preset",
    "save_preset",
    "delete_preset",
    "load_preset_from_file",
    "export_preset",
    # Serializer
    "LibrarySerializer",
    "serialize_library",
    "deserialize_library",
    "load_library_from_file",
    "save_library_to_file",
]