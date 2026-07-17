# -*- coding: utf-8 -*-
"""
tools/optimizer/deformer.py

Deformer stack optimizations.
"""

import maya.cmds as cmds # type: ignore
from .types import DeformerOptimization


class DeformerOptimizer:
    """
    Optimize deformer stacks and history.
    """

    def __init__(self, settings):
        self.settings = settings

    def optimize(self) -> DeformerOptimization:
        """Run deformer optimizations."""
        result = DeformerOptimization()

        # Find all meshes with deformers
        all_meshes = cmds.ls(type='mesh', long=True)
        mesh_transforms = []
        for m in all_meshes:
            parents = cmds.listRelatives(m, parent=True, fullPath=True)
            if parents:
                mesh_transforms.append(parents[0])
        mesh_transforms = list(set(mesh_transforms))

        result.total_deformers = len(mesh_transforms)

        for mesh in mesh_transforms:
            if cmds.referenceQuery(mesh, isNodeReferenced=True):
                continue

            # Delete non-deformer history
            try:
                cmds.delete(mesh, ch=True, nonDeformerHistory=True)
                result.deleted_history += 1
            except:
                pass

            result.optimized_deformers += 1

        return result