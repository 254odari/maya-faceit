# -*- coding: utf-8 -*-
"""
maya_faceit.application.project

Project management (load/save, recent projects, etc.).
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class ProjectManager:
    """Manages the current project and project metadata."""

    def __init__(self) -> None:
        self._current_project: Optional[Dict[str, Any]] = None
        self._project_path: Optional[Path] = None

    def create(self, name: str, path: str, template: str = "Default") -> bool:
        """Create a new project."""
        project_dir = Path(path) / name
        project_dir.mkdir(parents=True, exist_ok=True)

        self._project_path = project_dir / "project.json"
        self._current_project = {
            "name": name,
            "path": str(project_dir),
            "template": template,
            "created": None,  # set timestamp later
            "modified": None,
            "rig": {},
            "blendshapes": [],
            "arkit_mapping": {},
        }
        return self.save()

    def load(self, path: str) -> bool:
        """Load a project from disk."""
        try:
            p = Path(path)
            if not p.exists():
                logger.error("Project file not found: %s", path)
                return False
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._current_project = data
            self._project_path = p
            logger.info("Loaded project: %s", data.get("name"))
            return True
        except Exception as e:
            logger.error("Failed to load project: %s", e)
            return False

    def save(self) -> bool:
        """Save the current project."""
        if not self._current_project or not self._project_path:
            return False
        try:
            self._project_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._project_path, "w", encoding="utf-8") as f:
                json.dump(self._current_project, f, indent=2)
            return True
        except Exception as e:
            logger.error("Failed to save project: %s", e)
            return False

    def get_current(self) -> Optional[Dict[str, Any]]:
        """Return the current project data."""
        return self._current_project

    def get_path(self) -> Optional[Path]:
        """Return the path to the current project file."""
        return self._project_path

    def get_recent_projects(self) -> List[str]:
        """Return a list of recent project paths."""
        # Could be stored in preferences
        return []