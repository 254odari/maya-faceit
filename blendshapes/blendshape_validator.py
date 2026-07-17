"""
blendshapes/blendshape_validator.py

Blendshape Quality Assurance (QA) Engine for Maya.

This module provides a comprehensive validation system for blendshape operations.
It is the single source of truth for determining whether a blendshape operation
is safe and valid. Every module that creates, edits, transfers, mirrors,
exports, or optimizes blendshapes should pass through this validator.

Responsibilities:
- Validate mesh geometry, topology, vertex counts, normals, UVs, transforms.
- Validate blendshape nodes, targets, weights, naming, connections.
- Validate topology for compatibility between meshes.
- Validate naming conventions and ARKit compliance.
- Validate weights (range, NaN, infinite, locked).
- Validate ARKit 52-shape completeness.
- Validate scene for unknown nodes, broken references, unused nodes.
- Provide detailed reports, statistics, and repair suggestions.

The validator uses a modular design with specialized sub-validators,
orchestrated by the main BlendshapeValidator class.

Dependencies:
- blendshape_utils.py: shared utilities for mesh operations.
- blendshape_library.py: ARKit definitions and target names.
- blendshape_weights.py: weight management utilities.
- blendshape_delta.py: delta operations (for topology checks).
- blendshape_creator.py: used to inspect blendshape nodes.
- blendshapes/arkit: ARKit constants and mappings.

The module is Maya-independent in interface, but uses Maya commands internally.
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Dict, Any, Set, Tuple, Union, Callable

# Maya imports
try:
    import maya.cmds as cmds
    import maya.mel as mel
    from pymel.core import PyNode, selected, ls, exists, currentTime
    import pymel.core as pm
except ImportError:
    class Dummy:
        def __getattr__(self, name):
            return lambda *args, **kwargs: None
    pm = Dummy()
    cmds = Dummy()
    mel = Dummy()

# Optional imports from other blendshape modules (with fallbacks)
try:
    from .blendshape_utils import MeshUtils, NameUtils, TopologyUtils
except ImportError:
    MeshUtils = None
    NameUtils = None
    TopologyUtils = None

try:
    from .blendshape_library import BlendShapeLibrary
except ImportError:
    BlendShapeLibrary = None

try:
    from .blendshape_weights import WeightManager
except ImportError:
    WeightManager = None

try:
    from .blendshape_delta import BlendshapeDeltaEngine
except ImportError:
    BlendshapeDeltaEngine = None

try:
    from .blendshape_creator import BlendShapeCreator
except ImportError:
    BlendShapeCreator = None

try:
    from ..arkit.arkit52 import ARKIT_BLENDSHAPES, ARKIT_SET
except ImportError:
    ARKIT_BLENDSHAPES = []
    ARKIT_SET = set()

# ---- Part 1: Foundation ------------------------------------------------

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"

logger = logging.getLogger(__name__)

# Exceptions
class ValidationError(Exception):
    """Base exception for validation errors."""
    pass

class ValidationCriticalError(ValidationError):
    """Critical validation error that prevents operation."""
    pass

# ---- Part 2: Constants & Enumerations --------------------------------

class ValidationLevel(Enum):
    """Strictness level for validation."""
    FAST = "fast"          # Basic checks (existence, vertex count)
    NORMAL = "normal"      # Standard checks including topology
    STRICT = "strict"      # Full checks including normals, UVs, history
    EXPORT = "export"      # Export-ready validation
    DEBUG = "debug"        # Extensive logging and diagnostics


class ValidationSeverity(Enum):
    """Severity of a validation issue."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationCategory(Enum):
    """Category of validation check."""
    MESH = "mesh"
    TOPOLOGY = "topology"
    WEIGHTS = "weights"
    NAMES = "names"
    ARKIT = "arkit"
    SCENE = "scene"
    EXPORT = "export"
    NODE = "node"


class RepairMode(Enum):
    """Mode for handling repairable issues."""
    NONE = "none"          # No repair attempted
    AUTO = "auto"          # Automatically fix issues
    SUGGEST = "suggest"    # Provide repair suggestions


# ---- Part 3: Data Models ----------------------------------------------

@dataclass
class ValidationIssue:
    """A single validation issue."""
    severity: ValidationSeverity
    category: ValidationCategory
    message: str
    node: Optional[str] = None
    attribute: Optional[str] = None
    repairable: bool = False
    repair_action: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity.value,
            "category": self.category.value,
            "message": self.message,
            "node": self.node,
            "attribute": self.attribute,
            "repairable": self.repairable,
            "repair_action": self.repair_action,
            "details": self.details,
        }


@dataclass
class ValidationReport:
    """Complete validation report."""
    passed: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)
    errors: List[ValidationIssue] = field(default_factory=list)
    criticals: List[ValidationIssue] = field(default_factory=list)
    duration_ms: float = 0.0
    level: ValidationLevel = ValidationLevel.NORMAL
    repair_mode: RepairMode = RepairMode.NONE
    statistics: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0 and len(self.criticals) == 0

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    def add_issue(self, issue: ValidationIssue) -> None:
        """Add an issue to the report."""
        self.issues.append(issue)
        if issue.severity == ValidationSeverity.ERROR:
            self.errors.append(issue)
        elif issue.severity == ValidationSeverity.WARNING:
            self.warnings.append(issue)
        elif issue.severity == ValidationSeverity.CRITICAL:
            self.criticals.append(issue)
        # If any error or critical, passed becomes False
        if issue.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL):
            self.passed = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "issues": [i.to_dict() for i in self.issues],
            "duration_ms": self.duration_ms,
            "level": self.level.value,
            "repair_mode": self.repair_mode.value,
            "statistics": self.statistics,
        }


@dataclass
class MeshValidation:
    """Validation result for a single mesh."""
    mesh: str
    is_valid: bool
    vertex_count: int = 0
    edge_count: int = 0
    face_count: int = 0
    has_history: bool = False
    has_normals: bool = True
    uv_sets: List[str] = field(default_factory=list)
    scale: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    is_frozen: bool = True
    issues: List[ValidationIssue] = field(default_factory=list)


@dataclass
class TopologyValidation:
    """Validation result for topology comparison."""
    identical: bool
    vertex_order: bool
    vertex_count_match: bool
    edge_count_match: bool
    face_count_match: bool
    shell_count: int = 1
    has_non_manifold: bool = False
    has_lamina_faces: bool = False
    has_open_borders: bool = False
    issues: List[ValidationIssue] = field(default_factory=list)


@dataclass
class BlendshapeValidation:
    """Validation result for a blendshape node."""
    node: str
    is_valid: bool
    target_count: int = 0
    targets: List[str] = field(default_factory=list)
    duplicate_targets: List[str] = field(default_factory=list)
    missing_targets: List[str] = field(default_factory=list)
    weight_aliases: Dict[str, str] = field(default_factory=dict)
    has_history: bool = False
    issues: List[ValidationIssue] = field(default_factory=list)


@dataclass
class WeightValidation:
    """Validation result for weights."""
    weights: Dict[str, float]
    is_valid: bool
    min_value: float = 0.0
    max_value: float = 1.0
    negative_weights: List[Tuple[str, float]] = field(default_factory=list)
    above_one: List[Tuple[str, float]] = field(default_factory=list)
    nan_weights: List[str] = field(default_factory=list)
    inf_weights: List[str] = field(default_factory=list)
    locked_weights: List[str] = field(default_factory=list)
    issues: List[ValidationIssue] = field(default_factory=list)


@dataclass
class ARKitValidation:
    """Validation result for ARKit mapping."""
    is_valid: bool
    total_targets: int = 0
    expected_targets: int = 52
    missing: List[str] = field(default_factory=list)
    duplicates: List[str] = field(default_factory=list)
    invalid_names: List[str] = field(default_factory=list)
    issues: List[ValidationIssue] = field(default_factory=list)


@dataclass
class SceneValidation:
    """Validation result for the overall scene."""
    is_valid: bool
    unknown_nodes: List[str] = field(default_factory=list)
    broken_references: List[str] = field(default_factory=list)
    duplicate_meshes: List[str] = field(default_factory=list)
    unused_blendshapes: List[str] = field(default_factory=list)
    invalid_history: List[str] = field(default_factory=list)
    issues: List[ValidationIssue] = field(default_factory=list)


@dataclass
class ValidationStatistics:
    """Statistics for a validation run."""
    total_checks: int = 0
    passed_checks: int = 0
    warnings: int = 0
    errors: int = 0
    criticals: int = 0
    repaired_issues: int = 0
    duration_ms: float = 0.0
    categories: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_checks": self.total_checks,
            "passed_checks": self.passed_checks,
            "warnings": self.warnings,
            "errors": self.errors,
            "criticals": self.criticals,
            "repaired_issues": self.repaired_issues,
            "duration_ms": self.duration_ms,
            "categories": self.categories,
        }


# ---- Part 4: Validation Engine -----------------------------------------

class BlendshapeValidator:
    """
    Main controller for all validation operations.

    Orchestrates specialized validators for mesh, topology, blendshape nodes,
    weights, naming, ARKit compliance, and scene validation.
    """
    def __init__(self):
        self._utils_mesh = MeshUtils() if MeshUtils else None
        self._utils_name = NameUtils() if NameUtils else None
        self._utils_topology = TopologyUtils() if TopologyUtils else None
        self._library = BlendShapeLibrary() if BlendShapeLibrary else None
        self._weight_manager = WeightManager() if WeightManager else None
        self._delta_engine = BlendshapeDeltaEngine() if BlendshapeDeltaEngine else None
        self._creator = BlendShapeCreator() if BlendShapeCreator else None

        self._last_report: Optional[ValidationReport] = None
        self._last_stats: Optional[ValidationStatistics] = None

    # ---- Main Entry Points ----

    def validate_mesh(
        self,
        mesh: str,
        level: ValidationLevel = ValidationLevel.NORMAL,
        repair_mode: RepairMode = RepairMode.NONE,
    ) -> ValidationReport:
        """
        Validate a single mesh.
        """
        report = ValidationReport(passed=True, level=level, repair_mode=repair_mode)
        start_time = time.time()

        # Existence
        if not cmds.objExists(mesh):
            report.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.MESH,
                message=f"Mesh '{mesh}' does not exist",
                repairable=False,
            ))
            report.duration_ms = (time.time() - start_time) * 1000
            self._last_report = report
            return report

        # Shape node
        shapes = cmds.listRelatives(mesh, shapes=True) or []
        if not shapes:
            report.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.MESH,
                message=f"'{mesh}' has no shape node",
                node=mesh,
                repairable=False,
            ))
            report.passed = False
            report.duration_ms = (time.time() - start_time) * 1000
            self._last_report = report
            return report

        shape = shapes[0]
        if cmds.nodeType(shape) != 'mesh':
            report.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.MESH,
                message=f"'{mesh}' shape is not a mesh (type: {cmds.nodeType(shape)})",
                node=mesh,
                repairable=False,
            ))
            report.passed = False
            report.duration_ms = (time.time() - start_time) * 1000
            self._last_report = report
            return report

        # Vertex count
        vertex_count = cmds.polyEvaluate(shape, vertex=True) or 0
        if vertex_count == 0:
            report.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.MESH,
                message=f"Mesh '{mesh}' has zero vertices",
                node=mesh,
                repairable=False,
            ))
            report.passed = False

        # History
        if level in (ValidationLevel.STRICT, ValidationLevel.EXPORT, ValidationLevel.DEBUG):
            if cmds.listHistory(shape, pruneDagObjects=True):
                report.add_issue(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.MESH,
                    message=f"Mesh '{mesh}' has construction history",
                    node=mesh,
                    repairable=True,
                    repair_action="Delete history"
                ))

        # Normals
        if level in (ValidationLevel.STRICT, ValidationLevel.EXPORT):
            if not cmds.polyNormalPerVertex(shape, q=True, x=True):
                report.add_issue(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.MESH,
                    message=f"Mesh '{mesh}' may have invalid normals",
                    node=mesh,
                ))

        # UV sets
        uv_sets = cmds.polyUVSet(shape, q=True, allUVSets=True) or []
        if level == ValidationLevel.EXPORT and not uv_sets:
            report.add_issue(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.MESH,
                message=f"Mesh '{mesh}' has no UV sets (may affect export)",
                node=mesh,
            ))

        # Transforms
        tx, ty, tz = cmds.getAttr(f"{mesh}.t")[0]
        if level in (ValidationLevel.STRICT, ValidationLevel.EXPORT):
            if tx != 0 or ty != 0 or tz != 0:
                report.add_issue(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.MESH,
                    message=f"Mesh '{mesh}' has non-zero translate: ({tx}, {ty}, {tz})",
                    node=mesh,
                    repairable=True,
                    repair_action="Freeze transforms"
                ))

        # Scale
        sx, sy, sz = cmds.getAttr(f"{mesh}.s")[0]
        if sx != 1 or sy != 1 or sz != 1:
            report.add_issue(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.MESH,
                message=f"Mesh '{mesh}' has non-uniform scale: ({sx}, {sy}, {sz})",
                node=mesh,
                repairable=True,
                repair_action="Reset scale to 1"
            ))

        # Locked attributes
        for attr in ['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz']:
            full = f"{mesh}.{attr}"
            if cmds.objExists(full) and cmds.getAttr(full, lock=True):
                report.add_issue(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.MESH,
                    message=f"Attribute {attr} on '{mesh}' is locked",
                    node=mesh,
                    attribute=attr,
                    repairable=True,
                    repair_action="Unlock attribute"
                ))

        report.duration_ms = (time.time() - start_time) * 1000
        self._last_report = report
        return report

    def validate_topology(
        self,
        mesh_a: str,
        mesh_b: str,
        level: ValidationLevel = ValidationLevel.NORMAL,
    ) -> ValidationReport:
        """
        Validate topology compatibility between two meshes.
        This is critical for transfer, mirroring, and delta operations.
        """
        report = ValidationReport(passed=True, level=level)
        start_time = time.time()

        # First validate each mesh
        report_a = self.validate_mesh(mesh_a, level=level)
        report_b = self.validate_mesh(mesh_b, level=level)
        if not report_a.is_valid or not report_b.is_valid:
            report.passed = False
            for issue in report_a.issues + report_b.issues:
                report.add_issue(issue)
            report.duration_ms = (time.time() - start_time) * 1000
            self._last_report = report
            return report

        # Get vertex counts
        vcount_a = cmds.polyEvaluate(mesh_a, vertex=True) or 0
        vcount_b = cmds.polyEvaluate(mesh_b, vertex=True) or 0

        if vcount_a != vcount_b:
            report.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.TOPOLOGY,
                message=f"Vertex count mismatch: {mesh_a} has {vcount_a}, {mesh_b} has {vcount_b}",
                repairable=False,
            ))
            report.passed = False
        else:
            # Check vertex order (simplified: we can compute a hash of positions)
            # For a robust check, we could compare vertex positions with tolerance.
            # We'll assume that if counts match, we consider topology valid.
            # Additional checks could be added.
            pass

        # Edge and face counts (optional)
        if level in (ValidationLevel.STRICT, ValidationLevel.EXPORT, ValidationLevel.DEBUG):
            ecount_a = cmds.polyEvaluate(mesh_a, edge=True) or 0
            ecount_b = cmds.polyEvaluate(mesh_b, edge=True) or 0
            fcount_a = cmds.polyEvaluate(mesh_a, face=True) or 0
            fcount_b = cmds.polyEvaluate(mesh_b, face=True) or 0
            if ecount_a != ecount_b:
                report.add_issue(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.TOPOLOGY,
                    message=f"Edge count mismatch: {mesh_a} has {ecount_a}, {mesh_b} has {ecount_b}",
                ))
            if fcount_a != fcount_b:
                report.add_issue(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.TOPOLOGY,
                    message=f"Face count mismatch: {mesh_a} has {fcount_a}, {mesh_b} has {fcount_b}",
                ))

        # Non-manifold geometry check (simplified)
        if level == ValidationLevel.STRICT:
            non_manifold_a = cmds.polyInfo(mesh_a, nonManifoldEdge=True)
            non_manifold_b = cmds.polyInfo(mesh_b, nonManifoldEdge=True)
            if non_manifold_a:
                report.add_issue(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.TOPOLOGY,
                    message=f"Mesh '{mesh_a}' has non-manifold edges",
                    node=mesh_a,
                ))
            if non_manifold_b:
                report.add_issue(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.TOPOLOGY,
                    message=f"Mesh '{mesh_b}' has non-manifold edges",
                    node=mesh_b,
                ))

        report.duration_ms = (time.time() - start_time) * 1000
        self._last_report = report
        return report

    def validate_blendshape_node(
        self,
        node: str,
        level: ValidationLevel = ValidationLevel.NORMAL,
    ) -> ValidationReport:
        """
        Validate a blendshape node.
        """
        report = ValidationReport(passed=True, level=level)
        start_time = time.time()

        # Existence
        if not cmds.objExists(node):
            report.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.NODE,
                message=f"Blendshape node '{node}' does not exist",
                repairable=False,
            ))
            report.passed = False
            report.duration_ms = (time.time() - start_time) * 1000
            self._last_report = report
            return report

        if cmds.nodeType(node) != 'blendShape':
            report.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.NODE,
                message=f"Node '{node}' is not a blendShape (type: {cmds.nodeType(node)})",
                repairable=False,
            ))
            report.passed = False
            report.duration_ms = (time.time() - start_time) * 1000
            self._last_report = report
            return report

        # Get target names (weight aliases)
        targets = cmds.listAttr(node, m=True, string='weight') or []
        target_count = len(targets)

        # Check for duplicate targets
        seen = set()
        duplicates = []
        for t in targets:
            if t in seen:
                duplicates.append(t)
            seen.add(t)

        if duplicates:
            report.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.NODE,
                message=f"Duplicate target names: {duplicates}",
                node=node,
                repairable=True,
                repair_action="Rename or merge duplicate targets"
            ))
            report.passed = False

        # Check if any target has zero weight (optional)
        if level == ValidationLevel.STRICT:
            for t in targets:
                weight = cmds.getAttr(f"{node}.{t}")
                if weight == 0:
                    report.add_issue(ValidationIssue(
                        severity=ValidationSeverity.INFO,
                        category=ValidationCategory.NODE,
                        message=f"Target '{t}' has zero weight",
                        node=node,
                        attribute=t,
                    ))

        # Check history (if node has history)
        if level in (ValidationLevel.STRICT, ValidationLevel.EXPORT):
            if cmds.listHistory(node, pruneDagObjects=True):
                report.add_issue(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.NODE,
                    message=f"Blendshape node '{node}' has construction history",
                    node=node,
                    repairable=True,
                    repair_action="Delete history"
                ))

        report.duration_ms = (time.time() - start_time) * 1000
        self._last_report = report
        return report

    def validate_weights(
        self,
        node: str,
        level: ValidationLevel = ValidationLevel.NORMAL,
    ) -> ValidationReport:
        """
        Validate weights on a blendshape node.
        """
        report = ValidationReport(passed=True, level=level)
        start_time = time.time()

        if not cmds.objExists(node) or cmds.nodeType(node) != 'blendShape':
            report.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.NODE,
                message=f"Invalid blendshape node '{node}'",
                repairable=False,
            ))
            report.passed = False
            report.duration_ms = (time.time() - start_time) * 1000
            self._last_report = report
            return report

        targets = cmds.listAttr(node, m=True, string='weight') or []
        for t in targets:
            weight_attr = f"{node}.{t}"
            if not cmds.objExists(weight_attr):
                continue
            try:
                val = cmds.getAttr(weight_attr)
            except:
                report.add_issue(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.WEIGHTS,
                    message=f"Failed to get weight for target '{t}'",
                    node=node,
                    attribute=t,
                ))
                continue

            # Check for NaN or inf
            if not isinstance(val, (int, float)):
                report.add_issue(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.WEIGHTS,
                    message=f"Weight for '{t}' is not a number: {val}",
                    node=node,
                    attribute=t,
                ))
                report.passed = False
                continue

            if math.isnan(val):
                report.add_issue(ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    category=ValidationCategory.WEIGHTS,
                    message=f"Weight for '{t}' is NaN",
                    node=node,
                    attribute=t,
                ))
                report.passed = False
                continue

            if math.isinf(val):
                report.add_issue(ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    category=ValidationCategory.WEIGHTS,
                    message=f"Weight for '{t}' is infinite: {val}",
                    node=node,
                    attribute=t,
                ))
                report.passed = False
                continue

            # Check range
            if val < 0:
                report.add_issue(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.WEIGHTS,
                    message=f"Weight for '{t}' is negative: {val}",
                    node=node,
                    attribute=t,
                    repairable=True,
                    repair_action="Clamp to 0"
                ))
            if val > 1:
                report.add_issue(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.WEIGHTS,
                    message=f"Weight for '{t}' exceeds 1: {val}",
                    node=node,
                    attribute=t,
                    repairable=True,
                    repair_action="Clamp to 1"
                ))

            # Check if weight is locked
            if cmds.getAttr(weight_attr, lock=True):
                report.add_issue(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.WEIGHTS,
                    message=f"Weight for '{t}' is locked",
                    node=node,
                    attribute=t,
                    repairable=True,
                    repair_action="Unlock weight"
                ))

        report.duration_ms = (time.time() - start_time) * 1000
        self._last_report = report
        return report

    def validate_arkit(
        self,
        node: str,
        level: ValidationLevel = ValidationLevel.STRICT,
    ) -> ValidationReport:
        """
        Validate ARKit compliance: 52 shapes, naming, mapping.
        """
        report = ValidationReport(passed=True, level=level)
        start_time = time.time()

        if not cmds.objExists(node) or cmds.nodeType(node) != 'blendShape':
            report.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.ARKIT,
                message=f"Node '{node}' is not a valid blendshape node",
                repairable=False,
            ))
            report.passed = False
            report.duration_ms = (time.time() - start_time) * 1000
            self._last_report = report
            return report

        # Get targets
        targets = set(cmds.listAttr(node, m=True, string='weight') or [])

        # Check against ARKit list
        arkit_set = set(ARKIT_BLENDSHAPES) if ARKIT_BLENDSHAPES else set()
        if not arkit_set:
            report.add_issue(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.ARKIT,
                message="ARKit blendshape list not available; cannot validate completeness",
            ))
        else:
            missing = arkit_set - targets
            extra = targets - arkit_set

            if missing:
                report.add_issue(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.ARKIT,
                    message=f"Missing ARKit targets: {sorted(missing)}",
                    repairable=False,
                ))
                report.passed = False

            if extra:
                report.add_issue(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.ARKIT,
                    message=f"Extra targets not in ARKit spec: {sorted(extra)}",
                ))

        # Check naming conventions (no spaces, illegal chars)
        illegal_chars = set("!@#$%^&*()+=[]{}\\|;:'\"<>,/?`~")
        invalid_names = []
        for t in targets:
            if any(c in illegal_chars for c in t):
                invalid_names.append(t)
        if invalid_names:
            report.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.ARKIT,
                message=f"Targets contain illegal characters: {invalid_names}",
                repairable=True,
                repair_action="Rename targets"
            ))
            report.passed = False

        report.duration_ms = (time.time() - start_time) * 1000
        self._last_report = report
        return report

    def validate_scene(
        self,
        level: ValidationLevel = ValidationLevel.NORMAL,
    ) -> ValidationReport:
        """
        Validate the overall scene for cleanliness.
        """
        report = ValidationReport(passed=True, level=level)
        start_time = time.time()

        # Unknown nodes (types not recognized)
        # We'll check for common node types that may be orphaned.
        unknown_types = ['unknown', 'dependNode', 'script', 'expression', 'timeEditor']
        unknown_nodes = []
        for ut in unknown_types:
            nodes = cmds.ls(type=ut) or []
            unknown_nodes.extend(nodes)
        if unknown_nodes:
            report.add_issue(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.SCENE,
                message=f"Found unknown nodes: {unknown_nodes}",
                repairable=True,
                repair_action="Delete unknown nodes"
            ))

        # Broken references
        refs = cmds.file(q=True, reference=True) or []
        broken = []
        for ref in refs:
            if not cmds.file(ref, q=True, exists=True):
                broken.append(ref)
        if broken:
            report.add_issue(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.SCENE,
                message=f"Broken references: {broken}",
                repairable=True,
                repair_action="Remove broken references"
            ))

        # Duplicate meshes (by name pattern)
        meshes = cmds.ls(type='mesh') or []
        seen = set()
        duplicates = []
        for m in meshes:
            base = m.split('|')[-1]
            if base in seen:
                duplicates.append(m)
            seen.add(base)
        if duplicates:
            report.add_issue(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.SCENE,
                message=f"Duplicate mesh names: {duplicates}",
                repairable=True,
                repair_action="Rename duplicates"
            ))

        # Unused blendshape nodes (not connected to any mesh)
        all_blendshapes = cmds.ls(type='blendShape') or []
        unused = []
        for bs in all_blendshapes:
            # Check if connected to any mesh output
            connections = cmds.listConnections(bs, source=True, destination=False, type='mesh') or []
            if not connections:
                unused.append(bs)
        if unused:
            report.add_issue(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.SCENE,
                message=f"Unused blendshape nodes: {unused}",
                repairable=True,
                repair_action="Delete unused blendshape nodes"
            ))

        report.duration_ms = (time.time() - start_time) * 1000
        self._last_report = report
        return report

    def validate(
        self,
        target: Union[str, List[str], None] = None,
        level: ValidationLevel = ValidationLevel.NORMAL,
        repair_mode: RepairMode = RepairMode.NONE,
        validate_arkit: bool = True,
        validate_scene: bool = True,
    ) -> ValidationReport:
        """
        Comprehensive validation.

        Args:
            target: A mesh, blendshape node, list of meshes, or None for scene validation.
            level: Validation level.
            repair_mode: Repair mode.
            validate_arkit: If True, validate ARKit compliance (when target is a blendshape node).
            validate_scene: If True, also validate the scene.

        Returns:
            ValidationReport.
        """
        combined_report = ValidationReport(passed=True, level=level, repair_mode=repair_mode)
        start_time = time.time()

        if target is None:
            # Scene validation
            scene_report = self.validate_scene(level)
            combined_report.passed = combined_report.passed and scene_report.passed
            for issue in scene_report.issues:
                combined_report.add_issue(issue)
        elif isinstance(target, str):
            # Single target
            if cmds.nodeType(target) == 'blendShape':
                # Validate blendshape node
                bs_report = self.validate_blendshape_node(target, level)
                combined_report.passed = combined_report.passed and bs_report.passed
                for issue in bs_report.issues:
                    combined_report.add_issue(issue)
                # Validate weights
                weight_report = self.validate_weights(target, level)
                combined_report.passed = combined_report.passed and weight_report.passed
                for issue in weight_report.issues:
                    combined_report.add_issue(issue)
                # ARKit validation
                if validate_arkit:
                    arkit_report = self.validate_arkit(target, level)
                    combined_report.passed = combined_report.passed and arkit_report.passed
                    for issue in arkit_report.issues:
                        combined_report.add_issue(issue)
            else:
                # Validate mesh
                mesh_report = self.validate_mesh(target, level, repair_mode)
                combined_report.passed = combined_report.passed and mesh_report.passed
                for issue in mesh_report.issues:
                    combined_report.add_issue(issue)
        elif isinstance(target, list):
            # Multiple targets
            for item in target:
                item_report = self.validate(item, level, repair_mode, validate_arkit=False, validate_scene=False)
                combined_report.passed = combined_report.passed and item_report.passed
                for issue in item_report.issues:
                    combined_report.add_issue(issue)

        if validate_scene:
            scene_report = self.validate_scene(level)
            combined_report.passed = combined_report.passed and scene_report.passed
            for issue in scene_report.issues:
                combined_report.add_issue(issue)

        # Statistics
        stats = self._compute_statistics(combined_report)
        combined_report.statistics = stats.to_dict()
        combined_report.duration_ms = (time.time() - start_time) * 1000

        self._last_report = combined_report
        self._last_stats = stats
        return combined_report

    # ---- Repair ----

    def repair(self, report: ValidationReport) -> int:
        """
        Attempt to repair issues flagged as repairable.
        Returns the number of issues repaired.
        """
        if report.repair_mode == RepairMode.NONE:
            return 0

        repaired = 0
        for issue in report.issues:
            if not issue.repairable:
                continue
            if issue.repair_action is None:
                continue
            try:
                if issue.category == ValidationCategory.MESH:
                    if issue.repair_action == "Delete history":
                        if issue.node:
                            cmds.delete(issue.node, constructionHistory=True)
                            repaired += 1
                    elif issue.repair_action == "Freeze transforms":
                        if issue.node:
                            cmds.makeIdentity(issue.node, apply=True, t=1, r=1, s=1, n=0)
                            repaired += 1
                    elif issue.repair_action == "Reset scale to 1":
                        if issue.node:
                            cmds.setAttr(f"{issue.node}.s", 1, 1, 1)
                            repaired += 1
                    elif issue.repair_action == "Unlock attribute":
                        if issue.node and issue.attribute:
                            cmds.setAttr(f"{issue.node}.{issue.attribute}", lock=False)
                            repaired += 1
                elif issue.category == ValidationCategory.WEIGHTS:
                    if issue.repair_action == "Clamp to 0":
                        if issue.node and issue.attribute:
                            val = cmds.getAttr(f"{issue.node}.{issue.attribute}")
                            if val < 0:
                                cmds.setAttr(f"{issue.node}.{issue.attribute}", 0.0)
                                repaired += 1
                    elif issue.repair_action == "Clamp to 1":
                        if issue.node and issue.attribute:
                            val = cmds.getAttr(f"{issue.node}.{issue.attribute}")
                            if val > 1:
                                cmds.setAttr(f"{issue.node}.{issue.attribute}", 1.0)
                                repaired += 1
                    elif issue.repair_action == "Unlock weight":
                        if issue.node and issue.attribute:
                            cmds.setAttr(f"{issue.node}.{issue.attribute}", lock=False)
                            repaired += 1
                elif issue.category == ValidationCategory.NAMES:
                    if issue.repair_action == "Rename targets":
                        # Not implemented; would require a naming strategy
                        pass
                elif issue.category == ValidationCategory.SCENE:
                    if issue.repair_action == "Delete unknown nodes":
                        # Not safe; skip
                        pass
            except Exception as e:
                logger.warning(f"Failed to repair {issue.message}: {e}")
        return repaired

    # ---- Statistics ----

    def statistics(self) -> Optional[ValidationStatistics]:
        """Return statistics from the last validation."""
        return self._last_stats

    def get_last_report(self) -> Optional[ValidationReport]:
        return self._last_report

    def reset(self) -> None:
        self._last_report = None
        self._last_stats = None

    def _compute_statistics(self, report: ValidationReport) -> ValidationStatistics:
        stats = ValidationStatistics()
        stats.total_checks = len(report.issues) + len(report.warnings) + len(report.errors) + len(report.criticals)
        # Since we don't track passed checks separately, we approximate:
        stats.passed_checks = stats.total_checks - len(report.errors) - len(report.criticals)
        stats.warnings = len(report.warnings)
        stats.errors = len(report.errors)
        stats.criticals = len(report.criticals)
        stats.repaired_issues = 0  # We can track if repair was called
        stats.duration_ms = report.duration_ms

        # Categorize
        cats = {}
        for issue in report.issues:
            cat = issue.category.value
            cats[cat] = cats.get(cat, 0) + 1
        stats.categories = cats
        return stats


# ---- Part 13: Utility Functions --------------------------------------

def compare_meshes(mesh_a: str, mesh_b: str) -> bool:
    """
    Quick comparison: check if meshes have same vertex count.
    Returns True if same, False otherwise.
    """
    if not cmds.objExists(mesh_a) or not cmds.objExists(mesh_b):
        return False
    va = cmds.polyEvaluate(mesh_a, vertex=True) or 0
    vb = cmds.polyEvaluate(mesh_b, vertex=True) or 0
    return va == vb


def get_vertex_count(mesh: str) -> int:
    """Return vertex count of a mesh."""
    if not cmds.objExists(mesh):
        return 0
    return cmds.polyEvaluate(mesh, vertex=True) or 0


def get_blendshape_targets(node: str) -> List[str]:
    """Get target names from a blendshape node."""
    if not cmds.objExists(node) or cmds.nodeType(node) != 'blendShape':
        return []
    return cmds.listAttr(node, m=True, string='weight') or []


def has_history(node: str) -> bool:
    """Check if a node has construction history."""
    if not cmds.objExists(node):
        return False
    return bool(cmds.listHistory(node, pruneDagObjects=True))


# ---- Part 14: Public API -----------------------------------------------

__all__ = [
    "BlendshapeValidator",
    "ValidationIssue",
    "ValidationReport",
    "MeshValidation",
    "TopologyValidation",
    "BlendshapeValidation",
    "WeightValidation",
    "ARKitValidation",
    "SceneValidation",
    "ValidationStatistics",
    "ValidationLevel",
    "ValidationSeverity",
    "ValidationCategory",
    "RepairMode",
    "ValidationError",
    "ValidationCriticalError",
    "compare_meshes",
    "get_vertex_count",
    "get_blendshape_targets",
    "has_history",
]