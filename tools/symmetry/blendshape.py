# -*- coding: utf-8 -*-
"""
tools/symmetry/blendshape.py

Blendshape symmetry mapping.
"""

import maya.cmds as cmds # type: ignore
from typing import List, Dict
from .types import SymmetrySettings, BlendshapePair


class BlendshapeMapper:
    """
    Builds symmetry mappings for blendshape targets.
    """

    def __init__(self, settings: SymmetrySettings):
        self.settings = settings
        self._blendshape_cache: Dict[str, List[BlendshapePair]] = {}

    def build_map(self, blendshape_node: str) -> List[BlendshapePair]:
        if not cmds.objExists(blendshape_node):
            return []

        targets = cmds.listAttr(blendshape_node, m=True, string='weight') or []
        if not targets:
            return []

        pairs = []
        used = set()
        patterns = {
            "Left": "Right",
            "Right": "Left",
            "L": "R",
            "R": "L",
            "_l": "_r",
            "_r": "_l",
            ".L": ".R",
            ".R": ".L",
        }
        for tgt in targets:
            if tgt in used:
                continue
            mirror = None
            for pat, rep in patterns.items():
                if pat in tgt:
                    potential = tgt.replace(pat, rep)
                    if potential in targets and potential not in used:
                        mirror = potential
                        break
            if mirror:
                pairs.append(BlendshapePair(source=tgt, target=mirror, confidence=1.0))
                used.add(tgt)
                used.add(mirror)
            else:
                pairs.append(BlendshapePair(source=tgt, target="", confidence=0.0))
        return pairs