# -*- coding: utf-8 -*-
"""
validation/validator.py

Generic scene and node validation.
"""

import maya.cmds as cmds # type: ignore
from typing import List, Optional, Dict, Any, Union
from enum import Enum, auto
from dataclasses import dataclass, field


# =============================================================================
# ISSUE SEVERITY
# =============================================================================

class IssueSeverity(Enum):
    """Severity of a validation issue."""
    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    CRITICAL = auto()


# =============================================================================
# VALIDATION RESULT
# =============================================================================

@dataclass
class ValidationResult:
    """Container for validation results."""
    valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    infos: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def add_error(self, message: str) -> None:
        self.errors.append(message)
        self.valid = False

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def add_info(self, message: str) -> None:
        self.infos.append(message)

    def merge(self, other: 'ValidationResult') -> None:
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.infos.extend(other.infos)
        self.details.update(other.details)
        if not other.valid:
            self.valid = False


# =============================================================================
# VALIDATOR
# =============================================================================

class Validator:
    """
    General scene/node validator.

    Provides methods for checking node existence, types, attributes,
    scene structure, and common Maya issues.
    """

    def __init__(self):
        self._results: List[ValidationResult] = []

    # =========================================================================
    # NODE VALIDATION
    # =========================================================================

    @staticmethod
    def node_exists(node: str) -> bool:
        """Check if a node exists."""
        return cmds.objExists(node)

    @staticmethod
    def is_type(node: str, node_type: Union[str, List[str]]) -> bool:
        """
        Check if a node is of a given type (or one of several types).

        Args:
            node: Node name.
            node_type: Single type string or list of type strings.

        Returns:
            True if node matches any of the types.
        """
        if not cmds.objExists(node):
            return False
        actual = cmds.nodeType(node)
        if isinstance(node_type, str):
            return actual == node_type
        return actual in node_type

    @staticmethod
    def has_attribute(node: str, attribute: str) -> bool:
        """Check if a node has a specific attribute."""
        return cmds.objExists(f"{node}.{attribute}")

    @staticmethod
    def is_locked(node: str) -> bool:
        """Check if a node is locked."""
        if not cmds.objExists(node):
            return True
        return cmds.lockNode(node, q=True, lock=True)[0]

    @staticmethod
    def is_referenced(node: str) -> bool:
        """Check if a node is referenced."""
        if not cmds.objExists(node):
            return False
        return cmds.referenceQuery(node, isNodeReferenced=True)

    @staticmethod
    def get_parent(node: str) -> Optional[str]:
        """Get the parent of a node."""
        if not cmds.objExists(node):
            return None
        parents = cmds.listRelatives(node, parent=True, fullPath=True)
        return parents[0] if parents else None

    # =========================================================================
    # SCENE VALIDATION
    # =========================================================================

    def validate_scene(self) -> ValidationResult:
        """
        Perform broad scene-level validation.

        Checks:
            - Unknown nodes
            - Non-manifold geometry
            - Empty groups
            - Unused materials
            - References
            - Locked nodes
            - Animation on locked nodes

        Returns:
            ValidationResult with all issues found.
        """
        result = ValidationResult()

        # 1. Unknown nodes
        unknown = cmds.ls(type='unknown')
        if unknown:
            result.add_warning(f"Found {len(unknown)} unknown nodes: {', '.join(unknown[:10])}")

        # 2. Non-manifold geometry
        all_meshes = cmds.ls(type='mesh')
        non_manifold_meshes = []
        for m in all_meshes:
            if cmds.polyInfo(m, nonManifoldEdges=True):
                non_manifold_meshes.append(m)
        if non_manifold_meshes:
            result.add_error(f"Non-manifold geometry found on: {', '.join(non_manifold_meshes[:5])}")

        # 3. Empty groups
        groups = cmds.ls(type='group')
        empty_groups = [g for g in groups if not cmds.listRelatives(g, children=True)]
        if empty_groups:
            result.add_warning(f"Found {len(empty_groups)} empty groups.")

        # 4. Unused materials
        all_shaders = cmds.ls(type='shadingEngine')
        unused = []
        for s in all_shaders:
            if s in ['initialShadingGroup', 'initialParticleSE']:
                continue
            if not cmds.sets(s, q=True) and not cmds.listConnections(s, type='material'):
                unused.append(s)
        if unused:
            result.add_info(f"Found {len(unused)} unused shading groups.")

        # 5. References
        refs = cmds.ls(type='reference')
        if refs:
            result.add_info(f"Scene contains {len(refs)} references.")

        # 6. Locked nodes with animation
        all_transforms = cmds.ls(type='transform')
        locked_animated = []
        for t in all_transforms:
            if self.is_locked(t):
                attrs = cmds.listAttr(t, keyable=True) or []
                for attr in attrs:
                    if cmds.keyframe(f"{t}.{attr}", q=True, keyframeCount=True):
                        locked_animated.append(t)
                        break
        if locked_animated:
            result.add_warning(f"Locked nodes with animation: {', '.join(locked_animated[:5])}")

        return result

    def validate_nodes(self, nodes: List[str]) -> ValidationResult:
        """
        Validate a list of nodes.

        Checks:
            - Existence
            - Type (optional)
            - Locked state
            - Referenced state

        Returns:
            ValidationResult for the nodes.
        """
        result = ValidationResult()
        for node in nodes:
            if not self.node_exists(node):
                result.add_error(f"Node '{node}' does not exist.")
                continue
            if self.is_locked(node):
                result.add_warning(f"Node '{node}' is locked.")
            if self.is_referenced(node):
                result.add_info(f"Node '{node}' is referenced.")
        return result

    def validate_meshes(self) -> ValidationResult:
        """Validate all meshes in the scene."""
        result = ValidationResult()
        meshes = cmds.ls(type='mesh')
        for m in meshes:
            # Check for history
            history = cmds.listHistory(m)
            if history and len(history) > 5:
                result.add_warning(f"Mesh '{m}' has {len(history)} history nodes.")

            # Check for vertex count
            vtx = cmds.polyEvaluate(m, vertex=True)
            if vtx > 100000:
                result.add_warning(f"Mesh '{m}' has {vtx} vertices (high).")

            # Check for duplicate vertices
            # We'll skip heavy checks for performance; can be added.
        return result