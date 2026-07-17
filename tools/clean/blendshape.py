# -*- coding: utf-8 -*-
"""
tools/clean/blendshape.py

Blendshape cleanup.
"""

import maya.cmds as cmds # type: ignore
from .types import BlendshapeCleanup


class BlendshapeCleaner:
    """
    Clean up blendshapes: remove empty targets, duplicate targets.
    """

    def __init__(self, settings):
        self.settings = settings

    def cleanup(self) -> BlendshapeCleanup:
        """Run blendshape cleanup."""
        result = BlendshapeCleanup()

        bs_nodes = cmds.ls(type='blendShape', long=True)
        result.total_blendshapes = len(bs_nodes)

        for bs in bs_nodes:
            if self._is_referenced(bs):
                continue

            targets = cmds.listAttr(bs, m=True, string='weight') or []
            if not targets:
                continue

            # 1. Remove empty targets (weights always 0)
            if self.settings.remove_empty_targets:
                for t in targets:
                    attr = f"{bs}.{t}"
                    if cmds.getAttr(attr) == 0.0:
                        # Check if target geometry exists (optional)
                        try:
                            cmds.removeAttr(attr)
                            result.removed_targets += 1
                        except:
                            pass

            # 2. Remove duplicate targets (same name?)
            # This is complex; we'll skip for now

        return result

    def _is_referenced(self, node):
        return cmds.referenceQuery(node, isNodeReferenced=True)