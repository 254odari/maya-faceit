# -*- coding: utf-8 -*-
"""
tools/freeze/pivots.py

Pivot freezing operations.
"""

import maya.cmds as cmds # type: ignore
from typing import List
from .types import PivotFreeze


class PivotFreezer:
    """
    Freeze pivots on nodes.
    """

    def __init__(self, settings):
        self.settings = settings

    def freeze(self, nodes: List[str]) -> PivotFreeze:
        """Freeze pivots on nodes."""
        result = PivotFreeze()
        result.total_nodes = len(nodes)

        for node in nodes:
            if not cmds.objExists(node):
                result.skipped_nodes += 1
                continue

            if self._is_referenced(node):
                result.skipped_nodes += 1
                continue

            if cmds.lockNode(node, q=True, lock=True)[0]:
                result.skipped_nodes += 1
                continue

            if self._freeze_pivot(node):
                result.frozen_pivots += 1
            else:
                result.skipped_nodes += 1

        return result

    def _freeze_pivot(self, node: str) -> bool:
        """Freeze pivot on a single node."""
        try:
            # Reset rotate pivot to origin
            cmds.xform(node, piv=(0, 0, 0), ws=False)
            # Reset scale pivot
            cmds.xform(node, sp=(0, 0, 0), ws=False)
            return True
        except:
            return False

    def _is_referenced(self, node: str) -> bool:
        return cmds.referenceQuery(node, isNodeReferenced=True)