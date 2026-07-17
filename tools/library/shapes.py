# -*- coding: utf-8 -*-
"""
tools/library/shapes.py

Built_in controller shape library.
"""

import maya.cmds as cmds # type: ignore
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field

# =============================================================================
# DATA MODEL
# =============================================================================

@dataclass
class ShapeDefinition:
    """Definition of a controller shape."""
    name: str
    description: str = ""
    category: str = "General"
    tags: List[str] = field(default_factory=list)
    create_func: Optional[Callable] = None
    preview: Optional[str] = None  # path to preview image
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# SHAPE REGISTRY
# =============================================================================

class ShapeRegistry:
    """Registry of available controller shapes."""

    _shapes: Dict[str, ShapeDefinition] = {}

    @classmethod
    def register(cls, definition: ShapeDefinition) -> None:
        """Register a new shape definition."""
        cls._shapes[definition.name] = definition

    @classmethod
    def get(cls, name: str) -> Optional[ShapeDefinition]:
        """Get a shape definition by name."""
        return cls._shapes.get(name)

    @classmethod
    def list(cls, category: Optional[str] = None) -> List[ShapeDefinition]:
        """List all shapes, optionally filtered by category."""
        if category:
            return [s for s in cls._shapes.values() if s.category == category]
        return list(cls._shapes.values())

    @classmethod
    def clear(cls) -> None:
        """Clear all registered shapes."""
        cls._shapes.clear()


# =============================================================================
# SHAPE CREATION FUNCTIONS
# =============================================================================

def _create_circle(name: str, size: float = 1.0, axis: str = "y",
                   color: Optional[Tuple[float, float, float]] = None) -> str:
    """Create a NURBS circle controller."""
    axis_vec = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}
    result = cmds.circle(r=size, nr=axis_vec.get(axis, (0, 1, 0)), name=name)
    controller = result[0]
    if color:
        cmds.setAttr(f"{controller}.overrideEnabled", 1)
        cmds.setAttr(f"{controller}.overrideRGBColors", 1)
        cmds.setAttr(f"{controller}.overrideColorR", color[0])
        cmds.setAttr(f"{controller}.overrideColorG", color[1])
        cmds.setAttr(f"{controller}.overrideColorB", color[2])
    return controller


def _create_square(name: str, size: float = 1.0, axis: str = "y",
                   color: Optional[Tuple[float, float, float]] = None) -> str:
    """Create a NURBS square controller."""
    half = size / 2
    # Determine plane
    if axis == "y":
        pts = [(-half, 0, -half), (-half, 0, half), (half, 0, half), (half, 0, -half), (-half, 0, -half)]
    elif axis == "x":
        pts = [(0, -half, -half), (0, -half, half), (0, half, half), (0, half, -half), (0, -half, -half)]
    else:  # z
        pts = [(-half, -half, 0), (-half, half, 0), (half, half, 0), (half, -half, 0), (-half, -half, 0)]
    controller = cmds.curve(d=1, p=pts, name=name)
    if color:
        cmds.setAttr(f"{controller}.overrideEnabled", 1)
        cmds.setAttr(f"{controller}.overrideRGBColors", 1)
        cmds.setAttr(f"{controller}.overrideColorR", color[0])
        cmds.setAttr(f"{controller}.overrideColorG", color[1])
        cmds.setAttr(f"{controller}.overrideColorB", color[2])
    return controller


def _create_triangle(name: str, size: float = 1.0, axis: str = "y",
                     color: Optional[Tuple[float, float, float]] = None) -> str:
    """Create a NURBS triangle controller."""
    half = size / 2
    h = size * 0.866  # height of equilateral triangle
    # Determine plane
    if axis == "y":
        pts = [(-half, 0, -h/2), (0, 0, h/2), (half, 0, -h/2), (-half, 0, -h/2)]
    elif axis == "x":
        pts = [(0, -half, -h/2), (0, 0, h/2), (0, half, -h/2), (0, -half, -h/2)]
    else:
        pts = [(-half, -h/2, 0), (0, h/2, 0), (half, -h/2, 0), (-half, -h/2, 0)]
    controller = cmds.curve(d=1, p=pts, name=name)
    if color:
        cmds.setAttr(f"{controller}.overrideEnabled", 1)
        cmds.setAttr(f"{controller}.overrideRGBColors", 1)
        cmds.setAttr(f"{controller}.overrideColorR", color[0])
        cmds.setAttr(f"{controller}.overrideColorG", color[1])
        cmds.setAttr(f"{controller}.overrideColorB", color[2])
    return controller


def _create_diamond(name: str, size: float = 1.0, axis: str = "y",
                    color: Optional[Tuple[float, float, float]] = None) -> str:
    """Create a NURBS diamond (rhombus) controller."""
    half = size / 2
    if axis == "y":
        pts = [(0, 0, -half), (-half, 0, 0), (0, 0, half), (half, 0, 0), (0, 0, -half)]
    elif axis == "x":
        pts = [(0, 0, -half), (0, -half, 0), (0, 0, half), (0, half, 0), (0, 0, -half)]
    else:
        pts = [(-half, 0, 0), (0, -half, 0), (half, 0, 0), (0, half, 0), (-half, 0, 0)]
    controller = cmds.curve(d=1, p=pts, name=name)
    if color:
        cmds.setAttr(f"{controller}.overrideEnabled", 1)
        cmds.setAttr(f"{controller}.overrideRGBColors", 1)
        cmds.setAttr(f"{controller}.overrideColorR", color[0])
        cmds.setAttr(f"{controller}.overrideColorG", color[1])
        cmds.setAttr(f"{controller}.overrideColorB", color[2])
    return controller


def _create_cross(name: str, size: float = 1.0, axis: str = "y",
                  color: Optional[Tuple[float, float, float]] = None) -> str:
    """Create a NURBS cross controller."""
    half = size / 2
    thickness = size * 0.2
    # Build cross points
    if axis == "y":
        pts = [
            (-thickness, 0, -half), (-thickness, 0, -thickness),
            (-half, 0, -thickness), (-half, 0, thickness),
            (-thickness, 0, thickness), (-thickness, 0, half),
            (thickness, 0, half), (thickness, 0, thickness),
            (half, 0, thickness), (half, 0, -thickness),
            (thickness, 0, -thickness), (thickness, 0, -half),
            (-thickness, 0, -half),
        ]
    elif axis == "x":
        pts = [
            (-half, -thickness, 0), (-thickness, -thickness, 0),
            (-thickness, -half, 0), (thickness, -half, 0),
            (thickness, -thickness, 0), (half, -thickness, 0),
            (half, thickness, 0), (thickness, thickness, 0),
            (thickness, half, 0), (-thickness, half, 0),
            (-thickness, thickness, 0), (-half, thickness, 0),
            (-half, -thickness, 0),
        ]
    else:
        pts = [
            (-half, -thickness, 0), (-thickness, -thickness, 0),
            (-thickness, -half, 0), (thickness, -half, 0),
            (thickness, -thickness, 0), (half, -thickness, 0),
            (half, thickness, 0), (thickness, thickness, 0),
            (thickness, half, 0), (-thickness, half, 0),
            (-thickness, thickness, 0), (-half, thickness, 0),
            (-half, -thickness, 0),
        ]
    controller = cmds.curve(d=1, p=pts, name=name)
    if color:
        cmds.setAttr(f"{controller}.overrideEnabled", 1)
        cmds.setAttr(f"{controller}.overrideRGBColors", 1)
        cmds.setAttr(f"{controller}.overrideColorR", color[0])
        cmds.setAttr(f"{controller}.overrideColorG", color[1])
        cmds.setAttr(f"{controller}.overrideColorB", color[2])
    return controller


def _create_arrow(name: str, size: float = 1.0, axis: str = "y",
                  color: Optional[Tuple[float, float, float]] = None) -> str:
    """Create a NURBS arrow controller."""
    half = size / 2
    head_len = size * 0.3
    head_width = size * 0.2
    shaft_len = size * 0.6
    shaft_width = size * 0.08
    # Arrow in Y axis by default
    if axis == "y":
        pts = [
            (0, 0, -shaft_width/2), (0, shaft_len, -shaft_width/2),
            (-head_width/2, shaft_len, -head_width/2),
            (-head_width/2, shaft_len + head_len, 0),
            (0, shaft_len + head_len, head_width/2),
            (head_width/2, shaft_len + head_len, 0),
            (head_width/2, shaft_len, head_width/2),
            (0, shaft_len, head_width/2),
            (0, 0, head_width/2),
            (0, 0, -shaft_width/2),
        ]
    elif axis == "x":
        pts = [
            (-shaft_width/2, 0, 0), (shaft_len, 0, 0),
            (shaft_len, 0, -head_width/2), (shaft_len + head_len, 0, 0),
            (shaft_len, 0, head_width/2), (shaft_len, 0, 0),
            (shaft_len, 0, 0), (-shaft_width/2, 0, 0),
        ]
    else:
        pts = [
            (0, -shaft_width/2, 0), (0, shaft_len, 0),
            (0, shaft_len, -head_width/2), (0, shaft_len + head_len, 0),
            (0, shaft_len, head_width/2), (0, shaft_len, 0),
            (0, -shaft_width/2, 0),
        ]
    controller = cmds.curve(d=1, p=pts, name=name)
    if color:
        cmds.setAttr(f"{controller}.overrideEnabled", 1)
        cmds.setAttr(f"{controller}.overrideRGBColors", 1)
        cmds.setAttr(f"{controller}.overrideColorR", color[0])
        cmds.setAttr(f"{controller}.overrideColorG", color[1])
        cmds.setAttr(f"{controller}.overrideColorB", color[2])
    return controller


# =============================================================================
# BUILT‑IN SHAPES REGISTRATION
# =============================================================================

SHAPES = {
    "circle": ShapeDefinition(
        name="circle",
        description="Standard circular controller",
        category="Basic",
        create_func=_create_circle,
    ),
    "square": ShapeDefinition(
        name="square",
        description="Square controller",
        category="Basic",
        create_func=_create_square,
    ),
    "triangle": ShapeDefinition(
        name="triangle",
        description="Triangular controller",
        category="Basic",
        create_func=_create_triangle,
    ),
    "diamond": ShapeDefinition(
        name="diamond",
        description="Diamond (rhombus) controller",
        category="Basic",
        create_func=_create_diamond,
    ),
    "cross": ShapeDefinition(
        name="cross",
        description="Cross-shaped controller",
        category="Basic",
        create_func=_create_cross,
    ),
    "arrow": ShapeDefinition(
        name="arrow",
        description="Arrow controller",
        category="Basic",
        create_func=_create_arrow,
    ),
}

# Register all shapes
for shape_def in SHAPES.values():
    ShapeRegistry.register(shape_def)


# =============================================================================
# PUBLIC API
# =============================================================================

def get_shape(name: str) -> Optional[ShapeDefinition]:
    """Get a shape definition by name."""
    return ShapeRegistry.get(name)


def list_shapes(category: Optional[str] = None) -> List[ShapeDefinition]:
    """List all shapes, optionally filtered by category."""
    return ShapeRegistry.list(category)


def create_shape(name: str, controller_name: str, size: float = 1.0,
                 axis: str = "y",
                 color: Optional[Tuple[float, float, float]] = None) -> Optional[str]:
    """
    Create a controller using a registered shape.

    Args:
        name: Shape name (e.g., "circle").
        controller_name: Name for the new controller.
        size: Size of the controller.
        axis: Axis of the controller ("x", "y", "z").
        color: RGB color (0-1).

    Returns:
        Name of the created controller, or None if shape not found.
    """
    shape_def = ShapeRegistry.get(name)
    if not shape_def or not shape_def.create_func:
        return None
    return shape_def.create_func(controller_name, size, axis, color)


def register_shape(definition: ShapeDefinition) -> None:
    """Register a custom shape."""
    ShapeRegistry.register(definition)


def load_shape_from_file(filepath: str, name: Optional[str] = None) -> Optional[ShapeDefinition]:
    """
    Load a shape definition from a file (JSON or Maya scene).
    (Placeholder - not fully implemented)
    """
    # This would parse a file and create a ShapeDefinition.
    # For now, return None.
    return None


def export_shape(shape_name: str, filepath: str) -> bool:
    """
    Export a shape definition to a file.
    (Placeholder - not fully implemented)
    """
    return False


# Alias for convenience
ShapeLibrary = ShapeRegistry