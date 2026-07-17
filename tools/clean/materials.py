# -*- coding: utf-8 -*-
"""
tools/clean/materials.py

Material and texture cleanup.
"""

import maya.cmds as cmds # type: ignore
from .types import MaterialCleanup


class MaterialCleaner:
    """
    Clean up unused materials, textures, shading groups, file nodes.
    """

    def __init__(self, settings):
        self.settings = settings

    def cleanup(self) -> MaterialCleanup:
        """Run material cleanup."""
        result = MaterialCleanup()

        # 1. Remove unused materials
        if self.settings.remove_unused_materials:
            all_materials = cmds.ls(type='material')
            used = set()
            for mat in all_materials:
                if self._is_referenced(mat):
                    continue
                # Check if material is connected to any shadingEngine
                sg = cmds.listConnections(mat, type='shadingEngine') or []
                if sg:
                    # Check if shadingEngine has objects
                    objects = cmds.sets(sg[0], q=True) or []
                    if objects:
                        used.add(mat)
            to_delete = [m for m in all_materials if m not in used]
            deleted = 0
            for mat in to_delete:
                try:
                    cmds.delete(mat)
                    deleted += 1
                except:
                    pass
            result.removed_materials = deleted

        # 2. Remove unused shading groups
        if self.settings.remove_unused_shading_groups:
            all_sg = cmds.ls(type='shadingEngine')
            for sg in all_sg:
                if sg in ['initialShadingGroup', 'initialParticleSE']:
                    continue
                if self._is_referenced(sg):
                    continue
                if not cmds.sets(sg, q=True) and not cmds.listConnections(sg, type='material'):
                    try:
                        cmds.delete(sg)
                        result.removed_shading_groups += 1
                    except:
                        pass

        # 3. Remove unused textures (file nodes)
        if self.settings.remove_unused_textures:
            files = cmds.ls(type='file')
            used = set()
            for f in files:
                if self._is_referenced(f):
                    continue
                # Check if connected to any material
                conn = cmds.listConnections(f, type='material') or []
                if conn:
                    used.add(f)
            to_delete = [f for f in files if f not in used]
            deleted = 0
            for f in to_delete:
                try:
                    cmds.delete(f)
                    deleted += 1
                except:
                    pass
            result.removed_textures = deleted
            result.removed_file_nodes = deleted

        return result

    def _is_referenced(self, node):
        return cmds.referenceQuery(node, isNodeReferenced=True)