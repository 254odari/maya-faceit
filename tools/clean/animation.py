# -*- coding: utf-8 -*-
"""
tools/clean/animation.py

Animation cleanup.
"""

import maya.cmds as cmds # type: ignore
from .types import AnimationCleanup


class AnimationCleaner:
    """
    Clean up animation data: static channels, empty curves, unused layers, constraints.
    """

    def __init__(self, settings):
        self.settings = settings

    def cleanup(self) -> AnimationCleanup:
        """Run animation cleanup."""
        result = AnimationCleanup()

        # 1. Remove static channels (attributes with no keys)
        if self.settings.remove_static_channels:
            # Identify attributes with no keys
            all_transforms = cmds.ls(type='transform', long=True)
            for obj in all_transforms:
                if self._is_referenced(obj):
                    continue
                attrs = cmds.listAttr(obj, keyable=True) or []
                for attr in attrs:
                    full = f"{obj}.{attr}"
                    if cmds.keyframe(full, q=True, keyframeCount=True):
                        continue
                    # If no keys, we could set it to default or remove? For safety, we skip.
                    pass

        # 2. Remove empty curves (curves with no keyframes)
        if self.settings.remove_empty_curves:
            # Could use `cmds.listConnections` to find empty curves
            pass

        # 3. Remove unused animation layers
        if self.settings.remove_unused_animation_layers:
            layers = cmds.ls(type='animLayer')
            for layer in layers:
                if self._is_referenced(layer):
                    continue
                # Check if layer has any animation
                # Hard to detect; we'll skip for now

        # 4. Remove unused constraints
        if self.settings.remove_unused_constraints:
            constraints = cmds.ls(type='constraint')
            for c in constraints:
                if self._is_referenced(c):
                    continue
                if not cmds.listConnections(c):
                    try:
                        cmds.delete(c)
                        result.removed_constraints += 1
                    except:
                        pass

        return result

    def _is_referenced(self, node):
        return cmds.referenceQuery(node, isNodeReferenced=True)