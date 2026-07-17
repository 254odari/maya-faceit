# -*- coding: utf-8 -*-
"""
tools/controllers/engine.py

Main facade for controller operations.
"""

import maya.cmds as cmds # type: ignore
from typing import List, Optional, Dict, Any, Tuple
from .types import (
    ControllerType, ControllerShape, ControllerAxis,
    ControllerInfo, ControllerPair, ControllerStats
)
from .settings import ControllerSettings, DEFAULT_CONTROLLER_SETTINGS


class ControllerEngine:
    """
    Main controller management engine.

    Provides methods for creating, editing, mirroring, and querying
    controllers.
    """

    def __init__(self, settings: Optional[ControllerSettings] = None):
        self.settings = settings or DEFAULT_CONTROLLER_SETTINGS

    # =========================================================================
    # CREATION
    # =========================================================================

    def create(self, name: str, shape: ControllerShape = ControllerShape.CIRCLE,
               size: float = 1.0, axis: ControllerAxis = ControllerAxis.Y,
               color: Optional[Tuple[float, float, float]] = None,
               position: Optional[Tuple[float, float, float]] = None) -> str:
        """
        Create a new controller.

        Args:
            name: Controller name.
            shape: Shape type.
            size: Size of the controller.
            axis: Orientation axis.
            color: RGB color (0-1).
            position: World position.

        Returns:
            Name of the created controller.
        """
        # Build full name
        full_name = f"{self.settings.naming_prefix}{name}{self.settings.naming_suffix}"

        # Create shape
        if shape == ControllerShape.CIRCLE:
            result = cmds.circle(r=size, nr=(axis == ControllerAxis.X, axis == ControllerAxis.Y, axis == ControllerAxis.Z),
                                 name=full_name)
        elif shape == ControllerShape.SQUARE:
            # Create a square using curve
            half = size / 2
            pts = [
                (-half, 0, -half),
                (-half, 0, half),
                (half, 0, half),
                (half, 0, -half),
                (-half, 0, -half),
            ]
            result = cmds.curve(d=1, p=pts, name=full_name)
        else:
            # Default: circle
            result = cmds.circle(r=size, nr=(axis == ControllerAxis.X, axis == ControllerAxis.Y, axis == ControllerAxis.Z),
                                 name=full_name)

        controller = result[0]

        # Set color
        if color:
            self.set_color(controller, color)
        elif self.settings.default_color:
            self.set_color(controller, self.settings.default_color)

        # Set position
        if position:
            cmds.xform(controller, ws=True, t=position)

        # Freeze transforms if requested
        if self.settings.freeze_on_create:
            cmds.makeIdentity(controller, apply=True, t=1, r=1, s=1, n=0)

        # Create offset group if requested
        if self.settings.create_offset_group:
            offset = cmds.createNode('transform', name=f"{controller}_offset")
            cmds.xform(offset, ws=True, matrix=cmds.xform(controller, q=True, ws=True, matrix=True))
            cmds.parent(controller, offset)

        # Auto-lock if requested
        if self.settings.auto_lock:
            self.lock(controller)

        return controller

    def create_from_shape(self, name: str, shape_node: str,
                          color: Optional[Tuple[float, float, float]] = None) -> str:
        """
        Create a controller using an existing NURBS shape.

        Args:
            name: Controller name.
            shape_node: Existing NURBS curve node.
            color: RGB color.

        Returns:
            Name of the created controller.
        """
        # Duplicate the shape
        dup = cmds.duplicate(shape_node, returnRootsOnly=True)[0]
        full_name = f"{self.settings.naming_prefix}{name}{self.settings.naming_suffix}"
        controller = cmds.rename(dup, full_name)
        if color:
            self.set_color(controller, color)
        return controller

    # =========================================================================
    # EDITING
    # =========================================================================

    def set_color(self, controller: str, color: Tuple[float, float, float]) -> bool:
        """Set the override color of a controller."""
        if not cmds.objExists(controller):
            return False
        cmds.setAttr(f"{controller}.overrideEnabled", 1)
        cmds.setAttr(f"{controller}.overrideRGBColors", 1)
        cmds.setAttr(f"{controller}.overrideColorR", color[0])
        cmds.setAttr(f"{controller}.overrideColorG", color[1])
        cmds.setAttr(f"{controller}.overrideColorB", color[2])
        return True

    def lock(self, controller: str) -> bool:
        """Lock a controller (prevent selection and editing)."""
        if not cmds.objExists(controller):
            return False
        attrs = ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"]
        for a in attrs:
            full = f"{controller}.{a}"
            if cmds.objExists(full):
                cmds.setAttr(full, lock=True, keyable=False)
        return True

    def unlock(self, controller: str) -> bool:
        """Unlock a controller."""
        if not cmds.objExists(controller):
            return False
        attrs = ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"]
        for a in attrs:
            full = f"{controller}.{a}"
            if cmds.objExists(full):
                cmds.setAttr(full, lock=False, keyable=True)
        return True

    def hide(self, controller: str) -> bool:
        """Hide a controller."""
        if not cmds.objExists(controller):
            return False
        cmds.setAttr(f"{controller}.visibility", 0)
        return True

    def show(self, controller: str) -> bool:
        """Show a controller."""
        if not cmds.objExists(controller):
            return False
        cmds.setAttr(f"{controller}.visibility", 1)
        return True

    # =========================================================================
    # QUERY
    # =========================================================================

    def get_info(self, controller: str) -> Optional[ControllerInfo]:
        """Get information about a controller."""
        if not cmds.objExists(controller):
            return None
        info = ControllerInfo(
            name=controller,
            long_name=cmds.ls(controller, long=True)[0],
            type=ControllerType.CUSTOM,
            shape=ControllerShape.CUSTOM,
            parent=cmds.listRelatives(controller, parent=True, fullPath=True)[0] if cmds.listRelatives(controller, parent=True) else None,
            children=cmds.listRelatives(controller, children=True, fullPath=True) or [],
            attributes=cmds.listAttr(controller, keyable=True) or [],
            locked=cmds.lockNode(controller, q=True, lock=True)[0],
            hidden=not cmds.getAttr(f"{controller}.visibility"),
        )
        return info

    def get_all_controllers(self) -> List[str]:
        """Get all controller nodes in the scene."""
        # Heuristic: transforms with NURBS shapes
        all_transforms = cmds.ls(type='transform', long=True)
        controllers = []
        for t in all_transforms:
            shapes = cmds.listRelatives(t, shapes=True, fullPath=True) or []
            for s in shapes:
                if cmds.nodeType(s) in ['nurbsCurve', 'nurbsSurface']:
                    controllers.append(t)
                    break
        return controllers

    # =========================================================================
    # MIRROR
    # =========================================================================

    def mirror(self, controller: str, axis: ControllerAxis = ControllerAxis.X) -> Optional[str]:
        """Mirror a controller to the opposite side."""
        # Placeholder – will use symmetry tools eventually
        return None

    # =========================================================================
    # UTILITY
    # =========================================================================

    def freeze(self, controller: str) -> bool:
        """Freeze transforms of a controller."""
        if not cmds.objExists(controller):
            return False
        cmds.makeIdentity(controller, apply=True, t=1, r=1, s=1, n=0)
        return True


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

controller = ControllerEngine()

__all__ = ["ControllerEngine", "controller"]