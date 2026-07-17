"""
core/pipeline/rig_builder.py

High-level facial rig builder.

Coordinates the construction of every subsystem of the facial rig.
This module should not contain low-level rigging code. Instead, it
delegates work to specialized builders located in maya_faceit.rig.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..logging.logger import log
from ..undo.undo_manager import undo
from .facial_template import FacialTemplate
from ..validation.validation import ValidationResult

# Rig modules (future imports)
# from maya_faceit.rig.skeleton import SkeletonBuilder
# from maya_faceit.rig.controllers import ControllerBuilder
# from maya_faceit.rig.driver_network import DriverNetworkBuilder
# from maya_faceit.rig.constraints import ConstraintBuilder


# ----------------------------------------------------------
# Result
# ----------------------------------------------------------

@dataclass(slots=True)
class RigBuildResult:
    """Result of a rig build operation."""
    success: bool
    message: str
    created_nodes: List[str] = field(default_factory=list)


# ----------------------------------------------------------
# Rig Builder
# ----------------------------------------------------------

class RigBuilder:
    """
    Main facial rig construction engine.
    """

    def __init__(self):
        self.mesh: Optional[str] = None
        self.template: Optional[FacialTemplate] = None
        self.validation: Optional[ValidationResult] = None
        self.created_nodes: List[str] = []

    @undo.undoable("Build Facial Rig")
    def build(
        self,
        mesh: str,
        template: FacialTemplate,
        validation: Optional[ValidationResult] = None
    ) -> RigBuildResult:
        """
        Build a complete facial rig from a mesh and template.

        Args:
            mesh: The base mesh for the rig.
            template: FacialTemplate defining the rig structure.
            validation: Optional validation report to pass through.

        Returns:
            RigBuildResult indicating success/failure and created nodes.
        """
        self.mesh = mesh
        self.template = template
        self.validation = validation

        log.info("Building facial rig...")

        try:
            self._build_skeleton()
            self._build_controllers()
            self._build_regions()
            self._build_driver_network()
            self._build_constraints()
            self._finalize()

            log.info(f"Facial rig built successfully. Created {len(self.created_nodes)} nodes.")
            return RigBuildResult(
                success=True,
                message="Rig created successfully.",
                created_nodes=self.created_nodes
            )

        except Exception as exc:
            log.exception(exc)
            return RigBuildResult(
                success=False,
                message=str(exc)
            )

    def _build_skeleton(self) -> None:
        """Build the skeleton (joints)."""
        log.info("Building skeleton...")
        # Placeholder: SkeletonBuilder().build(self.template)
        # For now, simulate with dummy nodes.
        self.created_nodes.append("face_skeleton_grp")
        log.info("Skeleton built (placeholder).")

    def _build_controllers(self) -> None:
        """Build controllers for each region."""
        log.info("Building controllers...")
        # Placeholder: ControllerBuilder().build(self.template)
        self.created_nodes.append("controllers_grp")
        log.info("Controllers built (placeholder).")

    def _build_regions(self) -> None:
        """Build facial regions (eyes, jaw, lips, etc.)."""
        log.info("Building facial regions...")
        # Future: JawBuilder().build(...), EyeBuilder().build(...), etc.
        self.created_nodes.append("regions_grp")
        log.info("Regions built (placeholder).")

    def _build_driver_network(self) -> None:
        """Create the driver network (SDKs, constraints, etc.)."""
        log.info("Creating driver network...")
        # Placeholder: DriverNetworkBuilder().build()
        self.created_nodes.append("driver_network_grp")
        log.info("Driver network built (placeholder).")

    def _build_constraints(self) -> None:
        """Create constraints for the rig."""
        log.info("Creating constraints...")
        # Placeholder: ConstraintBuilder().build()
        self.created_nodes.append("constraints_grp")
        log.info("Constraints built (placeholder).")

    def _finalize(self) -> None:
        """Finalize the rig: organize hierarchy, lock channels, color, etc."""
        log.info("Finalizing rig...")
        # Future: organize hierarchy, create display layers, lock channels,
        # color controllers, create selection sets, save metadata.
        log.info("Rig finalized.")

    @property
    def node_count(self) -> int:
        return len(self.created_nodes)


# ----------------------------------------------------------
# Singleton
# ----------------------------------------------------------

rig_builder = RigBuilder()