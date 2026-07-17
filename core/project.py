# -*- coding: utf-8 -*-
"""
core/project.py

Project management for Maya Faceit.

Handles:
    - Project creation
    - Project loading
    - Project saving
    - Autosave
    - Recent projects
    - Metadata
    - Version compatibility
    - Nested data access

Author: Maya FaceIT Team
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union

from ..version import VERSION_STRING

logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# Project Data Model
# ---------------------------------------------------------

@dataclass
class Project:
    """
    Project data container.

    Stores the full project state including rig, blendshapes, ARKit, etc.
    """
    name: str = "Untitled"
    path: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    created: str = field(default_factory=lambda: datetime.now().isoformat())
    modified: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def default_data() -> Dict[str, Any]:
        """Return the default project data structure."""
        return {
            "project": {
                "name": "Untitled",
                "version": VERSION_STRING,
                "created": datetime.now().isoformat(),
                "modified": datetime.now().isoformat()
            },
            "scene": {
                "path": "",
                "units": "cm"
            },
            "rig": {
                "mesh": "",
                "template": "Human",
                "controllers": [],
                "joints": []
            },
            "landmarks": {
                "points": []
            },
            "blendshapes": {
                "targets": []
            },
            "arkit": {
                "mapping": {}
            },
            "mocap": {
                "calibration": {}
            },
            "export": {
                "settings": {}
            }
        }


# ---------------------------------------------------------
# Project Manager
# ---------------------------------------------------------

class ProjectManager:
    """
    Manages the current project.

    Projects are stored as JSON files in the user's project directory.
    """

    FILE_EXTENSION = ".faceit"
    AUTOSAVE_EXTENSION = ".autosave"

    def __init__(self):
        self._project: Optional[Project] = None
        self._base_dir = Path.home() / ".faceit" / "projects"
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._current_path = self._base_dir / "current.json"
        self._recent_path = self._base_dir / "recent.json"

    # ---------------------------------------------------------
    # Project Management
    # ---------------------------------------------------------

    def get(self) -> Optional[Project]:
        """Get the current project."""
        return self._project

    def set(self, project: Project) -> None:
        """Set the current project."""
        self._project = project

    def new(self, name: str = "Untitled") -> Project:
        """Create a new project."""
        project = Project(name=name, data=Project.default_data())
        self._project = project
        self._save_current()
        logger.info(f"Created new project: {name}")
        return project

    def load(self, filepath: Union[str, Path]) -> bool:
        """
        Load a project from a file.

        Args:
            filepath: Path to the .faceit file.

        Returns:
            True if successful.
        """
        filepath = Path(filepath)
        if not filepath.exists():
            logger.error(f"Project file not found: {filepath}")
            return False

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Determine if it's the new format (with 'project' top-level) or old format
            if "project" in data and "scene" in data and "rig" in data:
                # New format: full project data
                project = Project(
                    name=data["project"].get("name", "Untitled"),
                    path=str(filepath),
                    data=data,
                    created=data["project"].get("created", datetime.now().isoformat()),
                    modified=data["project"].get("modified", datetime.now().isoformat()),
                )
            else:
                # Old format: just a simple project dict
                project = Project(
                    name=data.get("name", "Untitled"),
                    path=str(filepath),
                    data=Project.default_data(),
                    metadata=data,
                )
                # Update the data with the loaded values
                project.data["project"]["name"] = project.name
                # Merge metadata into appropriate sections
                for key, value in data.items():
                    if key in project.data:
                        project.data[key].update(value) if isinstance(value, dict) else project.data[key] = value

            self._project = project
            self._save_current()
            self._add_to_recent(str(filepath))
            logger.info(f"Loaded project: {filepath}")
            return True

        except Exception as e:
            logger.exception(f"Failed to load project: {e}")
            return False

    def save(self) -> bool:
        """Save the current project to its file."""
        if not self._project:
            logger.warning("No project to save.")
            return False

        if not self._project.path:
            logger.warning("Project has no file path. Use save_as() to specify a location.")
            return False

        try:
            # Update timestamps
            self._project.modified = datetime.now().isoformat()
            if "project" in self._project.data:
                self._project.data["project"]["modified"] = self._project.modified
                self._project.data["project"]["name"] = self._project.name

            with open(self._project.path, 'w', encoding='utf-8') as f:
                json.dump(self._project.data, f, indent=4, sort_keys=True)

            self._save_current()
            logger.info(f"Saved project: {self._project.path}")
            return True

        except Exception as e:
            logger.exception(f"Failed to save project: {e}")
            return False

    def save_as(self, filepath: Union[str, Path]) -> bool:
        """Save the current project to a new location."""
        filepath = Path(filepath)
        if filepath.suffix != self.FILE_EXTENSION:
            filepath = filepath.with_suffix(self.FILE_EXTENSION)

        if self._project:
            self._project.path = str(filepath)
            self._project.name = filepath.stem
        else:
            self._project = Project(name=filepath.stem, path=str(filepath), data=Project.default_data())

        return self.save()

    def autosave(self) -> bool:
        """Create an autosave of the current project."""
        if not self._project or not self._project.path:
            return False

        autosave_path = Path(self._project.path).with_suffix(self.AUTOSAVE_EXTENSION)
        try:
            with open(autosave_path, 'w', encoding='utf-8') as f:
                json.dump(self._project.data, f, indent=4)
            logger.debug(f"Project autosaved: {autosave_path}")
            return True
        except Exception as e:
            logger.warning(f"Autosave failed: {e}")
            return False

    def clear(self) -> None:
        """Clear the current project."""
        self._project = None
        if self._current_path.exists():
            self._current_path.unlink()
        logger.info("Project cleared.")

    # ---------------------------------------------------------
    # Data Access
    # ---------------------------------------------------------

    def get_nested(self, *keys) -> Any:
        """
        Get a nested value from the project data.

        Args:
            *keys: Path to the value (e.g., 'rig', 'mesh')

        Returns:
            The value, or None if any key is missing.
        """
        if not self._project:
            return None
        data = self._project.data
        for key in keys:
            if key not in data:
                return None
            data = data[key]
        return data

    def set_nested(self, value: Any, *keys) -> bool:
        """
        Set a nested value in the project data.

        Args:
            value: Value to set.
            *keys: Path to the value.

        Returns:
            True if successful.
        """
        if not self._project:
            return False
        data = self._project.data
        for key in keys[:-1]:
            if key not in data:
                data[key] = {}
            data = data[key]
        data[keys[-1]] = value
        return True

    def exists(self, *keys) -> bool:
        """Check if a nested key exists."""
        return self.get_nested(*keys) is not None

    # ---------------------------------------------------------
    # Validation
    # ---------------------------------------------------------

    def validate(self) -> bool:
        """Validate the project data structure."""
        if not self._project:
            return False
        required = ["project", "scene", "rig", "landmarks", "blendshapes", "arkit", "mocap", "export"]
        for key in required:
            if key not in self._project.data:
                logger.error(f"Missing project section: {key}")
                return False
        return True

    # ---------------------------------------------------------
    # Recent Projects
    # ---------------------------------------------------------

    def get_recent_projects(self, limit: int = 10) -> list:
        """Get a list of recent project paths."""
        try:
            if self._recent_path.exists():
                with open(self._recent_path, 'r', encoding='utf-8') as f:
                    recent = json.load(f)
                    return recent[:limit]
        except:
            pass
        return []

    def _add_to_recent(self, path: str) -> None:
        """Add a path to the recent projects list."""
        try:
            recent = self.get_recent_projects(100)
            if path in recent:
                recent.remove(path)
            recent.insert(0, path)
            with open(self._recent_path, 'w', encoding='utf-8') as f:
                json.dump(recent[:20], f, indent=2)
        except:
            pass

    def clear_recent(self) -> None:
        """Clear the recent projects list."""
        if self._recent_path.exists():
            self._recent_path.unlink()

    # ---------------------------------------------------------
    # Internal Helpers
    # ---------------------------------------------------------

    def _save_current(self) -> None:
        """Save the current project reference."""
        try:
            if self._project:
                with open(self._current_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        "name": self._project.name,
                        "path": self._project.path,
                        "created": self._project.created,
                        "modified": self._project.modified,
                        "metadata": self._project.metadata,
                    }, f, indent=2)
            else:
                if self._current_path.exists():
                    self._current_path.unlink()
        except Exception as e:
            logger.warning(f"Failed to save current project reference: {e}")


# -------------------------------------------------------------
# Global Instance
# -------------------------------------------------------------

project = ProjectManager()

__all__ = ["Project", "ProjectManager", "project"]