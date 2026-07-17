# -*- coding: utf-8 -*-
"""
tools/freeze/mesh.py

Mesh freezing operations.
"""

import maya.cmds as cmds # type: ignore
from typing import List
from .types import MeshFreeze


class MeshFreezer:
    """
    Freeze mesh transforms.
    """

    def __init__(self, settings):
        self.settings = settings

    def freeze(self, meshes: List[str]) -> MeshFreeze:
        """Freeze mesh transforms."""
        result = MeshFreeze()
        result.total_meshes = len(meshes)

        for mesh in meshes:
            if not cmds.objExists(mesh):
                result.skipped_meshes += 1
                continue

            if self._is_referenced(mesh):
                result.skipped_meshes += 1
                continue

            if not self._is_mesh(mesh):
                result.skipped_meshes += 1
                continue

            # Determine channels
            channels = []
            if self.settings.freeze_translate:
                channels.extend(['tx', 'ty', 'tz'])
            if self.settings.freeze_rotate:
                channels.extend(['rx', 'ry', 'rz'])
            if self.settings.freeze_scale:
                channels.extend(['sx', 'sy', 'sz'])

            if not channels:
                result.skipped_meshes += 1
                continue

            # Check if mesh has deformers
            has_deformers = self._has_deformers(mesh)

            # If mesh has deformers and in safe mode, create offset group
            if self.settings.mode.value == "safe" and has_deformers:
                offset = self._create_offset_group(mesh)
                if offset:
                    self._freeze_node(offset, channels)
                    result.frozen_meshes += 1
                    continue
                else:
                    result.skipped_meshes += 1
                    continue

            if self._freeze_node(mesh, channels):
                result.frozen_meshes += 1
            else:
                result.skipped_meshes += 1

        return result

    def _freeze_node(self, node: str, channels: List[str]) -> bool:
        """Freeze a single node."""
        if not cmds.objExists(node):
            return False

        locked = []
        for attr in channels:
            full = f"{node}.{attr}"
            if cmds.objExists(full) and cmds.getAttr(full, lock=True):
                locked.append(attr)
                cmds.setAttr(full, lock=False)

        try:
            cmds.makeIdentity(node, apply=True,
                             t='t' in str(channels),
                             r='r' in str(channels),
                             s='s' in str(channels),
                             n=0)
        except:
            return False

        for attr in locked:
            full = f"{node}.{attr}"
            if cmds.objExists(full):
                cmds.setAttr(full, lock=True)

        return True

    def _create_offset_group(self, node: str) -> str:
        """Create an offset group for the node."""
        parent = cmds.listRelatives(node, parent=True, fullPath=True)
        offset = cmds.createNode('transform', name=f"{node}_offset")

        cmds.xform(offset, ws=True, matrix=cmds.xform(node, q=True, ws=True, matrix=True))

        if parent:
            cmds.parent(offset, parent[0])
        else:
            cmds.parent(offset, world=True)

        cmds.parent(node, offset)
        return offset

    def _is_mesh(self, node: str) -> bool:
        """Check if node is a mesh."""
        shapes = cmds.listRelatives(node, shapes=True) or []
        return any(cmds.nodeType(s) == 'mesh' for s in shapes)

    def _has_deformers(self, node: str) -> bool:
        """Check if node has deformers."""
        history = cmds.listHistory(node) or []
        deformers = ['cluster', 'softMod', 'wire', 'blendShape', 'skinCluster']
        for h in history:
            if cmds.nodeType(h) in deformers:
                return True
        return False

    def _is_referenced(self, node: str) -> bool:
        return cmds.referenceQuery(node, isNodeReferenced=True)