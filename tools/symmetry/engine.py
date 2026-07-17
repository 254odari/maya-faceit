# -*- coding: utf-8 -*-
"""
tools/symmetry/engine.py

Main facade for symmetry analysis operations.
"""

import logging
import maya.cmds as cmds # type: ignore
from typing import Optional, List, Dict, Any
from .types import (
    SymmetrySettings, SymmetryPlane, VertexPair, ControllerPair,
    JointPair, BlendshapePair, SymmetryMap, SymmetryReport,
    ValidationResult
)
from .settings import DEFAULT_SYMMETRY_SETTINGS
from .plane import SymmetryPlaneDetector
from .vertex import VertexMapper
from .controller import ControllerMapper
from .joint import JointMapper
from .blendshape import BlendshapeMapper
from .analyzer import MeshAnalyzer
from .validation import SymmetryValidator
from .repair import SymmetryRepair
from .cache import SymmetryCache
from .reporter import SymmetryReporter
from .utils import SymmetryUtils

logger = logging.getLogger(__name__)


class SymmetryAnalyzer:
    """
    Main facade for symmetry analysis operations.
    """

    def __init__(self, settings: Optional[SymmetrySettings] = None):
        self.settings = settings or DEFAULT_SYMMETRY_SETTINGS
        self.plane_detector = SymmetryPlaneDetector()
        self.vertex_mapper = VertexMapper(self.settings)
        self.controller_mapper = ControllerMapper(self.settings)
        self.joint_mapper = JointMapper(self.settings)
        self.blendshape_mapper = BlendshapeMapper(self.settings)
        self.mesh_analyzer = MeshAnalyzer(self.settings)
        self.validator = SymmetryValidator()
        self.repair = SymmetryRepair(self.settings)
        self.cache = SymmetryCache(self.settings.cache_directory)
        self.reporter = SymmetryReporter()
        self._last_map: Optional[SymmetryMap] = None

    # -------------------------------------------------------------------------
    # Plane Detection
    # -------------------------------------------------------------------------
    def detect_plane(self, mesh: str, method: str = "bounding_box") -> Optional[SymmetryPlane]:
        return self.plane_detector.detect_from_mesh(mesh, self.settings.axis, method)

    # -------------------------------------------------------------------------
    # Build Maps
    # -------------------------------------------------------------------------
    def build_map(self, mesh: str, use_cache: bool = True) -> Optional[SymmetryMap]:
        if not cmds.objExists(mesh):
            logger.warning(f"Mesh '{mesh}' does not exist.")
            return None

        if use_cache and self.settings.cache_enabled:
            cached = self.cache.load_map("symmetry", mesh)
            if cached:
                self._last_map = cached
                return cached

        plane = self.detect_plane(mesh)
        if not plane:
            logger.warning("Could not detect symmetry plane.")
            return None

        vertex_pairs = self.vertex_mapper.build_map(mesh, plane)
        if not vertex_pairs:
            logger.warning("No vertex pairs found.")
            return None

        controllers = SymmetryUtils.get_controllers_in_scene()
        controller_pairs = self.controller_mapper.build_map(controllers)

        joints = SymmetryUtils.get_joints_in_scene()
        joint_pairs = self.joint_mapper.build_map(joints)

        blendshape_nodes = SymmetryUtils.get_blendshape_nodes()
        all_blendshape_pairs = []
        for bnode in blendshape_nodes:
            pairs = self.blendshape_mapper.build_map(bnode)
            all_blendshape_pairs.extend(pairs)

        map_data = SymmetryMap(
            mesh=mesh,
            vertices=vertex_pairs,
            controllers=controller_pairs,
            joints=joint_pairs,
            blendshapes=all_blendshape_pairs,
            vertex_count=cmds.polyEvaluate(mesh, vertex=True),
            symmetric_vertex_count=sum(1 for v in vertex_pairs if v.vertex2 != -1),
            asymmetric_vertex_count=sum(1 for v in vertex_pairs if v.vertex2 == -1),
            plane=plane,
            settings=self.settings,
            checksum=self.cache._compute_mesh_checksum(mesh),
        )
        self._last_map = map_data

        if use_cache and self.settings.cache_enabled:
            self.cache.save_map(map_data, "symmetry")

        return map_data

    def build_vertex_map(self, mesh: str, use_cache: bool = True) -> List[VertexPair]:
        map_data = self.build_map(mesh, use_cache)
        return map_data.vertices if map_data else []

    def build_controller_map(self, controllers: Optional[List[str]] = None) -> List[ControllerPair]:
        if controllers is None:
            controllers = SymmetryUtils.get_controllers_in_scene()
        return self.controller_mapper.build_map(controllers)

    def build_joint_map(self, joints: Optional[List[str]] = None) -> List[JointPair]:
        if joints is None:
            joints = SymmetryUtils.get_joints_in_scene()
        return self.joint_mapper.build_map(joints)

    def build_blendshape_map(self, blendshape_node: str) -> List[BlendshapePair]:
        return self.blendshape_mapper.build_map(blendshape_node)

    # -------------------------------------------------------------------------
    # Analysis
    # -------------------------------------------------------------------------
    def analyze_mesh(self, mesh: str) -> Dict[str, Any]:
        vertex_map = self.build_vertex_map(mesh, use_cache=True)
        return self.mesh_analyzer.analyze(mesh, vertex_map)

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------
    def validate(self, mesh: str) -> ValidationResult:
        map_data = self.build_map(mesh, use_cache=True)
        if not map_data:
            return ValidationResult(valid=False, errors=["Failed to build symmetry map."])
        return self.validator.validate_vertex_map(mesh, map_data.vertices)

    # -------------------------------------------------------------------------
    # Repair
    # -------------------------------------------------------------------------
    def repair(self, mesh: str) -> int:
        map_data = self.build_map(mesh, use_cache=True)
        if not map_data:
            return 0
        return self.repair.snap_asymmetric_vertices(mesh, map_data.vertices)

    # -------------------------------------------------------------------------
    # Reporting
    # -------------------------------------------------------------------------
    def report(self, mesh: str) -> Optional[SymmetryReport]:
        map_data = self.build_map(mesh, use_cache=True)
        if not map_data:
            return None
        analysis = self.mesh_analyzer.analyze(mesh, map_data.vertices)
        return self.reporter.generate_report(mesh, map_data, analysis)

    # -------------------------------------------------------------------------
    # Cache Management
    # -------------------------------------------------------------------------
    def save_cache(self, identifier: str = "symmetry") -> bool:
        if not self._last_map:
            return False
        return self.cache.save_map(self._last_map, identifier)

    def load_cache(self, mesh: str, identifier: str = "symmetry") -> Optional[SymmetryMap]:
        return self.cache.load_map(identifier, mesh)

    def clear_cache(self):
        self.vertex_mapper.clear_cache()

    # -------------------------------------------------------------------------
    # Utility
    # -------------------------------------------------------------------------
    def get_plane(self, mesh: str) -> Optional[SymmetryPlane]:
        map_data = self.build_map(mesh, use_cache=True)
        if map_data:
            return map_data.plane
        return self.detect_plane(mesh)

    def get_vertex_pairs(self, mesh: str) -> List[VertexPair]:
        map_data = self.build_map(mesh, use_cache=True)
        return map_data.vertices if map_data else []

    def get_controller_pairs(self, mesh: Optional[str] = None) -> List[ControllerPair]:
        if self._last_map:
            return self._last_map.controllers
        controllers = SymmetryUtils.get_controllers_in_scene()
        return self.controller_mapper.build_map(controllers)


# =============================================================================
# Singleton
# =============================================================================

_analyzer: Optional[SymmetryAnalyzer] = None

def get_analyzer() -> SymmetryAnalyzer:
    """Get the global SymmetryAnalyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = SymmetryAnalyzer()
    return _analyzer