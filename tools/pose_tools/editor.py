# -*- coding: utf-8 -*-
"""
tools/pose_tools/editor.py

Low-level Maya operations for reading/writing pose data.
"""

import maya.cmds as cmds # type: ignore
from typing import List, Dict, Optional, Any, Set
from .types import PoseAttribute, Pose, PoseCategory, PoseType


class PoseEditor:
    """
    Low-level Maya operations for capturing and applying poses.
    """

    def __init__(self, settings):
        self.settings = settings

    # =========================================================================
    # CAPTURE POSE
    # =========================================================================

    def capture_from_scene(self, objects: Optional[List[str]] = None,
                           attributes: Optional[List[str]] = None) -> List[PoseAttribute]:
        """
        Capture current values from the scene.

        Args:
            objects: List of objects to capture from. If None, uses selected objects.
            attributes: List of specific attributes to capture. If None, captures all keyable.

        Returns:
            List of PoseAttribute objects.
        """
        if objects is None:
            objects = cmds.ls(selection=True, long=True)
            if not objects:
                return []

        if attributes is None:
            # Capture all keyable attributes on the objects
            attr_list = []
            for obj in objects:
                keyable = cmds.listAttr(obj, keyable=True) or []
                attr_list.extend([f"{obj}.{a}" for a in keyable])
        else:
            attr_list = attributes

        result = []
        for attr in attr_list:
            if not cmds.objExists(attr):
                continue
            try:
                value = cmds.getAttr(attr)
                # Determine type
                attr_type = "float"
                if isinstance(value, bool):
                    attr_type = "bool"
                elif isinstance(value, int):
                    attr_type = "int"
                elif isinstance(value, str):
                    attr_type = "string"
                # Handle enum
                if cmds.attributeQuery(attr.split('.')[-1], node=attr.split('.')[0], listEnum=True):
                    attr_type = "enum"
                result.append(PoseAttribute(name=attr, value=value, type=attr_type))
            except:
                pass

        return result

    def capture_controllers(self, controllers: List[str]) -> List[PoseAttribute]:
        """
        Capture controller transform values.
        """
        if not controllers:
            return []
        # Capture transform attributes (tx, ty, tz, rx, ry, rz, sx, sy, sz)
        attrs = []
        for ctrl in controllers:
            for a in ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"]:
                full = f"{ctrl}.{a}"
                if cmds.objExists(full):
                    try:
                        val = cmds.getAttr(full)
                        attrs.append(PoseAttribute(name=full, value=val, type="float"))
                    except:
                        pass
        return attrs

    def capture_blendshapes(self, blendshape_nodes: List[str]) -> List[PoseAttribute]:
        """
        Capture blendshape weights from specified nodes.
        """
        if not blendshape_nodes:
            return []
        attrs = []
        for node in blendshape_nodes:
            targets = cmds.listAttr(node, m=True, string="weight") or []
            for t in targets:
                full = f"{node}.{t}"
                try:
                    val = cmds.getAttr(full)
                    attrs.append(PoseAttribute(name=full, value=val, type="float"))
                except:
                    pass
        return attrs

    # =========================================================================
    # APPLY POSE
    # =========================================================================

    def apply_to_scene(self, attributes: List[PoseAttribute],
                       blend_factor: float = 1.0,
                       blend_mode: str = "overwrite") -> int:
        """
        Apply a list of pose attributes to the scene.

        Args:
            attributes: List of PoseAttribute objects.
            blend_factor: Blending factor (0-1).
            blend_mode: "overwrite", "add", "subtract", "average", "max", "min".

        Returns:
            Number of attributes modified.
        """
        modified = 0
        for attr in attributes:
            if not cmds.objExists(attr.name):
                continue
            # Get current value
            try:
                current = cmds.getAttr(attr.name)
            except:
                continue

            # Compute new value based on blend mode
            if blend_mode == "overwrite":
                new_val = attr.value
            elif blend_mode == "add":
                new_val = current + attr.value * blend_factor
            elif blend_mode == "subtract":
                new_val = current - attr.value * blend_factor
            elif blend_mode == "average":
                new_val = (current + attr.value) * 0.5
            elif blend_mode == "max":
                new_val = max(current, attr.value)
            elif blend_mode == "min":
                new_val = min(current, attr.value)
            else:
                new_val = attr.value

            # Apply blending factor if not overwrite
            if blend_mode != "overwrite":
                new_val = current + (new_val - current) * blend_factor

            # Clamp if needed (only for float attributes in 0-1 range)
            if self.settings.auto_clamp:
                if attr.type == "float":
                    if -1.0 <= current <= 1.0:
                        new_val = max(self.settings.clamp_min, min(self.settings.clamp_max, new_val))
                    # For transforms, clamping might not be desired
                elif attr.type == "bool":
                    new_val = bool(new_val)

            # Set the value
            try:
                cmds.setAttr(attr.name, new_val)
                modified += 1
            except:
                pass

        return modified

    # =========================================================================
    # UTILITY
    # =========================================================================

    def get_controller_list(self) -> List[str]:
        """Get all controllers in the scene (heuristic)."""
        all_transforms = cmds.ls(type='transform', long=True)
        controllers = []
        for t in all_transforms:
            shapes = cmds.listRelatives(t, shapes=True) or []
            if shapes and any(cmds.nodeType(s) in ['nurbsCurve', 'nurbsSurface'] for s in shapes):
                controllers.append(t)
        return controllers

    def get_blendshape_nodes(self) -> List[str]:
        """Get all blendshape nodes in the scene."""
        return cmds.ls(type='blendShape', long=True)