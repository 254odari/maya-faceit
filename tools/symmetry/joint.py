# -*- coding: utf-8 -*-
"""
tools/symmetry/joint.py

Joint symmetry mapping.
"""

from typing import List, Dict
from .types import SymmetrySettings, JointPair
from .controller import ControllerMapper


class JointMapper:
    """
    Builds symmetry mappings for joints.
    """

    def __init__(self, settings: SymmetrySettings):
        self.settings = settings
        self._joint_cache: Dict[str, List[JointPair]] = {}

    def build_map(self, joints: List[str]) -> List[JointPair]:
        controller_mapper = ControllerMapper(self.settings)
        pairs = controller_mapper._fallback_mapping(joints)
        joint_pairs = []
        for cp in pairs:
            joint_pairs.append(JointPair(source=cp.source, target=cp.target, confidence=cp.confidence))
        return joint_pairs