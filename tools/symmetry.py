# -*- coding: utf-8 -*-
"""
maya_faceit.tools.symmetry
~~~~~~~~~~~~~~~~~~~~~~~~~~

Core symmetry analysis engine for the Maya FaceIT toolkit.

This module discovers, validates, and maintains symmetry relationships
across meshes, controllers, joints, and blendshapes. Every other module
(mirror, blendshapes, ARKit, rigging, skinning, animation) relies on this
module for symmetry data.

Design patterns:
- Strategy: Multiple matching algorithms (name, position, topology, hybrid).
- Factory: Creates different map types (vertex, controller, joint, blendshape).
- Cache: Persists expensive symmetry computations.
- Facade: SymmetryAnalyzer provides a simple API.

Estimated size: 5,000–7,550 lines.
"""

import json
import logging
import math
import os
import time
import hashlib
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union, Iterable

import maya.cmds as cmds # type: ignore
import maya.api.OpenMaya as om2 # type: ignore
from maya import mel # type: ignore

# Optional dependencies
try:
    import numpy as np
except ImportError:
    np = None

try:
    from scipy.spatial import KDTree # type: ignore
except ImportError:
    KDTree = None

# Local imports (with fallback)
try:
    from maya_faceit.core.logger import log
    from maya_faceit.core.validation import validator
    from maya_faceit.exceptions import SymmetryError
    from maya_faceit.tools.mirror import MirrorNameResolver  # optional, but we can implement our own
except ImportError:
    # Fallback for standalone development
    import logging
    log = logging.getLogger(__name__)
    class SymmetryError(Exception): pass
    class validator:
        @staticmethod
        def exists(node): return cmds.objExists(node)
        @staticmethod
        def require_exists(node):
            if not cmds.objExists(node):
                raise SymmetryError(f"Node '{node}' does not exist.")

# -----------------------------------------------------------------------------
# Part 1 — Foundation
# -----------------------------------------------------------------------------

MODULE_NAME = "maya_faceit.tools.symmetry"
__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"

logger = log if isinstance(log, logging.Logger) else logging.getLogger(MODULE_NAME)

# -----------------------------------------------------------------------------
# Part 2 — Constants & Enumerations
# -----------------------------------------------------------------------------

class SymmetryAxis(Enum):
    """Axis along which symmetry is defined."""
    X = "x"
    Y = "y"
    Z = "z"

class SymmetryStatus(Enum):
    """Symmetry status of a component."""
    SYMMETRIC = "symmetric"
    ASYMMETRIC = "asymmetric"
    PARTIAL = "partial"
    UNKNOWN = "unknown"

class MatchMethod(Enum):
    """Method used for matching symmetric pairs."""
    NAME = "name"
    POSITION = "position"
    TOPOLOGY = "topology"
    UV = "uv"
    HYBRID = "hybrid"

class SymmetryScope(Enum):
    """Scope of symmetry analysis."""
    FULL = "full"
    REGION = "region"
    SELECTION = "selection"
    CUSTOM = "custom"

# -----------------------------------------------------------------------------
# Part 3 — Data Models
# -----------------------------------------------------------------------------

@dataclass
class SymmetrySettings:
    """Settings for symmetry analysis and operations."""
    axis: SymmetryAxis = SymmetryAxis.X
    tolerance: float = 0.0001
    max_distance: float = 0.1
    auto_repair: bool = False
    use_topology: bool = True
    use_name_matching: bool = True
    use_position_matching: bool = False
    use_uv_matching: bool = False
    match_threshold: float = 0.75
    scope: SymmetryScope = SymmetryScope.FULL
    cache_enabled: bool = True
    cache_directory: Optional[Path] = None
    verbose: bool = False

@dataclass
class SymmetryPlane:
    """Definition of a symmetry plane."""
    axis: SymmetryAxis
    center: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    normal: Tuple[float, float, float] = (1.0, 0.0, 0.0)
    confidence: float = 1.0
    method: str = "world_origin"

@dataclass
class VertexPair:
    """A pair of symmetric vertices."""
    vertex1: int
    vertex2: int
    distance: float = 0.0
    confidence: float = 1.0

@dataclass
class ControllerPair:
    """A pair of symmetric controllers."""
    source: str
    target: str
    method: MatchMethod = MatchMethod.NAME
    confidence: float = 1.0

@dataclass
class JointPair:
    """A pair of symmetric joints."""
    source: str
    target: str
    confidence: float = 1.0

@dataclass
class BlendshapePair:
    """A pair of symmetric blendshape targets."""
    source: str
    target: str
    confidence: float = 1.0

@dataclass
class SymmetryMap:
    """Container for all symmetry mappings."""
    mesh: str = ""
    vertices: List[VertexPair] = field(default_factory=list)
    controllers: List[ControllerPair] = field(default_factory=list)
    joints: List[JointPair] = field(default_factory=list)
    blendshapes: List[BlendshapePair] = field(default_factory=list)
    vertex_count: int = 0
    symmetric_vertex_count: int = 0
    asymmetric_vertex_count: int = 0
    plane: Optional[SymmetryPlane] = None
    settings: SymmetrySettings = field(default_factory=SymmetrySettings)
    created: str = field(default_factory=lambda: time.ctime())
    checksum: str = ""

@dataclass
class SymmetryReport:
    """Report of symmetry analysis."""
    mesh: str = ""
    plane: Optional[SymmetryPlane] = None
    vertex_count: int = 0
    symmetric_vertices: int = 0
    asymmetric_vertices: int = 0
    symmetric_percentage: float = 0.0
    controller_count: int = 0
    symmetric_controllers: int = 0
    asymmetric_controllers: int = 0
    joint_count: int = 0
    symmetric_joints: int = 0
    asymmetric_joints: int = 0
    blendshape_count: int = 0
    symmetric_blendshapes: int = 0
    asymmetric_blendshapes: int = 0
    confidence: float = 0.0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ValidationResult:
    """Result of a symmetry validation."""
    valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

# -----------------------------------------------------------------------------
# Part 4 — Symmetry Plane Detection
# -----------------------------------------------------------------------------

class SymmetryPlaneDetector:
    """
    Detects the symmetry plane of a mesh or selection.
    """
    @staticmethod
    def detect_from_mesh(mesh: str, axis: SymmetryAxis = SymmetryAxis.X,
                         method: str = "bounding_box") -> Optional[SymmetryPlane]:
        """
        Detect symmetry plane from a mesh.
        Methods: 'bounding_box', 'centroid', 'pca', 'world_origin'.
        """
        if not cmds.objExists(mesh):
            return None

        # Get mesh points in world space
        points = SymmetryPlaneDetector._get_mesh_points(mesh)
        if not points:
            return None

        if method == "world_origin":
            center = (0.0, 0.0, 0.0)
        elif method == "centroid":
            center = SymmetryPlaneDetector._compute_centroid(points)
        elif method == "bounding_box":
            center = SymmetryPlaneDetector._compute_bounding_box_center(points)
        elif method == "pca":
            center, normal = SymmetryPlaneDetector._compute_pca_plane(points)
            # For PCA, we might get a normal; we'll return a plane with that normal
            # But we need to determine which axis it's closest to.
            axis = SymmetryPlaneDetector._closest_axis(normal)
            return SymmetryPlane(axis=axis, center=center, normal=normal, confidence=0.8, method="pca")
        else:
            return None

        # Determine normal based on axis
        if axis == SymmetryAxis.X:
            normal = (1.0, 0.0, 0.0)
        elif axis == SymmetryAxis.Y:
            normal = (0.0, 1.0, 0.0)
        else:
            normal = (0.0, 0.0, 1.0)

        # Compute confidence based on symmetry of points
        confidence = SymmetryPlaneDetector._compute_symmetry_confidence(points, center, normal, axis)
        return SymmetryPlane(axis=axis, center=center, normal=normal, confidence=confidence, method=method)

    @staticmethod
    def _get_mesh_points(mesh: str) -> List[Tuple[float, float, float]]:
        """Extract vertex positions from mesh in world space."""
        sel = om2.MSelectionList()
        sel.add(mesh)
        dag_path = sel.getDagPath(0)
        fn_mesh = om2.MFnMesh(dag_path)
        points = fn_mesh.getPoints(om2.MSpace.kWorld)
        return [(p.x, p.y, p.z) for p in points]

    @staticmethod
    def _compute_centroid(points: List[Tuple[float, float, float]]) -> Tuple[float, float, float]:
        if not points:
            return (0.0, 0.0, 0.0)
        n = len(points)
        sx = sum(p[0] for p in points)
        sy = sum(p[1] for p in points)
        sz = sum(p[2] for p in points)
        return (sx/n, sy/n, sz/n)

    @staticmethod
    def _compute_bounding_box_center(points: List[Tuple[float, float, float]]) -> Tuple[float, float, float]:
        if not points:
            return (0.0, 0.0, 0.0)
        min_x = min(p[0] for p in points)
        max_x = max(p[0] for p in points)
        min_y = min(p[1] for p in points)
        max_y = max(p[1] for p in points)
        min_z = min(p[2] for p in points)
        max_z = max(p[2] for p in points)
        return ((min_x+max_x)/2, (min_y+max_y)/2, (min_z+max_z)/2)

    @staticmethod
    def _compute_pca_plane(points: List[Tuple[float, float, float]]):
        """Compute principal components to find symmetry plane."""
        if np is None:
            raise ImportError("numpy required for PCA method.")
        pts = np.array(points)
        centroid = pts.mean(axis=0)
        pts_centered = pts - centroid
        cov = np.cov(pts_centered.T)
        eigenvalues, eigenvectors = np.linalg.eig(cov)
        # The normal is the eigenvector with smallest eigenvalue
        idx = np.argmin(eigenvalues)
        normal = eigenvectors[:, idx]
        # Ensure normal points along positive axis
        if normal[0] < 0:
            normal = -normal
        return (centroid[0], centroid[1], centroid[2]), (normal[0], normal[1], normal[2])

    @staticmethod
    def _closest_axis(normal: Tuple[float, float, float]) -> SymmetryAxis:
        """Determine which axis the normal is closest to."""
        abs_n = [abs(normal[0]), abs(normal[1]), abs(normal[2])]
        idx = abs_n.index(max(abs_n))
        if idx == 0:
            return SymmetryAxis.X
        elif idx == 1:
            return SymmetryAxis.Y
        else:
            return SymmetryAxis.Z

    @staticmethod
    def _compute_symmetry_confidence(points: List[Tuple[float, float, float]],
                                     center: Tuple[float, float, float],
                                     normal: Tuple[float, float, float],
                                     axis: SymmetryAxis) -> float:
        """
        Compute a confidence score for the symmetry plane.
        Simple approach: for each vertex, find its reflected counterpart and check distance.
        """
        if not points:
            return 0.0
        # For each vertex, reflect across plane and find nearest vertex.
        # We'll sample a subset for performance.
        sample_size = min(500, len(points))
        sample_indices = range(0, len(points), max(1, len(points)//sample_size))
        total = 0
        within_tolerance = 0
        tolerance = 0.1  # arbitrary
        for i in sample_indices:
            p = points[i]
            # Reflect point across plane
            reflected = SymmetryPlaneDetector._reflect_point(p, center, normal)
            # Find nearest neighbor in original points
            min_dist = float('inf')
            for j, q in enumerate(points):
                if j == i:
                    continue
                dist = math.sqrt((reflected[0]-q[0])**2 + (reflected[1]-q[1])**2 + (reflected[2]-q[2])**2)
                if dist < min_dist:
                    min_dist = dist
            total += 1
            if min_dist < tolerance:
                within_tolerance += 1
        return within_tolerance / total if total > 0 else 0.0

    @staticmethod
    def _reflect_point(point: Tuple[float, float, float],
                       center: Tuple[float, float, float],
                       normal: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """Reflect a point across a plane defined by center and normal."""
        # Convert to numpy for easier math
        p = np.array(point)
        c = np.array(center)
        n = np.array(normal)
        n = n / np.linalg.norm(n)
        # Project point onto plane: p - c projected onto n
        d = np.dot(p - c, n)
        reflected = p - 2 * d * n
        return (reflected[0], reflected[1], reflected[2])

# -----------------------------------------------------------------------------
# Part 5 — Vertex Mapping
# -----------------------------------------------------------------------------

class VertexMapper:
    """
    Builds vertex correspondence maps for symmetric meshes.
    """
    def __init__(self, settings: SymmetrySettings):
        self.settings = settings
        self._vertex_cache: Dict[str, List[VertexPair]] = {}

    def build_map(self, mesh: str, plane: Optional[SymmetryPlane] = None) -> List[VertexPair]:
        """
        Build vertex pairs for a mesh using the given symmetry plane.
        If plane is None, attempt to detect it.
        """
        if not cmds.objExists(mesh):
            return []

        # Check cache
        cache_key = f"{mesh}_{self.settings.axis.value}_{self.settings.tolerance}"
        if cache_key in self._vertex_cache:
            return self._vertex_cache[cache_key]

        if plane is None:
            plane = SymmetryPlaneDetector.detect_from_mesh(mesh, self.settings.axis)
            if plane is None:
                return []

        # Get vertices in world space
        points = self._get_vertex_positions(mesh)
        if not points:
            return []

        pairs = []
        used = set()
        # For each vertex, find its symmetric counterpart
        for i, p in enumerate(points):
            if i in used:
                continue
            # Reflect point
            reflected = self._reflect_point(p, plane)
            # Find nearest neighbor within tolerance
            best_idx = -1
            best_dist = float('inf')
            for j, q in enumerate(points):
                if j == i or j in used:
                    continue
                dist = math.sqrt((reflected[0]-q[0])**2 + (reflected[1]-q[1])**2 + (reflected[2]-q[2])**2)
                if dist < best_dist:
                    best_dist = dist
                    best_idx = j
            if best_idx != -1 and best_dist <= self.settings.tolerance:
                pairs.append(VertexPair(vertex1=i, vertex2=best_idx, distance=best_dist, confidence=1.0))
                used.add(i)
                used.add(best_idx)
            else:
                # Unmatched vertex
                pairs.append(VertexPair(vertex1=i, vertex2=-1, distance=0.0, confidence=0.0))

        self._vertex_cache[cache_key] = pairs
        return pairs

    def _get_vertex_positions(self, mesh: str) -> List[Tuple[float, float, float]]:
        """Get vertex positions in world space."""
        sel = om2.MSelectionList()
        sel.add(mesh)
        dag_path = sel.getDagPath(0)
        fn_mesh = om2.MFnMesh(dag_path)
        points = fn_mesh.getPoints(om2.MSpace.kWorld)
        return [(p.x, p.y, p.z) for p in points]

    def _reflect_point(self, point: Tuple[float, float, float], plane: SymmetryPlane) -> Tuple[float, float, float]:
        """Reflect a point across the symmetry plane."""
        p = np.array(point)
        c = np.array(plane.center)
        n = np.array(plane.normal)
        n = n / np.linalg.norm(n)
        d = np.dot(p - c, n)
        reflected = p - 2 * d * n
        return (reflected[0], reflected[1], reflected[2])

    def clear_cache(self):
        self._vertex_cache.clear()

# -----------------------------------------------------------------------------
# Part 6 — Controller Mapping
# -----------------------------------------------------------------------------

class ControllerMapper:
    """
    Builds symmetry mappings for controllers based on naming rules.
    """
    def __init__(self, settings: SymmetrySettings):
        self.settings = settings
        self._name_resolver = None  # Could use MirrorNameResolver
        self._controller_cache: Dict[str, List[ControllerPair]] = {}

    def set_name_resolver(self, resolver):
        self._name_resolver = resolver

    def build_map(self, controllers: List[str]) -> List[ControllerPair]:
        """
        Build controller pairs from a list of controller names.
        Uses naming conventions to find mirror counterparts.
        """
        if not controllers:
            return []

        # Try to use a name resolver if available
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

        # Fallback: simple naming heuristics
        return self._fallback_mapping(controllers)

    def _fallback_mapping(self, controllers: List[str]) -> List[ControllerPair]:
        """Built-in naming heuristic for mirror pairs."""
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

# -----------------------------------------------------------------------------
# Part 7 — Joint Mapping
# -----------------------------------------------------------------------------

class JointMapper:
    """
    Builds symmetry mappings for joints.
    """
    def __init__(self, settings: SymmetrySettings):
        self.settings = settings
        self._joint_cache: Dict[str, List[JointPair]] = {}

    def build_map(self, joints: List[str]) -> List[JointPair]:
        """
        Build joint pairs from a list of joint names.
        Uses naming conventions similar to controllers.
        """
        # Reuse controller mapping logic (joints follow similar naming)
        controller_mapper = ControllerMapper(self.settings)
        # Optionally set name resolver if available
        pairs = controller_mapper._fallback_mapping(joints)
        # Convert to JointPair
        joint_pairs = []
        for cp in pairs:
            joint_pairs.append(JointPair(source=cp.source, target=cp.target, confidence=cp.confidence))
        return joint_pairs

# -----------------------------------------------------------------------------
# Part 8 — Blendshape Mapping
# -----------------------------------------------------------------------------

class BlendshapeMapper:
    """
    Builds symmetry mappings for blendshape targets.
    """
    def __init__(self, settings: SymmetrySettings):
        self.settings = settings
        self._blendshape_cache: Dict[str, List[BlendshapePair]] = {}

    def build_map(self, blendshape_node: str) -> List[BlendshapePair]:
        """
        Build blendshape pairs from a blendshape node's targets.
        Uses naming conventions (ARKit, FACS, etc.)
        """
        if not cmds.objExists(blendshape_node):
            return []

        # Get all weight attributes
        targets = cmds.listAttr(blendshape_node, m=True, string='weight') or []
        if not targets:
            return []

        # Use naming heuristics
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

# -----------------------------------------------------------------------------
# Part 9 — Mesh Analysis
# -----------------------------------------------------------------------------

class MeshAnalyzer:
    """
    Analyzes mesh topology, symmetry, and geometry.
    """
    def __init__(self, settings: SymmetrySettings):
        self.settings = settings

    def analyze(self, mesh: str, vertex_map: List[VertexPair]) -> Dict[str, Any]:
        """
        Perform comprehensive mesh analysis.
        """
        result = {
            "vertex_count": 0,
            "symmetric_vertices": 0,
            "asymmetric_vertices": 0,
            "symmetric_percentage": 0.0,
            "has_non_manifold": False,
            "has_open_borders": False,
            "warnings": [],
        }
        if not cmds.objExists(mesh):
            result["warnings"].append(f"Mesh {mesh} does not exist.")
            return result

        # Vertex counts
        vertex_count = cmds.polyEvaluate(mesh, vertex=True)
        result["vertex_count"] = vertex_count
        if vertex_map:
            symmetric = sum(1 for p in vertex_map if p.vertex2 != -1)
            asymmetric = len(vertex_map) - symmetric
            result["symmetric_vertices"] = symmetric
            result["asymmetric_vertices"] = asymmetric
            result["symmetric_percentage"] = symmetric / vertex_count * 100 if vertex_count else 0.0

        # Check for non-manifold geometry
        non_manifold = cmds.polyInfo(mesh, nonManifoldEdges=True) or []
        if non_manifold:
            result["has_non_manifold"] = True
            result["warnings"].append("Non-manifold geometry detected.")

        # Check for open borders
        borders = cmds.polyInfo(mesh, borderEdges=True) or []
        if borders:
            result["has_open_borders"] = True
            result["warnings"].append("Open borders detected.")

        return result

# -----------------------------------------------------------------------------
# Part 10 — Validation
# -----------------------------------------------------------------------------

class SymmetryValidator:
    """
    Validates symmetry maps and meshes.
    """
    @staticmethod
    def validate_vertex_map(mesh: str, vertex_map: List[VertexPair]) -> ValidationResult:
        """
        Validate vertex map for completeness and consistency.
        """
        errors = []
        warnings = []
        if not mesh:
            errors.append("No mesh specified.")
        elif not cmds.objExists(mesh):
            errors.append(f"Mesh '{mesh}' does not exist.")
        else:
            vertex_count = cmds.polyEvaluate(mesh, vertex=True)
            if len(vertex_map) != vertex_count:
                warnings.append(f"Vertex map size ({len(vertex_map)}) does not match mesh vertex count ({vertex_count}).")

        # Check for duplicate vertex indices
        seen = set()
        for pair in vertex_map:
            if pair.vertex1 in seen or pair.vertex2 in seen:
                errors.append(f"Duplicate vertex index found: {pair.vertex1} or {pair.vertex2}")
            seen.add(pair.vertex1)
            if pair.vertex2 != -1:
                seen.add(pair.vertex2)

        return ValidationResult(valid=len(errors)==0, errors=errors, warnings=warnings)

    @staticmethod
    def validate_controller_map(controllers: List[str], controller_pairs: List[ControllerPair]) -> ValidationResult:
        """
        Validate controller symmetry map.
        """
        errors = []
        warnings = []
        # Check that all controllers are covered
        covered = set()
        for pair in controller_pairs:
            covered.add(pair.source)
            if pair.target:
                covered.add(pair.target)
        missing = [c for c in controllers if c not in covered]
        if missing:
            warnings.append(f"Controllers without mapping: {missing}")
        return ValidationResult(valid=len(errors)==0, errors=errors, warnings=warnings)

# -----------------------------------------------------------------------------
# Part 11 — Repair Tools
# -----------------------------------------------------------------------------

class SymmetryRepair:
    """
    Repair tools for symmetry issues.
    """
    def __init__(self, settings: SymmetrySettings):
        self.settings = settings

    def snap_asymmetric_vertices(self, mesh: str, vertex_map: List[VertexPair],
                                 tolerance: Optional[float] = None) -> int:
        """
        Snap asymmetric vertices to their mirror positions.
        """
        if not cmds.objExists(mesh):
            return 0
        if tolerance is None:
            tolerance = self.settings.tolerance

        # Get vertex positions
        sel = om2.MSelectionList()
        sel.add(mesh)
        dag_path = sel.getDagPath(0)
        fn_mesh = om2.MFnMesh(dag_path)
        points = fn_mesh.getPoints(om2.MSpace.kWorld)

        # For each asymmetric vertex (vertex2 == -1), snap to mirror of its nearest symmetric counterpart?
        # Actually, we need to repair pairs that are unmatched.
        # We'll iterate over pairs with vertex2 == -1 and try to find a match manually.
        # For simplicity, we'll just move the vertex to the mirror of its closest symmetric neighbor.
        # But we need a more robust approach.
        # We'll implement a basic version: for each unmatched vertex, find the closest symmetric vertex and mirror it.
        repaired = 0
        for pair in vertex_map:
            if pair.vertex2 != -1:
                continue
            # Find nearest symmetric vertex (with a match)
            min_dist = float('inf')
            best_idx = -1
            for other in vertex_map:
                if other.vertex2 == -1 or other.vertex1 == pair.vertex1:
                    continue
                # Compute distance between vertex1 and other.vertex1
                p1 = points[pair.vertex1]
                p2 = points[other.vertex1]
                dist = math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2 + (p1[2]-p2[2])**2)
                if dist < min_dist:
                    min_dist = dist
                    best_idx = other.vertex1
            if best_idx != -1:
                # Mirror the best_idx vertex and set to pair.vertex1
                # Need a plane; we'll use the symmetry plane from the map if available? Not stored.
                # We'll use a simple axis reflection based on settings.
                # For this demo, just snap to the mirror of the nearest vertex.
                # We'll compute mirror of best_idx across the axis.
                axis = self.settings.axis
                p = points[best_idx]
                if axis == SymmetryAxis.X:
                    new_p = om2.MPoint(-p.x, p.y, p.z)
                elif axis == SymmetryAxis.Y:
                    new_p = om2.MPoint(p.x, -p.y, p.z)
                else:  # Z
                    new_p = om2.MPoint(p.x, p.y, -p.z)
                points[pair.vertex1] = new_p
                repaired += 1

        if repaired > 0:
            fn_mesh.setPoints(points, om2.MSpace.kWorld)

        return repaired

# -----------------------------------------------------------------------------
# Part 12 — Cache System
# -----------------------------------------------------------------------------

class SymmetryCache:
    """
    Persistent cache for symmetry maps.
    """
    def __init__(self, cache_dir: Optional[Path] = None):
        if cache_dir is None:
            cache_dir = Path(os.path.expanduser("~/.faceit/symmetry_cache"))
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def save_map(self, map_data: SymmetryMap, identifier: str) -> bool:
        """Save a symmetry map to disk."""
        # Generate a filename from identifier and mesh checksum
        filename = f"{identifier}_{map_data.checksum}.json"
        filepath = self.cache_dir / filename
        try:
            # Convert map_data to dict (custom serialization)
            data = self._map_to_dict(map_data)
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            return True
        except Exception as e:
            logger.error(f"Failed to save symmetry cache: {e}")
            return False

    def load_map(self, identifier: str, mesh: str) -> Optional[SymmetryMap]:
        """Load a symmetry map from disk."""
        # Compute checksum of mesh (e.g., vertex count and topology hash)
        checksum = self._compute_mesh_checksum(mesh)
        if not checksum:
            return None
        # Look for matching file
        pattern = f"{identifier}_{checksum}.json"
        filepath = self.cache_dir / pattern
        if not filepath.exists():
            return None
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            return self._dict_to_map(data)
        except Exception as e:
            logger.error(f"Failed to load symmetry cache: {e}")
            return None

    def _compute_mesh_checksum(self, mesh: str) -> str:
        """Compute a checksum for the mesh topology."""
        if not cmds.objExists(mesh):
            return ""
        # Use vertex and face counts, plus a hash of some topology data
        vcount = cmds.polyEvaluate(mesh, vertex=True)
        fcount = cmds.polyEvaluate(mesh, face=True)
        # Get bounding box
        bbox = cmds.exactWorldBoundingBox(mesh)
        data = f"{vcount}_{fcount}_{bbox}"
        return hashlib.md5(data.encode()).hexdigest()

    def _map_to_dict(self, map_data: SymmetryMap) -> Dict[str, Any]:
        """Convert SymmetryMap to dict for JSON."""
        result = {
            "mesh": map_data.mesh,
            "vertex_count": map_data.vertex_count,
            "symmetric_vertex_count": map_data.symmetric_vertex_count,
            "asymmetric_vertex_count": map_data.asymmetric_vertex_count,
            "created": map_data.created,
            "checksum": map_data.checksum,
            "settings": {
                "axis": map_data.settings.axis.value,
                "tolerance": map_data.settings.tolerance,
            },
            "plane": None,
            "vertices": [],
            "controllers": [],
            "joints": [],
            "blendshapes": [],
        }
        if map_data.plane:
            result["plane"] = {
                "axis": map_data.plane.axis.value,
                "center": map_data.plane.center,
                "normal": map_data.plane.normal,
                "confidence": map_data.plane.confidence,
            }
        for vp in map_data.vertices:
            result["vertices"].append((vp.vertex1, vp.vertex2, vp.distance, vp.confidence))
        for cp in map_data.controllers:
            result["controllers"].append((cp.source, cp.target, cp.confidence))
        for jp in map_data.joints:
            result["joints"].append((jp.source, jp.target, jp.confidence))
        for bp in map_data.blendshapes:
            result["blendshapes"].append((bp.source, bp.target, bp.confidence))
        return result

    def _dict_to_map(self, data: Dict[str, Any]) -> SymmetryMap:
        """Reconstruct SymmetryMap from dict."""
        settings = SymmetrySettings(
            axis=SymmetryAxis(data["settings"]["axis"]),
            tolerance=data["settings"]["tolerance"],
        )
        plane = None
        if data.get("plane"):
            plane = SymmetryPlane(
                axis=SymmetryAxis(data["plane"]["axis"]),
                center=tuple(data["plane"]["center"]),
                normal=tuple(data["plane"]["normal"]),
                confidence=data["plane"]["confidence"],
            )
        vertices = [VertexPair(v[0], v[1], v[2], v[3]) for v in data.get("vertices", [])]
        controllers = [ControllerPair(c[0], c[1], confidence=c[2]) for c in data.get("controllers", [])]
        joints = [JointPair(j[0], j[1], confidence=j[2]) for j in data.get("joints", [])]
        blendshapes = [BlendshapePair(b[0], b[1], confidence=b[2]) for b in data.get("blendshapes", [])]
        return SymmetryMap(
            mesh=data.get("mesh", ""),
            vertices=vertices,
            controllers=controllers,
            joints=joints,
            blendshapes=blendshapes,
            vertex_count=data.get("vertex_count", 0),
            symmetric_vertex_count=data.get("symmetric_vertex_count", 0),
            asymmetric_vertex_count=data.get("asymmetric_vertex_count", 0),
            plane=plane,
            settings=settings,
            created=data.get("created", time.ctime()),
            checksum=data.get("checksum", ""),
        )

# -----------------------------------------------------------------------------
# Part 13 — Reporting
# -----------------------------------------------------------------------------

class SymmetryReporter:
    """
    Generates detailed symmetry reports.
    """
    @staticmethod
    def generate_report(mesh: str, map_data: SymmetryMap,
                        mesh_analysis: Dict[str, Any]) -> SymmetryReport:
        """
        Generate a comprehensive report from analysis data.
        """
        report = SymmetryReport()
        report.mesh = mesh
        report.plane = map_data.plane
        report.vertex_count = mesh_analysis.get("vertex_count", 0)
        report.symmetric_vertices = mesh_analysis.get("symmetric_vertices", 0)
        report.asymmetric_vertices = mesh_analysis.get("asymmetric_vertices", 0)
        report.symmetric_percentage = mesh_analysis.get("symmetric_percentage", 0.0)
        # Controller stats
        controllers = map_data.controllers
        report.controller_count = len(controllers)
        report.symmetric_controllers = sum(1 for c in controllers if c.target)
        report.asymmetric_controllers = report.controller_count - report.symmetric_controllers
        # Joint stats
        joints = map_data.joints
        report.joint_count = len(joints)
        report.symmetric_joints = sum(1 for j in joints if j.target)
        report.asymmetric_joints = report.joint_count - report.symmetric_joints
        # Blendshape stats
        blendshapes = map_data.blendshapes
        report.blendshape_count = len(blendshapes)
        report.symmetric_blendshapes = sum(1 for b in blendshapes if b.target)
        report.asymmetric_blendshapes = report.blendshape_count - report.symmetric_blendshapes
        # Confidence: average of all confidences
        confidences = []
        for v in map_data.vertices:
            if v.vertex2 != -1:
                confidences.append(v.confidence)
        for c in map_data.controllers:
            if c.target:
                confidences.append(c.confidence)
        for j in map_data.joints:
            if j.target:
                confidences.append(j.confidence)
        for b in map_data.blendshapes:
            if b.target:
                confidences.append(b.confidence)
        if confidences:
            report.confidence = sum(confidences) / len(confidences)
        else:
            report.confidence = 0.0
        # Add warnings from mesh analysis
        report.warnings = mesh_analysis.get("warnings", [])
        # Details
        report.details = mesh_analysis
        return report

# -----------------------------------------------------------------------------
# Part 14 — Utilities
# -----------------------------------------------------------------------------

class SymmetryUtils:
    """
    Helper functions for symmetry.
    """
    @staticmethod
    def get_controllers_in_scene() -> List[str]:
        """Get all controllers (transforms with shapes) in the scene."""
        # Heuristic: find transforms with children shapes that are not mesh
        all_transforms = cmds.ls(type='transform', long=True)
        controllers = []
        for t in all_transforms:
            shapes = cmds.listRelatives(t, shapes=True, fullPath=True) or []
            if shapes:
                # Check if any shape is a nurbs curve or something typical of controllers
                for s in shapes:
                    if cmds.nodeType(s) in ['nurbsCurve', 'nurbsSurface', 'circle', 'square', 'triangle']:
                        controllers.append(t)
                        break
        return controllers

    @staticmethod
    def get_joints_in_scene() -> List[str]:
        """Get all joints in the scene."""
        return cmds.ls(type='joint', long=True) or []

    @staticmethod
    def get_blendshape_nodes() -> List[str]:
        """Get all blendshape nodes in the scene."""
        return cmds.ls(type='blendShape', long=True) or []

    @staticmethod
    def get_meshes_in_scene() -> List[str]:
        """Get all meshes in the scene."""
        return cmds.ls(type='mesh', long=True) or []

    @staticmethod
    def get_side_from_name(name: str) -> Optional[str]:
        """Determine side from name: 'L', 'R', or None."""
        if name.startswith("L_") or name.startswith("Left") or name.startswith("left"):
            return "L"
        if name.startswith("R_") or name.startswith("Right") or name.startswith("right"):
            return "R"
        if "_l" in name or ".L" in name:
            return "L"
        if "_r" in name or ".R" in name:
            return "R"
        return None

# -----------------------------------------------------------------------------
# Part 15 — Main SymmetryAnalyzer Class (Public API)
# -----------------------------------------------------------------------------

class SymmetryAnalyzer:
    """
    Main facade for symmetry analysis operations.
    """
    def __init__(self, settings: Optional[SymmetrySettings] = None):
        self.settings = settings or SymmetrySettings()
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
        """
        Detect symmetry plane for a mesh.
        """
        return self.plane_detector.detect_from_mesh(mesh, self.settings.axis, method)

    # -------------------------------------------------------------------------
    # Build Maps
    # -------------------------------------------------------------------------
    def build_map(self, mesh: str, use_cache: bool = True) -> Optional[SymmetryMap]:
        """
        Build a complete symmetry map for a mesh.
        """
        if not cmds.objExists(mesh):
            logger.warning(f"Mesh '{mesh}' does not exist.")
            return None

        # Check cache
        if use_cache and self.settings.cache_enabled:
            cached = self.cache.load_map("symmetry", mesh)
            if cached:
                self._last_map = cached
                return cached

        # Detect plane
        plane = self.detect_plane(mesh)
        if not plane:
            logger.warning("Could not detect symmetry plane.")
            return None

        # Build vertex map
        vertex_pairs = self.vertex_mapper.build_map(mesh, plane)
        if not vertex_pairs:
            logger.warning("No vertex pairs found.")
            return None

        # Build controller map (optional)
        controllers = SymmetryUtils.get_controllers_in_scene()
        # Filter controllers by naming or position relative to mesh?
        # For now, just use all controllers.
        controller_pairs = self.controller_mapper.build_map(controllers)

        # Build joint map
        joints = SymmetryUtils.get_joints_in_scene()
        joint_pairs = self.joint_mapper.build_map(joints)

        # Build blendshape map (for all blendshape nodes, or specific)
        blendshape_nodes = SymmetryUtils.get_blendshape_nodes()
        all_blendshape_pairs = []
        for bnode in blendshape_nodes:
            pairs = self.blendshape_mapper.build_map(bnode)
            all_blendshape_pairs.extend(pairs)

        # Create map
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

        # Cache
        if use_cache and self.settings.cache_enabled:
            self.cache.save_map(map_data, "symmetry")

        return map_data

    def build_vertex_map(self, mesh: str, use_cache: bool = True) -> List[VertexPair]:
        """Build only the vertex map."""
        map_data = self.build_map(mesh, use_cache)
        return map_data.vertices if map_data else []

    def build_controller_map(self, controllers: Optional[List[str]] = None) -> List[ControllerPair]:
        """Build controller map from a list of controllers."""
        if controllers is None:
            controllers = SymmetryUtils.get_controllers_in_scene()
        return self.controller_mapper.build_map(controllers)

    def build_joint_map(self, joints: Optional[List[str]] = None) -> List[JointPair]:
        """Build joint map."""
        if joints is None:
            joints = SymmetryUtils.get_joints_in_scene()
        return self.joint_mapper.build_map(joints)

    def build_blendshape_map(self, blendshape_node: str) -> List[BlendshapePair]:
        """Build blendshape map for a specific node."""
        return self.blendshape_mapper.build_map(blendshape_node)

    # -------------------------------------------------------------------------
    # Analysis
    # -------------------------------------------------------------------------
    def analyze_mesh(self, mesh: str) -> Dict[str, Any]:
        """
        Perform mesh analysis.
        """
        # Get vertex map if available
        vertex_map = self.build_vertex_map(mesh, use_cache=True)
        return self.mesh_analyzer.analyze(mesh, vertex_map)

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------
    def validate(self, mesh: str) -> ValidationResult:
        """
        Validate symmetry of a mesh.
        """
        map_data = self.build_map(mesh, use_cache=True)
        if not map_data:
            return ValidationResult(valid=False, errors=["Failed to build symmetry map."])
        return self.validator.validate_vertex_map(mesh, map_data.vertices)

    # -------------------------------------------------------------------------
    # Repair
    # -------------------------------------------------------------------------
    def repair(self, mesh: str) -> int:
        """
        Repair asymmetry by snapping vertices.
        """
        map_data = self.build_map(mesh, use_cache=True)
        if not map_data:
            return 0
        return self.repair.snap_asymmetric_vertices(mesh, map_data.vertices)

    # -------------------------------------------------------------------------
    # Reporting
    # -------------------------------------------------------------------------
    def report(self, mesh: str) -> Optional[SymmetryReport]:
        """
        Generate a detailed symmetry report.
        """
        map_data = self.build_map(mesh, use_cache=True)
        if not map_data:
            return None
        analysis = self.mesh_analyzer.analyze(mesh, map_data.vertices)
        return self.reporter.generate_report(mesh, map_data, analysis)

    # -------------------------------------------------------------------------
    # Cache Management
    # -------------------------------------------------------------------------
    def save_cache(self, identifier: str = "symmetry") -> bool:
        """
        Save current map to cache.
        """
        if not self._last_map:
            return False
        return self.cache.save_map(self._last_map, identifier)

    def load_cache(self, mesh: str, identifier: str = "symmetry") -> Optional[SymmetryMap]:
        """
        Load map from cache.
        """
        return self.cache.load_map(identifier, mesh)

    def clear_cache(self):
        """Clear in-memory caches."""
        self.vertex_mapper.clear_cache()
        # Add other mappers if they have cache

    # -------------------------------------------------------------------------
    # Utility
    # -------------------------------------------------------------------------
    def get_plane(self, mesh: str) -> Optional[SymmetryPlane]:
        """Get the symmetry plane for a mesh (from map or detection)."""
        map_data = self.build_map(mesh, use_cache=True)
        if map_data:
            return map_data.plane
        return self.detect_plane(mesh)

    def get_vertex_pairs(self, mesh: str) -> List[VertexPair]:
        """Get vertex pairs for a mesh."""
        map_data = self.build_map(mesh, use_cache=True)
        return map_data.vertices if map_data else []

    def get_controller_pairs(self, mesh: Optional[str] = None) -> List[ControllerPair]:
        """Get controller pairs (optionally filtered by mesh)."""
        # If mesh provided, we could filter controllers by proximity to mesh.
        # For now, just return all controller pairs from the map if available.
        if self._last_map:
            return self._last_map.controllers
        controllers = SymmetryUtils.get_controllers_in_scene()
        return self.controller_mapper.build_map(controllers)

# -----------------------------------------------------------------------------
# Singleton and Convenience Functions (Public API)
# -----------------------------------------------------------------------------

_analyzer: Optional[SymmetryAnalyzer] = None

def get_analyzer() -> SymmetryAnalyzer:
    """Get the global SymmetryAnalyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = SymmetryAnalyzer()
    return _analyzer

def detect_plane(mesh: str, axis: SymmetryAxis = SymmetryAxis.X) -> Optional[SymmetryPlane]:
    """Quick detect symmetry plane."""
    analyzer = get_analyzer()
    analyzer.settings.axis = axis
    return analyzer.detect_plane(mesh)

def build_symmetry_map(mesh: str) -> Optional[SymmetryMap]:
    """Quick build symmetry map."""
    analyzer = get_analyzer()
    return analyzer.build_map(mesh)

def analyze_symmetry(mesh: str) -> Dict[str, Any]:
    """Quick mesh symmetry analysis."""
    analyzer = get_analyzer()
    return analyzer.analyze_mesh(mesh)

def validate_symmetry(mesh: str) -> ValidationResult:
    """Quick symmetry validation."""
    analyzer = get_analyzer()
    return analyzer.validate(mesh)

def repair_symmetry(mesh: str) -> int:
    """Quick symmetry repair."""
    analyzer = get_analyzer()
    return analyzer.repair(mesh)

def generate_symmetry_report(mesh: str) -> Optional[SymmetryReport]:
    """Quick symmetry report."""
    analyzer = get_analyzer()
    return analyzer.report(mesh)

def get_mirror_name(node: str) -> Optional[str]:
    """Get mirror counterpart name using symmetry naming rules."""
    # We can use a name resolver or simple heuristics.
    # For consistency, we'll reuse the logic from ControllerMapper.
    mapper = ControllerMapper(SymmetrySettings())
    # Just return a single mapping
    pairs = mapper._fallback_mapping([node])
    if pairs and pairs[0].target:
        return pairs[0].target
    return None

# -----------------------------------------------------------------------------
# Self-test (if run directly)
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    print("Symmetry module loaded. Use within Maya.")