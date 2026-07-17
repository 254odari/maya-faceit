# -*- coding: utf-8 -*-
"""
tools/optimizer/animation.py

Animation optimizations.
"""

import maya.cmds as cmds # type: ignore
from .types import AnimationOptimization


class AnimationOptimizer:
    """
    Optimize animation curves and playback.
    """

    def __init__(self, settings):
        self.settings = settings

    def optimize(self) -> AnimationOptimization:
        """Run animation optimizations."""
        result = AnimationOptimization()

        # Find all animated attributes
        all_transforms = cmds.ls(type='transform', long=True)
        animated_attrs = []
        for obj in all_transforms:
            attrs = cmds.listAttr(obj, keyable=True) or []
            for attr in attrs:
                full = f"{obj}.{attr}"
                if cmds.keyframe(full, q=True, keyframeCount=True):
                    animated_attrs.append(full)

        result.total_curves = len(animated_attrs)

        # Simplify curves
        if self.settings.simplify_curves:
            for attr in animated_attrs:
                try:
                    cmds.filterCurve(attr, tolerance=self.settings.curve_tolerance)
                    result.simplified_curves += 1
                except:
                    pass

        # Enable cached playback
        try:
            cmds.playbackOptions(useCache=True)
            result.cached_playback_enabled = True
        except:
            pass

        return result