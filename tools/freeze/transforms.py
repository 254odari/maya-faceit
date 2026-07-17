# -*- coding: utf-8 -*-
"""
tools/freeze/transforms.py

Transform freezing operations.
"""

import maya.cmds as cmds # type: ignore
from typing import List, Dict, Any
from .types import TransformFreeze


class TransformFreezer:
    """
    Freeze transforms on generic nodes.
    """

    def __init__(self, settings):
        self.settings = settings
        self._offset_groups: Dict[str, str] = {}

    def freeze(self, nodes: List[str]) -> TransformFreeze:
        """Freeze transforms on nodes."""
        result = TransformFreeze()
        result.total_nodes = len(nodes)

        for node in nodes:
            if not cmds.objExists(node):
                result.skipped_nodes += 1
                continue

            # Check for dependencies
            has_anim = self._has_animation(node)
            has_const = self._has_constraints(node)
            has_skin = self._has_skinning(node)
            has_bs = self._has_blendshapes(node)
            has_critical = has_anim or has_const or has_skin or has_bs

            # Determine channels to freeze
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

            # Safe mode: create offset group if critical dependencies exist
            if self.settings.mode.value == "safe" and has_critical:
                offset = self._create_offset_group(node)
                if offset:
                    result.offset_groups += 1
                    # Freeze the offset group (it has no dependencies)
                    self._freeze_node(offset, channels)
                    result.frozen_nodes += 1
                    continue
                else:
                    result.skipped_nodes += 1
                    continue

            # Standard or Force: freeze directly
            if self._freeze_node(node, channels):
                result.frozen_nodes += 1
                result.preserved_connections += 1
                # Track channels frozen
                if 'tx' in channels or 'ty' in channels or 'tz' in channels:
                    result.frozen_translates += 1
                if 'rx' in channels or 'ry' in channels or 'rz' in channels:
                    result.frozen_rotates += 1
                if 'sx' in channels or 'sy' in channels or 'sz' in channels:
                    result.frozen_scales += 1
            else:
                result.skipped_nodes += 1

        return result

    def _freeze_node(self, node: str, channels: List[str]) -> bool:
        """Freeze a single node."""
        if not cmds.objExists(node):
            return False
        if self._is_referenced(node):
            return False
        if cmds.lockNode(node, q=True, lock=True)[0]:
            return False

        # Unlock attributes if needed
        locked = []
        for attr in channels:
            full = f"{node}.{attr}"
            if cmds.objExists(full) and cmds.getAttr(full, lock=True):
                locked.append(attr)
                cmds.setAttr(full, lock=False)

        # Freeze
        try:
            cmds.makeIdentity(node, apply=True,
                             t='t' in str(channels),
                             r='r' in str(channels),
                             s='s' in str(channels),
                             n=0)
        except:
            return False

        # Relock
        for attr in locked:
            full = f"{node}.{attr}"
            if cmds.objExists(full):
                cmds.setAttr(full, lock=True)

        return True

    def _create_offset_group(self, node: str) -> str:
        """Create an offset group above the node."""
        if node in self._offset_groups:
            return self._offset_groups[node]

        parent = cmds.listRelatives(node, parent=True, fullPath=True)
        offset = cmds.createNode('transform', name=f"{node}_offset")

        # Match world transform
        cmds.xform(offset, ws=True, matrix=cmds.xform(node, q=True, ws=True, matrix=True))

        # Parent under original parent
        if parent:
            cmds.parent(offset, parent[0])
        else:
            cmds.parent(offset, world=True)

        # Parent node under offset
        cmds.parent(node, offset)

        self._offset_groups[node] = offset
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

    def _has_blendshapes(self, node: str) -> bool:
        """Check if node has blendshapes."""
        return bool(cmds.listConnections(node, type='blendShape'))

    def _is_referenced(self, node: str) -> bool:
        return cmds.referenceQuery(node, isNodeReferenced=True)