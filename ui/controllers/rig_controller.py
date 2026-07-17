"""
ui/controllers/rig_controller.py

Controller for rig building and configuration.
"""

from __future__ import annotations

import logging
from typing import Optional, List

logger = logging.getLogger(__name__)


class RigController:
    """Handles rig operations."""

    def __init__(self):
        self._mesh: Optional[str] = None
        self._joint_prefix: str = "face_"

    def set_base_mesh(self, mesh_name: str) -> None:
        """Set the base mesh for the rig."""
        self._mesh = mesh_name
        logger.info(f"Base mesh set to: {mesh_name}")

    def build_rig(self, template: str) -> bool:
        """Build the rig using the specified template."""
        if not self._mesh:
            logger.error("No base mesh set.")
            return False
        logger.info(f"Building rig with template '{template}' on mesh '{self._mesh}'")
        # TODO: Call core rig builder
        return True

    def set_joint_prefix(self, prefix: str) -> None:
        """Set prefix for joint names."""
        self._joint_prefix = prefix

    def get_joint_prefix(self) -> str:
        return self._joint_prefix

    def get_available_templates(self) -> List[str]:
        """Return list of available rig templates."""
        return ["Face Rig v1", "Face Rig v2", "Full Body"]

    def get_statistics(self) -> dict:
        """Return rig statistics."""
        # TODO: Query core for stats
        return {"joints": 0, "controllers": 0, "blendshapes": 0}