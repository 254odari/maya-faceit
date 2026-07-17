# -*- coding: utf-8 -*-
"""
tools/freeze/validation.py

Validation utilities for freeze operations.
"""

import maya.cmds as cmds # type: ignore
from typing import Dict, Any, List


class FreezeValidator:
    """
    Validate nodes before freezing.
    """

    def validate(self, node: str) -> Dict[str, Any]:
        """
        Validate a node for freezing.

        Checks:
            - Node exists
            - Node is not referenced
            - Node is not locked
            - Node has no critical dependencies (if in safe mode)

        Returns:
            Dict with validation results.
        """
        result = {
            'node': node,
            'valid': True,
            'warnings': [],
            'errors': [],
            'has_animation': False,
            'has_constraints': False,
            'has_skinning': False,
            'has_blendshapes': False,
            'is_referenced': False,
            'is_locked': False,
        }

        if not cmds.objExists(node):
            result['valid'] = False
            result['errors'].append(f"Node '{node}' does not exist.")
            return result

        # Check references
        if cmds.referenceQuery(node, isNodeReferenced=True):
            result['is_referenced'] = True
            result['warnings'].append(f"Node '{node}' is referenced.")

        # Check locked
        if cmds.lockNode(node, q=True, lock=True)[0]:
            result['is_locked'] = True
            result['warnings'].append(f"Node '{node}' is locked.")

        # Check dependencies
        if self._has_animation(node):
            result['has_animation'] = True
            result['warnings'].append(f"Node '{node}' has animation keys.")

        if self._has_constraints(node):
            result['has_constraints'] = True
            result['warnings'].append(f"Node '{node}' has constraints.")

        if self._has_skinning(node):
            result['has_skinning'] = True
            result['warnings'].append(f"Node '{node}' has skinning.")

        if self._has_blendshapes(node):
            result['has_blendshapes'] = True
            result['warnings'].append(f"Node '{node}' has blendshapes.")

        return result

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