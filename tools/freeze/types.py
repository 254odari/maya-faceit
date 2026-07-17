# -*- coding: utf-8 -*-
"""
tools/freeze/types.py

Enums and dataclasses for the freeze toolkit.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple


# =============================================================================
# ENUMS
# =============================================================================

class FreezeType(Enum):
    """Type of freeze operation."""
    TRANSFORM = "transform"
    PIVOT = "pivot"
    CONTROLLER = "controller"
    RIG = "rig"
    MESH = "mesh"


class FreezeMode(Enum):
    """How aggressively to freeze."""
    SAFE = "safe"              # Preserve all dependencies, use offset groups
    STANDARD = "standard"      # Freeze if no critical dependencies
    FORCE = "force"            # Freeze even if dependencies exist (can break rig)


class FreezeScope(Enum):
    """Scope of freeze operation."""
    SELECTED = "selected"
    HIERARCHY = "hierarchy"
    SCENE = "scene"


class FreezeChannel(Enum):
    """Channels to freeze."""
    TRANSLATE = "translate"
    ROTATE = "rotate"
    SCALE = "scale"
    ALL = "all"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class FreezeResult:
    """Result of a single freeze operation."""
    success: bool = True
    node: str = ""
    operation: str = ""
    frozen_channels: List[str] = field(default_factory=list)
    offset_group_created: bool = False
    preserved_connections: int = 0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TransformFreeze:
    """Transform freeze results."""
    total_nodes: int = 0
    frozen_nodes: int = 0
    skipped_nodes: int = 0
    offset_groups: int = 0
    preserved_connections: int = 0
    frozen_translates: int = 0
    frozen_rotates: int = 0
    frozen_scales: int = 0


@dataclass
class PivotFreeze:
    """Pivot freeze results."""
    total_nodes: int = 0
    frozen_pivots: int = 0
    skipped_nodes: int = 0


@dataclass
class ControllerFreeze:
    """Controller freeze results."""
    total_controllers: int = 0
    frozen_controllers: int = 0
    skipped_controllers: int = 0
    offset_groups: int = 0


@dataclass
class RigFreeze:
    """Rig freeze results."""
    total_nodes: int = 0
    frozen_transforms: int = 0
    frozen_pivots: int = 0
    skipped_nodes: int = 0
    offset_groups: int = 0


@dataclass
class MeshFreeze:
    """Mesh freeze results."""
    total_meshes: int = 0
    frozen_meshes: int = 0
    skipped_meshes: int = 0


@dataclass
class FreezeReport:
    """Complete freeze report."""
    success: bool = True
    type: FreezeType = FreezeType.TRANSFORM
    mode: FreezeMode = FreezeMode.SAFE
    scope: FreezeScope = FreezeScope.SELECTED
    transform: TransformFreeze = field(default_factory=TransformFreeze)
    pivot: PivotFreeze = field(default_factory=PivotFreeze)
    controller: ControllerFreeze = field(default_factory=ControllerFreeze)
    rig: RigFreeze = field(default_factory=RigFreeze)
    mesh: MeshFreeze = field(default_factory=MeshFreeze)
    elapsed_time_ms: float = 0.0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        """Generate a human-readable summary."""
        lines = []
        lines.append("=" * 60)
        lines.append(f"Freeze Report - {self.type.value}")
        lines.append("=" * 60)
        lines.append(f"  Mode: {self.mode.value}")
        lines.append(f"  Scope: {self.scope.value}")
        lines.append(f"  Duration: {self.elapsed_time_ms:.2f}ms")
        lines.append("")
        lines.append("  Freezes Applied:")
        if self.transform.frozen_nodes:
            lines.append(f"    Transform: {self.transform.frozen_nodes} nodes frozen")
            if self.transform.offset_groups:
                lines.append(f"      Offset groups: {self.transform.offset_groups}")
        if self.pivot.frozen_pivots:
            lines.append(f"    Pivot: {self.pivot.frozen_pivots} pivots frozen")
        if self.controller.frozen_controllers:
            lines.append(f"    Controller: {self.controller.frozen_controllers} controllers frozen")
        if self.rig.frozen_transforms:
            lines.append(f"    Rig: {self.rig.frozen_transforms} transforms frozen")
        if self.mesh.frozen_meshes:
            lines.append(f"    Mesh: {self.mesh.frozen_meshes} meshes frozen")
        if self.warnings:
            lines.append("")
            lines.append("  Warnings:")
            for w in self.warnings[:5]:
                lines.append(f"    - {w}")
        if self.errors:
            lines.append("")
            lines.append("  Errors:")
            for e in self.errors[:5]:
                lines.append(f"    - {e}")
        lines.append("=" * 60)
        return "\n".join(lines)