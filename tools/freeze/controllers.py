# -*- coding: utf-8 -*-
"""
tools/freeze/controllers.py

Controller freezing operations.
"""

import maya.cmds as cmds # type: ignore
from typing import List
from .types import ControllerFreeze


class ControllerFreezer:
    """
    Freeze controllers (NURBS controls).
    """

    def __init__(self, settings):
        self.settings = settings
        self._offset_groups: List[str] = []

    def freeze(self, controllers: List[str]) -> ControllerFreeze:
        """Freeze controllers."""
        result = ControllerFreeze()
        result.total_controllers = len(controllers)

        for ctrl in controllers:
            if not cmds.objExists(ctrl):
                result.skipped_controllers += 1
                continue

            if self._is_referenced(ctrl):
                result.skipped_controllers += 1
                continue

            # Check if it's a controller (has NURBS shapes)
            if not self._is_controller(ctrl):
                result.skipped_controllers += 1
                continue

            # Check dependencies
            has_anim = self._has_animation(ctrl)

            # Determine channels
            channels = []
            if self.settings.freeze_translate:
                channels.extend(['tx', 'ty', 'tz'])
            if self.settings.freeze_rotate:
                channels.extend(['rx', 'ry', 'rz'])
            if self.settings.freeze_scale:
                channels.extend(['sx', 'sy', 'sz'])

            if not channels:
                result.skipped_controllers += 1
                continue

            # Safe mode: create offset group if animated
            if self.settings.mode.value == "safe" and has_anim:
                offset = self._create_offset_group(ctrl)
                if offset:
                    result.offset_groups += 1
                    self._freeze_node(offset, channels)
                    result.frozen_controllers += 1
                    continue

            # Freeze directly
            if self._freeze_node(ctrl, channels):
                result.frozen_controllers += 1
            else:
                result.skipped_controllers += 1

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
        """Create an offset group for the controller."""
        parent = cmds.listRelatives(node, parent=True, fullPath=True)
        offset = cmds.createNode('transform', name=f"{node}_offset")

        cmds.xform(offset, ws=True, matrix=cmds.xform(node, q=True, ws=True, matrix=True))

        if parent:
            cmds.parent(offset, parent[0])
        else:
            cmds.parent(offset, world=True)

        cmds.parent(node, offset)
        self._offset_groups.append(offset)
        return offset

    def _is_controller(self, node: str) -> bool:
        """Check if node is a controller."""
        shapes = cmds.listRelatives(node, shapes=True) or []
        return any(cmds.nodeType(s) in ['nurbsCurve', 'nurbsSurface'] for s in shapes)

    def _has_animation(self, node: str) -> bool:
        """Check if node has animation keys."""
        attrs = cmds.listAttr(node, keyable=True) or []
        for attr in attrs:
            if cmds.keyframe(f"{node}.{attr}", q=True, keyframeCount=True):
                return True
        return False

    def _is_referenced(self, node: str) -> bool:
        return cmds.referenceQuery(node, isNodeReferenced=True)