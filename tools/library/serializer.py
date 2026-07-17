# -*- coding: utf-8 -*-
"""
tools/library/serializer.py

Serialization for library data (shapes, presets).
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from .shapes import ShapeDefinition, ShapeRegistry
from .presets import Preset, PresetLibrary, PresetCategory


class LibrarySerializer:
    """Serializes/deserializes library data to/from JSON."""

    @staticmethod
    def serialize_preset(preset: Preset) -> Dict[str, Any]:
        """Convert a Preset to a JSON-serializable dict."""
        return {
            "name": preset.name,
            "category": preset.category.value,
            "description": preset.description,
            "controllers": preset.controllers,
            "blendshapes": preset.blendshapes,
            "tags": preset.tags,
            "author": preset.author,
            "metadata": preset.metadata,
        }

    @staticmethod
    def deserialize_preset(data: Dict[str, Any]) -> Preset:
        """Convert a dict to a Preset."""
        return Preset(
            name=data["name"],
            category=PresetCategory(data.get("category", "custom")),
            description=data.get("description", ""),
            controllers=data.get("controllers", {}),
            blendshapes=data.get("blendshapes", {}),
            tags=data.get("tags", []),
            author=data.get("author", "unknown"),
            metadata=data.get("metadata", {}),
        )

    @staticmethod
    def serialize_shape(shape_def: ShapeDefinition) -> Dict[str, Any]:
        """Convert a ShapeDefinition to a dict (without the callable)."""
        return {
            "name": shape_def.name,
            "description": shape_def.description,
            "category": shape_def.category,
            "tags": shape_def.tags,
            # create_func is not serialized
            "metadata": shape_def.metadata,
        }

    @staticmethod
    def deserialize_shape(data: Dict[str, Any]) -> ShapeDefinition:
        """Convert a dict to a ShapeDefinition (without create_func)."""
        return ShapeDefinition(
            name=data["name"],
            description=data.get("description", ""),
            category=data.get("category", "General"),
            tags=data.get("tags", []),
            create_func=None,
            metadata=data.get("metadata", {}),
        )

    @staticmethod
    def save_to_file(data: Any, filepath: Union[str, Path], pretty: bool = True) -> bool:
        """Save data to a JSON file."""
        try:
            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                if pretty:
                    json.dump(data, f, indent=2, default=str)
                else:
                    json.dump(data, f, default=str)
            return True
        except Exception as e:
            print(f"Error saving library data: {e}")
            return False

    @staticmethod
    def load_from_file(filepath: Union[str, Path]) -> Optional[Any]:
        """Load data from a JSON file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading library data: {e}")
            return None


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def serialize_library(presets: Optional[List[Preset]] = None,
                      shapes: Optional[List[ShapeDefinition]] = None) -> Dict[str, Any]:
    """
    Serialize entire library (presets and shapes) to a dict.

    Args:
        presets: List of Preset objects. If None, uses all registered.
        shapes: List of ShapeDefinition objects. If None, uses all registered.

    Returns:
        Dict with 'presets' and 'shapes' keys.
    """
    if presets is None:
        presets = PresetLibrary.list()
    if shapes is None:
        shapes = ShapeRegistry.list()

    data = {
        "presets": [LibrarySerializer.serialize_preset(p) for p in presets],
        "shapes": [LibrarySerializer.serialize_shape(s) for s in shapes],
    }
    return data


def deserialize_library(data: Dict[str, Any]) -> None:
    """
    Deserialize library data and register presets/shapes.

    Args:
        data: Dict from serialize_library.
    """
    # Load presets
    for pdata in data.get("presets", []):
        preset = LibrarySerializer.deserialize_preset(pdata)
        PresetLibrary.register(preset)

    # Load shapes (create_func remains None, but metadata is preserved)
    for sdata in data.get("shapes", []):
        shape_def = LibrarySerializer.deserialize_shape(sdata)
        ShapeRegistry.register(shape_def)


def load_library_from_file(filepath: Union[str, Path]) -> bool:
    """Load and register library from a JSON file."""
    data = LibrarySerializer.load_from_file(filepath)
    if data is None:
        return False
    deserialize_library(data)
    return True


def save_library_to_file(filepath: Union[str, Path],
                         presets: Optional[List[Preset]] = None,
                         shapes: Optional[List[ShapeDefinition]] = None) -> bool:
    """Save library to a JSON file."""
    data = serialize_library(presets, shapes)
    return LibrarySerializer.save_to_file(data, filepath)