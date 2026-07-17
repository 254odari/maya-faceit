"""
core/pipeline/rig_pipeline.py

Main automatic rig generation pipeline.

Coordinates every subsystem required to build
a complete facial rig.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional
from ..logging.logger import log
from ..undo.undo_manager import undo
from ..mesh_analyzer import mesh_analyzer
from ..validation.topology_validator import topology_validator
from .landmark_solver import landmark_solver
from .facial_template import facial_template
from .rig_builder import rig_builder, RigBuildResult

# Future imports
# from maya_faceit.landmark.detector import detector
# from maya_faceit.blendshapes.manager import BlendshapeManager
# from maya_faceit.arkit.pose_generator import PoseGenerator
# from maya_faceit.expressions.generator import ExpressionGenerator


# ---------------------------------------------------------
# Pipeline Result
# ---------------------------------------------------------

@dataclass(slots=True)
class PipelineResult:
    """Result of the full pipeline run."""
    success: bool
    message: str
    rig_result: Optional[object] = None  # RigBuildResult


# ---------------------------------------------------------
# Pipeline
# ---------------------------------------------------------

class RigPipeline:
    """
    Controls the entire automatic rig generation process.
    """

    def __init__(self):
        self.mesh = None
        self.mesh_info = None
        self.validation = None
        self.landmarks = None
        self.template = facial_template

    @undo.undoable("Generate Face Rig")
    def build(self, mesh: str) -> PipelineResult:
        """
        Run the full rig generation pipeline on a given mesh.

        Args:
            mesh: The base mesh transform name.

        Returns:
            PipelineResult with success status and any errors.
        """
        self.mesh = mesh

        try:
            self._analyze_mesh()
            self._validate_topology()
            self._detect_landmarks()
            self._solve_landmarks()
            self._load_template()
            rig_result = self._build_rig()
            self._build_blendshapes()
            self._build_arkit()
            self._build_picker()
            self._save_project()

            log.info("Rig generation completed successfully.")
            return PipelineResult(
                success=True,
                message="Rig generation completed.",
                rig_result=rig_result
            )

        except Exception as e:
            log.exception(e)
            return PipelineResult(
                success=False,
                message=str(e)
            )

    def _analyze_mesh(self) -> None:
        """Analyze the mesh to gather stats."""
        log.info("Analyzing mesh...")
        self.mesh_info = mesh_analyzer.analyze(self.mesh)
        log.debug(f"Mesh info: {self.mesh_info}")

    def _validate_topology(self) -> None:
        """Validate mesh topology for rigging."""
        log.info("Validating topology...")
        self.validation = topology_validator.require_valid(self.mesh)
        log.debug(f"Topology validation passed with {len(self.validation.warnings)} warnings.")

    def _detect_landmarks(self) -> None:
        """Detect facial landmarks on the mesh."""
        log.info("Detecting landmarks...")
        # Future: self.landmarks = detector.detect(self.mesh)
        # For now, create dummy landmarks.
        self.landmarks = []
        log.debug("Landmarks detected (placeholder).")

    def _solve_landmarks(self) -> None:
        """Solve landmark positions into normalized coordinates."""
        log.info("Solving landmarks...")
        if self.landmarks:
            solved = landmark_solver.solve(self.landmarks)
            log.debug(f"Solved {len(solved.landmarks)} landmarks.")
        else:
            log.warning("No landmarks to solve; continuing with defaults.")

    def _load_template(self) -> None:
        """Load the facial template."""
        log.info("Loading facial template...")
        self.template = facial_template
        log.debug(f"Template loaded with {self.template.controller_count()} controllers.")

    def _build_rig(self) -> Optional[RigBuildResult]:
        """Build the facial rig using the template."""
        log.info("Building facial rig...")
        result = rig_builder.build(
            mesh=self.mesh,
            template=self.template,
            validation=self.validation
        )
        if result.success:
            log.info(f"Rig built: {result.created_nodes} nodes.")
        else:
            log.error(f"Rig build failed: {result.message}")
        return result

    def _build_blendshapes(self) -> None:
        """Build blendshape targets."""
        log.info("Building blendshapes...")
        # Future: BlendshapeManager().build(self.mesh, self.template)
        log.debug("Blendshapes built (placeholder).")

    def _build_arkit(self) -> None:
        """Generate ARKit poses."""
        log.info("Generating ARKit poses...")
        # Future: PoseGenerator().generate()
        log.debug("ARKit poses generated (placeholder).")

    def _build_picker(self) -> None:
        """Create the facial picker UI."""
        log.info("Creating picker...")
        # Future: PickerBuilder().build(self.template)
        log.debug("Picker created (placeholder).")

    def _save_project(self) -> None:
        """Save the project metadata."""
        log.info("Saving project...")
        # Future: project.save()
        log.debug("Project saved (placeholder).")


# ---------------------------------------------------------
# Singleton
# ---------------------------------------------------------

rig_pipeline = RigPipeline()