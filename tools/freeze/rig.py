# -*- coding: utf-8 -*-
"""
tools/freeze/rig.py

Rig freezing operations.
"""

import maya.cmds as cmds # type: ignore
from typing import List, Set
from .types import RigFreeze


class RigFreezer:
    """
    Freeze an entire rig hierarchy.
    """

    def __init__(self, settings):
        self.settings = settings
        self._offset_groups: Set[str] = set()

    def freeze(self, rig_root: str) -> RigFreeze:
        """Freeze an entire rig hierarchy."""
        result = RigFreeze()

        if not cmds.objExists(rig_root):
            return result

        # Get all descendants that are transforms
        descendants = cmds.listRelatives(rig_root, allDescendents=True, fullPath=True) or []
        nodes = [rig_root] + descendants
        transforms = [n for n in nodes if cmds.nodeType(n) == 'transform']

        result.total_nodes = len(transforms)

        for node in transforms:
            if self._is_referenced(node):
                result.skipped_nodes += 1
                continue

            if cmds.lockNode(node, q=True, lock=True)[0]:
                result.skipped_nodes += 1
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
                result.skipped_nodes += 1
                continue

            # Check if node has critical dependencies
            has_anim = self._has_animation(node)
            has_const = self._has_constraints(node)
            has_skin = self._has_skinning(node)

            if self.settings.mode.value == "safe" and (has_anim or has_const or has_skin):
                offset = self._create_offset_group(node)
                if offset:
                    result.offset_groups += 1
                    self._freeze_node(offset, channels)
                    result.frozen_transforms += 1
                    continue
                else:
                    result.skipped_nodes += 1
                    continue

            if self._freeze_node(node, channels):
                result.frozen_transforms += 1
                # Also freeze pivots
                if self._freeze_pivot(node):
                    result.frozen_pivots += 1
            else:
                result.skipped_nodes += 1

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

    def _freeze_pivot(self, node: str) -> bool:
        """Freeze pivot on a single node."""
        try:
            cmds.xform(node, piv=(0, 0, 0), ws=False)
            cmds.xform(node, sp=(0, 0, 0), ws=False)
            return True
        except:
            return False

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
        self._offset_groups.add(offset)
        return offset

    def _has_animation(self, node: str) -> bool:
        """Check if node has animation keys."""
        attrs = cmds.listAttr(node, keyable=True) or []
        for attr in attrs:
            if cmds.keyframe(f"{node}.{attr}", q=True, keyframeCount=True):
                return True
        return False

    def _has_constraints(self, node: str) -> bool:
        """Check if node has constraints."""
        return bool(cmds.listConnections(node, type='constraint'))

    def _has_skinning(self, node: str) -> bool:
        """Check if node is skinned."""
        return bool(cmds.listConnections(node, type='skinCluster'))

    def _is_referenced(self, node: str) -> bool:
        return cmds.referenceQuery(node, isNodeReferenced=True)