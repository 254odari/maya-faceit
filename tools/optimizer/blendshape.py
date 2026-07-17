# -*- coding: utf-8 -*-
"""
tools/optimizer/blendshape.py

Blendshape optimizations.
"""

import maya.cmds as cmds # type: ignore
from .types import BlendshapeOptimization


class BlendshapeOptimizer:
    """
    Optimize blendshape nodes.
    """

    def __init__(self, settings):
        self.settings = settings

    def optimize(self) -> BlendshapeOptimization:
        """Run blendshape optimizations."""
        result = BlendshapeOptimization()

        bs_nodes = cmds.ls(type='blendShape', long=True)
        result.total_blendshapes = len(bs_nodes)

        for bs in bs_nodes:
            if cmds.referenceQuery(bs, isNodeReferenced=True):
                continue

            # Remove zero-weight targets (aggressive only)
            if self.settings.level.value == "aggressive" and self.settings.remove_zero_weights:
                targets = cmds.listAttr(bs, m=True, string='weight') or []
                for t in targets:
                    attr = f"{bs}.{t}"
                    if cmds.getAttr(attr) == 0.0:
                        try:
                            # Check if target geometry exists and is used
                            # We'll just remove the attribute if zero weight
                            cmds.removeAttr(attr)
                            result.removed_targets += 1
                        except:
                            pass

            # Enable GPU blendshapes if available
            if self.settings.enable_gpu_blendshapes:
                try:
                    cmds.setAttr(f"{bs}.useGpu", True)
                    result.gpu_enabled += 1
                except:
                    pass

            result.optimized_blendshapes += 1

        return result