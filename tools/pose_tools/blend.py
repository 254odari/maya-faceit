# -*- coding: utf-8 -*-
"""
tools/pose_tools/blend.py

Pose blending utilities.
"""

from typing import Optional, List, Dict
from .types import Pose, PoseBlendMode, PoseAttribute
from .editor import PoseEditor
from .manager import PoseManager


class PoseBlender:
    """
    Blend poses together.
    """

    def __init__(self, editor: PoseEditor, manager: PoseManager):
        self.editor = editor
        self.manager = manager

    def blend_poses(self, pose1: str, pose2: str, result_name: str,
                    blend_factor: float = 0.5,
                    mode: PoseBlendMode = PoseBlendMode.AVERAGE,
                    category: str = "custom") -> Optional[Pose]:
        """
        Blend two poses into a new pose.

        Args:
            pose1: Name of first pose.
            pose2: Name of second pose.
            result_name: Name for the new blended pose.
            blend_factor: Blend factor (0-1) where 0 = pose1, 1 = pose2.
            mode: Blending mode.
            category: Category for the new pose.

        Returns:
            The blended Pose, or None if failed.
        """
        p1 = self.manager.get_pose(pose1)
        p2 = self.manager.get_pose(pose2)

        if not p1 or not p2:
            return None

        # Get attributes from both poses
        attrs1 = {a.name: a for a in p1.attributes}
        attrs2 = {a.name: a for a in p2.attributes}

        # Use intersection of attribute names
        common_names = set(attrs1.keys()) & set(attrs2.keys())
        if not common_names:
            return None

        blended_attrs = []
        for name in common_names:
            a1 = attrs1[name]
            a2 = attrs2[name]
            # Blend values based on mode
            if mode == PoseBlendMode.AVERAGE:
                val = a1.value * (1 - blend_factor) + a2.value * blend_factor
            elif mode == PoseBlendMode.ADD:
                val = a1.value + a2.value * blend_factor
            elif mode == PoseBlendMode.SUBTRACT:
                val = a1.value - a2.value * blend_factor
            elif mode == PoseBlendMode.MAX:
                val = max(a1.value, a2.value)
            elif mode == PoseBlendMode.MIN:
                val = min(a1.value, a2.value)
            elif mode == PoseBlendMode.CROSSFADE:
                # More complex crossfade
                val = a1.value * (1 - blend_factor) + a2.value * blend_factor
            else:
                val = a1.value * (1 - blend_factor) + a2.value * blend_factor

            blended_attrs.append(PoseAttribute(name=name, value=val, type=a1.type))

        # Create the new pose
        attr_dicts = [{"name": a.name, "value": a.value, "type": a.type} for a in blended_attrs]
        return self.manager.create_pose(
            name=result_name,
            attributes=attr_dicts,
            category=category,
            description=f"Blend of {pose1} and {pose2}",
            tags=["blended"]
        )