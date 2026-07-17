# -*- coding: utf-8 -*-
"""
tools/optimizer/skin.py

SkinCluster optimizations.
"""

import maya.cmds as cmds # type: ignore
from .types import SkinOptimization


class SkinOptimizer:
    """
    Optimize skinClusters.
    """

    def __init__(self, settings):
        self.settings = settings

    def optimize(self) -> SkinOptimization:
        """Run skinCluster optimizations."""
        result = SkinOptimization()

        skins = cmds.ls(type='skinCluster', long=True)
        result.total_skins = len(skins)

        for skin in skins:
            if cmds.referenceQuery(skin, isNodeReferenced=True):
                continue

            # Set max influences
            try:
                cmds.skinCluster(skin, e=True, maximumInfluences=self.settings.max_influences)
                result.max_influences_set += 1
            except:
                pass

            # Enable GPU skinning
            try:
                cmds.setAttr(f"{skin}.gpuSkinning", True)
                result.gpu_enabled += 1
            except:
                pass

            # Remove unused influences (aggressive only)
            if self.settings.level.value == "aggressive":
                # Placeholder - could use skinCluster -removeUnusedInfluence
                pass

            result.optimized_skins += 1

        return result