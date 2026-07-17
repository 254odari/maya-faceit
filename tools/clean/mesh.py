# -*- coding: utf-8 -*-
"""
tools/clean/mesh.py

Mesh cleanup operations.
"""

import maya.cmds as cmds # type: ignore
from .types import MeshCleanup


class MeshCleaner:
    """
    Clean up meshes: merge vertices, delete non-manifold, lamina, unused UVs, etc.
    """

    def __init__(self, settings):
        self.settings = settings

    def cleanup(self) -> MeshCleanup:
        """Run mesh cleanup."""
        result = MeshCleanup()

        meshes = self._get_all_meshes()
        result.total_meshes = len(meshes)

        for mesh in meshes:
            if self._is_referenced(mesh):
                continue

            # 1. Merge duplicate vertices
            if self.settings.merge_duplicate_vertices:
                try:
                    cmds.polyMergeVertex(mesh, d=0.001, am=True, ch=False)
                    result.merged_vertices += 1
                except:
                    pass

            # 2. Delete non-manifold geometry
            if self.settings.delete_non_manifold:
                try:
                    # Use polyChipOff to separate non-manifold edges
                    cmds.polyChipOff(mesh, nm=True, ch=False)
                    result.fixed_non_manifold += 1
                except:
                    pass

            # 3. Delete lamina faces
            if self.settings.delete_lamina_faces:
                try:
                    cmds.polyChipOff(mesh, lm=True, ch=False)
                    result.deleted_lamina += 1
                except:
                    pass

            # 4. Delete unused UV sets
            if self.settings.delete_unused_uv_sets:
                shapes = cmds.listRelatives(mesh, shapes=True) or []
                for s in shapes:
                    uv_sets = cmds.polyUVSet(s, q=True, allUVSets=True) or []
                    current = cmds.polyUVSet(s, q=True, currentUVSet=True)[0]
                    for uv_set in uv_sets:
                        if uv_set != current:
                            try:
                                cmds.polyUVSet(s, delete=True, uvSet=uv_set)
                                result.deleted_unused_uv_sets += 1
                            except:
                                pass

            # 5. Unlock normals
            if self.settings.unlock_normals:
                try:
                    cmds.polyNormalPerVertex(mesh, unFreezeNormals=True)
                    result.unlocked_normals += 1
                except:
                    pass

            # 6. Delete history
            try:
                cmds.delete(mesh, ch=True, nonDeformerHistory=True)
                result.deleted_history += 1
            except:
                pass

            # 7. Freeze transforms (if requested)
            if self.settings.freeze_transforms:
                try:
                    cmds.makeIdentity(mesh, apply=True, t=1, r=1, s=1, n=0)
                except:
                    pass

        return result

    def _get_all_meshes(self):
        meshes = cmds.ls(type='mesh', long=True)
        result = []
        for m in meshes:
            parents = cmds.listRelatives(m, parent=True, fullPath=True)
            if parents:
                result.append(parents[0])
        return list(set(result))

    def _is_referenced(self, node):
        return cmds.referenceQuery(node, isNodeReferenced=True)