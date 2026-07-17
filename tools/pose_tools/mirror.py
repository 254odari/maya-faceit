# -*- coding: utf-8 -*-
"""
tools/pose_tools/mirror.py

Pose mirroring utilities.
"""

import maya.cmds as cmds # type: ignore
from typing import Optional, Dict, List
from .types import Pose, PoseAttribute
from .editor import PoseEditor
from .manager import PoseManager
from ..mirror import MirrorNameResolver


class PoseMirror:
    """
    Mirror poses using naming conventions.
    """

    def __init__(self, editor: PoseEditor, manager: PoseManager):
        self.editor = editor
        self.manager = manager
        self.name_resolver = MirrorNameResolver()

    def mirror_pose(self, name: str, result_name: Optional[str] = None,
                    axis: str = "x") -> Optional[Pose]:
        """
        Mirror a pose.

        Args:
            name: Name of the pose to mirror.
            result_name: Name for the mirrored pose. If None, uses "{name}_mirror".
            axis: Axis to mirror across ("x", "y", "z").

        Returns:
            The mirrored Pose.
        """
        pose = self.manager.get_pose(name)
        if not pose:
            return None

        if result_name is None:
            result_name = f"{name}_mirror"

        # Mirror each attribute
        mirrored_attrs = []
        for attr in pose.attributes:
            # Check if attribute is a controller transform
            if attr.name.endswith(("tx", "ty", "tz", "rx", "ry", "rz")):
                # Try to resolve mirror name
                node, attr_name = attr.name.split('.')
                mirror_node = self.name_resolver.get_mirror_name(node)
                if mirror_node:
                    new_name = f"{mirror_node}.{attr_name}"
                    # Mirror the value
                    val = self._mirror_value(attr.value, attr_name, axis)
                    mirrored_attrs.append(PoseAttribute(name=new_name, value=val, type=attr.type))
                else:
                    # If no mirror, copy as is
                    mirrored_attrs.append(attr)
            else:
                # Non-transform attributes are copied as is
                mirrored_attrs.append(attr)

        # Create the mirrored pose
        attr_dicts = [{"name": a.name, "value": a.value, "type": a.type} for a in mirrored_attrs]
        return self.manager.create_pose(
            name=result_name,
            attributes=attr_dicts,
            category=pose.category,
            description=f"Mirror of {name}",
            tags=["mirrored"]
        )

    def _mirror_value(self, value: float, attr_name: str, axis: str) -> float:
        """Mirror a single value based on attribute type and axis."""
        # Determine if it's translation, rotation, or scale
        if attr_name.startswith("t"):
            # Translation: negate the axis component
            if attr_name.endswith(axis.upper()):
                return -value
            return value
        elif attr_name.startswith("r"):
            # Rotation: negate the axis component
            if attr_name.endswith(axis.upper()):
                return -value
            return value
        elif attr_name.startswith("s"):
            # Scale: usually mirrored as is
            return value
        else:
            return value