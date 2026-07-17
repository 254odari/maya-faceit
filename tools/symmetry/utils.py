# -*- coding: utf-8 -*-
"""
tools/symmetry/utils.py

Utility functions for symmetry.
"""

import maya.cmds as cmds # type: ignore
from typing import List, Optional


class SymmetryUtils:
    """
    Helper functions for symmetry.
    """

    @staticmethod
    def get_controllers_in_scene() -> List[str]:
        all_transforms = cmds.ls(type='transform', long=True)
        controllers = []
        for t in all_transforms:
            shapes = cmds.listRelatives(t, shapes=True, fullPath=True) or []
            if shapes:
                for s in shapes:
                    if cmds.nodeType(s) in ['nurbsCurve', 'nurbsSurface', 'circle', 'square', 'triangle']:
                        controllers.append(t)
                        break
        return controllers

    @staticmethod
    def get_joints_in_scene() -> List[str]:
        return cmds.ls(type='joint', long=True) or []

    @staticmethod
    def get_blendshape_nodes() -> List[str]:
        return cmds.ls(type='blendShape', long=True) or []

    @staticmethod
    def get_meshes_in_scene() -> List[str]:
        return cmds.ls(type='mesh', long=True) or []

    @staticmethod
    def get_side_from_name(name: str) -> Optional[str]:
        if name.startswith("L_") or name.startswith("Left") or name.startswith("left"):
            return "L"
        if name.startswith("R_") or name.startswith("Right") or name.startswith("right"):
            return "R"
        if "_l" in name or ".L" in name:
            return "L"
        if "_r" in name or ".R" in name:
            return "R"
        return None