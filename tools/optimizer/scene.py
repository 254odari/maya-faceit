# -*- coding: utf-8 -*-
"""
tools/optimizer/scene.py

Scene-level optimizations.
"""

import maya.cmds as cmds # type: ignore
from .types import SceneOptimization


class SceneOptimizer:
    """
    Optimize overall scene performance.
    """

    def __init__(self, settings):
        self.settings = settings

    def optimize(self) -> SceneOptimization:
        """Run scene-level optimizations."""
        result = SceneOptimization()

        # Remove unknown nodes
        unknown = cmds.ls(type='unknown')
        if unknown:
            try:
                cmds.delete(unknown)
                result.removed_unknown = len(unknown)
            except:
                pass

        # Remove empty groups
        groups = cmds.ls(type='group')
        empty = []
        for g in groups:
            children = cmds.listRelatives(g, children=True) or []
            if not children:
                empty.append(g)
        if empty:
            try:
                cmds.delete(empty)
                result.removed_empty_groups = len(empty)
            except:
                pass

        # Remove empty transforms
        if self.settings.level.value != "safe":
            transforms = cmds.ls(type='transform')
            empty = []
            for t in transforms:
                if cmds.referenceQuery(t, isNodeReferenced=True):
                    continue
                shapes = cmds.listRelatives(t, shapes=True) or []
                children = cmds.listRelatives(t, children=True) or []
                if not shapes and not children:
                    empty.append(t)
            if empty:
                try:
                    cmds.delete(empty)
                    result.removed_empty_transforms = len(empty)
                except:
                    pass

        result.optimized_nodes = (
            result.removed_unknown +
            result.removed_empty_groups +
            result.removed_empty_transforms
        )

        return result