# -*- coding: utf-8 -*-
"""
tools/clean/scene.py

Scene-level cleanup operations.
"""

import maya.cmds as cmds # type: ignore
from .types import SceneCleanup


class SceneCleaner:
    """
    Clean up scene-level elements: unknown nodes, empty groups, orphans, history.
    """

    def __init__(self, settings):
        self.settings = settings

    def cleanup(self) -> SceneCleanup:
        """Run scene-level cleanup."""
        result = SceneCleanup()

        # Auto backup
        if self.settings.auto_backup:
            self._auto_backup()

        # 1. Remove unknown nodes
        if self.settings.remove_unknown_nodes:
            unknown = cmds.ls(type='unknown')
            if unknown:
                deleted = self._safe_delete(unknown)
                result.removed_unknown = deleted
                result.deleted_nodes += deleted

        # 2. Remove orphan nodes (nodes with no connections)
        if self.settings.remove_orphan_nodes:
            # Simplified: find nodes with no connections (except transform parent)
            # This is complex; we'll skip for now
            pass

        # 3. Remove empty groups
        if self.settings.remove_empty_groups:
            groups = cmds.ls(type='group')
            empty = []
            for g in groups:
                if self._is_referenced(g):
                    continue
                children = cmds.listRelatives(g, children=True) or []
                if not children:
                    empty.append(g)
            if empty:
                deleted = self._safe_delete(empty)
                result.removed_empty_groups = deleted
                result.deleted_nodes += deleted

        # 4. Remove empty transforms
        if self.settings.remove_empty_transforms:
            transforms = cmds.ls(type='transform')
            empty = []
            for t in transforms:
                if self._is_referenced(t):
                    continue
                # Skip if it has shapes
                shapes = cmds.listRelatives(t, shapes=True) or []
                if shapes:
                    continue
                children = cmds.listRelatives(t, children=True) or []
                if not children:
                    empty.append(t)
            if empty:
                deleted = self._safe_delete(empty)
                result.removed_empty_transforms = deleted
                result.deleted_nodes += deleted

        # 5. Remove empty display layers
        if self.settings.remove_empty_display_layers:
            layers = cmds.ls(type='displayLayer')
            empty = []
            for l in layers:
                if self._is_referenced(l):
                    continue
                members = cmds.editDisplayLayerMembers(l, q=True) or []
                if not members:
                    empty.append(l)
            if empty:
                deleted = self._safe_delete(empty)
                result.removed_empty_display_layers = deleted
                result.deleted_nodes += deleted

        # 6. Remove empty render layers
        if self.settings.remove_empty_render_layers:
            layers = cmds.ls(type='renderLayer')
            empty = []
            for l in layers:
                if l in ['defaultRenderLayer']:
                    continue
                # Hard to detect empty render layers; skip for now
                pass

        # 7. Delete history
        if self.settings.delete_history:
            meshes = self._get_all_meshes()
            for mesh in meshes:
                if self._is_referenced(mesh):
                    continue
                try:
                    if self.settings.history_mode.value == "all":
                        cmds.delete(mesh, ch=True)
                    elif self.settings.history_mode.value == "non_deformer":
                        cmds.delete(mesh, ch=True, nonDeformerHistory=True)
                    else:
                        # PRESERVE_DEFORMERS: skip
                        pass
                    result.deleted_history += 1
                except:
                    pass

        return result

    def _safe_delete(self, nodes):
        """Delete nodes, skipping locked or referenced."""
        deleted = 0
        for n in nodes:
            if not cmds.objExists(n):
                continue
            if self._is_referenced(n):
                continue
            if cmds.lockNode(n, q=True, lock=True)[0]:
                continue
            try:
                cmds.delete(n)
                deleted += 1
            except:
                pass
        return deleted

    def _is_referenced(self, node):
        return cmds.referenceQuery(node, isNodeReferenced=True)

    def _get_all_meshes(self):
        """Get all mesh transforms."""
        meshes = cmds.ls(type='mesh', long=True)
        result = []
        for m in meshes:
            parents = cmds.listRelatives(m, parent=True, fullPath=True)
            if parents:
                result.append(parents[0])
        return list(set(result))

    def _auto_backup(self):
        """Create an auto backup before destructive operations."""
        # Placeholder: could save a backup file
        pass