# -*- coding: utf-8 -*-
"""
tools/analysis/animation.py

Animation analysis.
"""

import maya.cmds as cmds # type: ignore
from typing import Optional, Set, List
from .types import AnimationStats, AnalysisScope, AnalysisLevel


class AnimationAnalyzer:
    """
    Analyze animation data.
    """

    def __init__(self, settings):
        self.settings = settings

    def analyze(self, scope: AnalysisScope = AnalysisScope.SCENE,
                level: AnalysisLevel = AnalysisLevel.STANDARD) -> AnimationStats:
        """Analyze animation statistics."""
        stats = AnimationStats()

        # Get time range
        stats.time_range_start = cmds.playbackOptions(q=True, min=True)
        stats.time_range_end = cmds.playbackOptions(q=True, max=True)
        stats.fps = cmds.currentUnit(q=True, time=True)
        try:
            stats.fps = float(stats.fps)
        except:
            stats.fps = 24.0

        # Animated objects
        all_transforms = cmds.ls(type='transform', long=True)
        animated_objects = []
        animated_attrs = []
        total_keyframes = 0
        total_curves = 0
        empty_curves = 0
        static_channels = 0

        for obj in all_transforms:
            attrs = cmds.listAttr(obj, keyable=True) or []
            has_anim = False
            for a in attrs:
                full = f"{obj}.{a}"
                count = cmds.keyframe(full, q=True, keyframeCount=True)
                if count is not None and count > 0:
                    total_keyframes += count
                    animated_attrs.append(full)
                    has_anim = True
                    total_curves += 1
                elif count == 0:
                    empty_curves += 1
            if has_anim:
                animated_objects.append(obj)

        stats.total_animated_objects = len(animated_objects)
        stats.total_animated_attributes = len(animated_attrs)
        stats.total_keyframes = total_keyframes
        stats.total_animation_curves = total_curves
        stats.empty_curves = empty_curves
        stats.static_channels = len(all_transforms) * 9 - total_curves  # Rough estimate

        # Animation layers
        stats.total_animation_layers = len(cmds.ls(type='animLayer', long=True))

        if level == AnalysisLevel.DEEP:
            stats.details['animated_objects'] = animated_objects[:10]
            stats.details['animated_attributes'] = animated_attrs[:10]

        return stats