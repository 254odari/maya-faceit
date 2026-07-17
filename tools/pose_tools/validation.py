# -*- coding: utf-8 -*-
"""
tools/pose_tools/validation.py

Validation for poses.
"""

import maya.cmds as cmds # type: ignore
from typing import Dict, Any, List
from .types import Pose
from .editor import PoseEditor
from .manager import PoseManager


class PoseValidator:
    """
    Validate poses for integrity.
    """

    def __init__(self, editor: PoseEditor, manager: PoseManager):
        self.editor = editor
        self.manager = manager

    def validate(self, name: str) -> Dict[str, Any]:
        """
        Validate a pose.

        Checks:
            - Pose exists
            - All attributes exist in the scene
            - Values are within expected ranges
        """
        result = {
            'name': name,
            'valid': True,
            'warnings': [],
            'errors': [],
            'details': {}
        }

        pose = self.manager.get_pose(name)
        if not pose:
            result['valid'] = False
            result['errors'].append(f"Pose '{name}' does not exist.")
            return result

        # Check each attribute
        missing = []
        for attr in pose.attributes:
            if not cmds.objExists(attr.name):
                missing.append(attr.name)
            else:
                # Check value range (for 0-1 attributes)
                if attr.type == "float" and attr.value < 0 or attr.value > 1:
                    # Only warn if it's a blendshape or clampable attribute
                    if "blendShape" in attr.name or attr.name.endswith(".weight"):
                        result['warnings'].append(f"Attribute '{attr.name}' value {attr.value} outside 0-1 range.")

        if missing:
            result['errors'].append(f"Missing attributes: {', '.join(missing[:10])}")
            result['valid'] = False

        result['details'] = {
            'attribute_count': len(pose.attributes),
            'pose_type': pose.pose_type.value,
            'category': pose.category.value,
        }

        return result