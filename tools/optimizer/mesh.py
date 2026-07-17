# -*- coding: utf-8 -*-
"""
tools/optimizer/mesh.py

Mesh optimizations.
"""

import maya.cmds as cmds # type: ignore
from .types import MeshOptimization


class MeshOptimizer:
    """
    Optimize polygon meshes.
    """

    def __init__(self, settings):
        self.settings = settings

    def optimize(self) -> MeshOptimization:
        """Run mesh optimizations."""
        result = MeshOptimization()

        # Get all meshes
        all_meshes = cmds.ls(type='mesh', long=True)
        mesh_transforms = []
        for m in all_meshes:
            parents = cmds.listRelatives(m, parent=True, fullPath=True)
            if parents:
                mesh_transforms.append(parents[0])
        mesh_transforms = list(set(mesh_transforms))
        result.total_meshes = len(mesh_transforms)

        for mesh in mesh_transforms:
            if cmds.referenceQuery(mesh, isNodeReferenced=True):
                continue

            # Merge duplicate vertices
            try:
                cmds.polyMergeVertex(mesh, d=self.settings.merge_vertex_tolerance, am=True, ch=False)
                result.merged_vertices += 1
            except:
                pass

            # Delete non-deformer history
            try:
                cmds.delete(mesh, ch=True, nonDeformerHistory=True)
                result.deleted_history += 1
            except:
                pass

            # Optimize display for heavy meshes (aggressive only)
            if self.settings.level.value == "aggressive":
                vtx_count = cmds.polyEvaluate(mesh, vertex=True)
                if vtx_count > self.settings.max_vertices_for_display_opt:
                    try:
                        cmds.setAttr(f"{mesh}.displayType", 0)  # Bounding box
                        result.optimized_display += 1
                    except:
                        pass

            # Optimize UVs (remove unused)
            shapes = cmds.listRelatives(mesh, shapes=True) or []
            for s in shapes:
                uv_sets = cmds.polyUVSet(s, q=True, allUVSets=True) or []
                current = cmds.polyUVSet(s, q=True, currentUVSet=True)[0]
                for uv_set in uv_sets:
                    if uv_set != current and cmds.polyEvaluate(s, uvCoord=True) > 0:
                        try:
                            cmds.polyUVSet(s, delete=True, uvSet=uv_set)
                            result.optimized_uvs += 1
                        except:
                            pass

        return result