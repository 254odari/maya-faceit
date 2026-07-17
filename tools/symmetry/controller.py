# -*- coding: utf-8 -*-
"""
tools/symmetry/controller.py

Controller symmetry mapping.
"""

from typing import List, Optional, Dict
from .types import SymmetrySettings, ControllerPair, MatchMethod


class ControllerMapper:
    """
    Builds symmetry mappings for controllers based on naming rules.
    """

    def __init__(self, settings: SymmetrySettings):
        self.settings = settings
        self._name_resolver = None
        self._controller_cache: Dict[str, List[ControllerPair]] = {}

    def set_name_resolver(self, resolver):
        self._name_resolver = resolver

    def build_map(self, controllers: List[str]) -> List[ControllerPair]:
        if not controllers:
            return []

        if self._name_resolver:
            pairs = []
            used = set()
            for ctrl in controllers:
                if ctrl in used:
                    continue
                mirror = self._name_resolver.get_mirror_name(ctrl)
                if mirror and mirror in controllers and mirror not in used:
                    pairs.append(ControllerPair(source=ctrl, target=mirror, confidence=1.0))
                    used.add(ctrl)
                    used.add(mirror)
                else:
                    pairs.append(ControllerPair(source=ctrl, target="", confidence=0.0))
            return pairs

        return self._fallback_mapping(controllers)

    def _fallback_mapping(self, controllers: List[str]) -> List[ControllerPair]:
        patterns = {
            "L_": "R_",
            "R_": "L_",
            "Left": "Right",
            "Right": "Left",
            "_l": "_r",
            "_r": "_l",
            ".L": ".R",
            ".R": ".L",
            "LF": "RT",
            "RT": "LF",
            "_LEFT": "_RIGHT",
            "_RIGHT": "_LEFT",
        }
        pairs = []
        used = set()
        for ctrl in controllers:
            if ctrl in used:
                continue
            mirror = None
            for pat, rep in patterns.items():
                if pat in ctrl:
                    potential = ctrl.replace(pat, rep)
                    if potential in controllers and potential not in used:
                        mirror = potential
                        break
            if mirror:
                pairs.append(ControllerPair(source=ctrl, target=mirror, confidence=1.0))
                used.add(ctrl)
                used.add(mirror)
            else:
                pairs.append(ControllerPair(source=ctrl, target="", confidence=0.0))
        return pairs