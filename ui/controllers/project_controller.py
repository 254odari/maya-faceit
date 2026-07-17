"""
ui/controllers/project_controller.py

Controller for project settings and management.
"""

from __future__ import annotations

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class ProjectController:
    """Handles project-level operations."""

    def __init__(self):
        self._current_project: Optional[Dict[str, Any]] = None

    def load_project(self, path: str) -> Dict[str, Any]:
        """Load a project from disk."""
        logger.info(f"Loading project: {path}")
        # TODO: Deserialize project data
        self._current_project = {"name": "Test", "path": path, "template": "Default"}
        return self._current_project

    def save_project(self, path: str) -> bool:
        """Save current project to disk."""
        logger.info(f"Saving project to: {path}")
        # TODO: Serialize project data
        return True

    def get_project_info(self) -> Dict[str, Any]:
        """Return current project metadata."""
        return self._current_project or {"name": "None", "path": "", "template": "Default"}

    def set_template(self, template: str) -> None:
        """Set the rig template."""
        logger.info(f"Setting template: {template}")
        # TODO: Update project settings

    def get_available_templates(self) -> list:
        """Return list of available rig templates."""
        return ["Default", "Cartoon", "Realistic", "Stylized"]