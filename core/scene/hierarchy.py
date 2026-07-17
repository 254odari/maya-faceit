"""
core/scene/hierarchy.py

Hierarchy utilities for Maya Faceit.
"""

import maya.cmds as cmds # type: ignore

class HierarchyUtils:
    @staticmethod
    def get_all_children(node: str, recursive: bool = True):
        if not recursive:
            return cmds.listRelatives(node, children=True, fullPath=True) or []
        return cmds.listRelatives(node, allDescendents=True, fullPath=True) or []

    @staticmethod
    def get_parents(node: str):
        return cmds.listRelatives(node, parent=True, fullPath=True) or []