# -*- coding: utf-8 -*-
"""
tools/skin/influences.py

Influence management: add, remove, reorder, query.
"""

import maya.cmds as cmds # type: ignore
from typing import List, Optional
from .types import InfluenceInfo
from .editor import SkinEditor


class InfluenceTools:
    """
    Influence management tools.
    """

    def __init__(self, editor: SkinEditor):
        self.editor = editor

    def get_influences(self, skin: str) -> List[InfluenceInfo]:
        """Get all influences with their info."""
        info = self.editor.get_skin_info(skin)
        if info:
            return info.influences
        return []

    def add_influence(self, skin: str, influence: str) -> bool:
        """Add an influence to a skinCluster."""
        if not cmds.objExists(skin) or not cmds.objExists(influence):
            return False
        try:
            cmds.skinCluster(skin, e=True, influence=influence)
            return True
        except:
            return False

    def remove_influence(self, skin: str, influence: str) -> bool:
        """Remove an influence from a skinCluster."""
        if not cmds.objExists(skin) or not cmds.objExists(influence):
            return False
        try:
            cmds.skinCluster(skin, e=True, removeInfluence=influence)
            return True
        except:
            return False

    def reorder_influences(self, skin: str, order: List[str]) -> bool:
        """Reorder influences."""
        if not cmds.objExists(skin):
            return False
        current = cmds.skinCluster(skin, q=True, influence=True) or []
        if set(current) != set(order):
            return False
        try:
            cmds.skinCluster(skin, e=True, influenceOrder=order)
            return True
        except:
            return False

    def get_influence_index(self, skin: str, influence: str) -> int:
        """Get the index of an influence."""
        influences = self.get_influences(skin)
        for i, inf in enumerate(influences):
            if inf.name == influence:
                return i
        return -1