# -*- coding: utf-8 -*-
"""
tools/selection_sets/engine.py

Main facade for selection set operations.
"""

import maya.cmds as cmds # type: ignore
from typing import List, Optional, Union, Dict, Any
from .types import SetInfo, SelectionSetType, SelectionSetState
from .settings import DEFAULT_SETTINGS
from .editor import SelectionSetEditor
from .manager import SetManager
from .exporter import SelectionSetExporter
from .validation import SelectionSetValidator


class SelectionSetEngine:
    """
    Main facade for all selection set operations.
    """

    def __init__(self, settings=None):
        self.settings = settings or DEFAULT_SETTINGS
        self.editor = SelectionSetEditor(self.settings)
        self.manager = SetManager(self.editor)
        self.exporter = SelectionSetExporter(self.editor)
        self.validator = SelectionSetValidator(self.editor)

    # =========================================================================
    # SET MANAGEMENT
    # =========================================================================

    def create(self, name: str, members: List[str],
               set_type: Optional[SelectionSetType] = None,
               description: str = "",
               tags: Optional[List[str]] = None) -> Optional[SetInfo]:
        """
        Create a new selection set.

        Args:
            name: Set name.
            members: List of Maya components (e.g., "pCube1.vtx[0:10]").
            set_type: Type of set (auto-detected if None).
            description: Optional description.
            tags: Optional list of tags.

        Returns:
            SetInfo for the created set, or None on failure.
        """
        return self.manager.create_set(name, members, set_type, description, tags)

    def delete(self, name: str) -> bool:
        """Delete a selection set."""
        return self.manager.delete_set(name)

    def rename(self, old_name: str, new_name: str) -> bool:
        """Rename a selection set."""
        return self.manager.rename_set(old_name, new_name)

    def list_sets(self, set_type: Optional[SelectionSetType] = None) -> List[SetInfo]:
        """List all selection sets, optionally filtered by type."""
        return self.manager.list_sets(set_type)

    def get_set(self, name: str) -> Optional[SetInfo]:
        """Get information about a selection set."""
        return self.manager.get_set_info(name)

    def get_members(self, name: str) -> List[str]:
        """Get the members of a selection set."""
        return self.manager.get_set_members(name)

    def update_members(self, name: str, members: List[str]) -> bool:
        """Replace all members of a selection set."""
        return self.manager.update_set_members(name, members)

    def add_members(self, name: str, members: List[str]) -> bool:
        """Add members to a selection set."""
        return self.manager.add_to_set(name, members)

    def remove_members(self, name: str, members: List[str]) -> bool:
        """Remove members from a selection set."""
        return self.manager.remove_from_set(name, members)

    # =========================================================================
    # SELECTION HELPERS
    # =========================================================================

    def select(self, name: str, replace: bool = True) -> bool:
        """Select the members of a selection set."""
        members = self.get_members(name)
        if not members:
            return False
        if replace:
            cmds.select(members, replace=True)
        else:
            cmds.select(members, add=True)
        return True

    def get_selection_as_set(self, name: str,
                             set_type: Optional[SelectionSetType] = None) -> Optional[SetInfo]:
        """Create a set from the current selection."""
        selection = cmds.ls(selection=True, flatten=True)
        if not selection:
            return None
        return self.create(name, selection, set_type)

    # =========================================================================
    # EXPORT / IMPORT
    # =========================================================================

    def export(self, filepath: str, names: Optional[List[str]] = None) -> bool:
        """Export selection sets to a file."""
        return self.exporter.export(filepath, names)

    def import_sets(self, filepath: str) -> int:
        """Import selection sets from a file."""
        return self.exporter.import_sets(filepath)

    # =========================================================================
    # VALIDATION
    # =========================================================================

    def validate(self, name: str) -> Dict[str, Any]:
        """Validate a selection set."""
        return self.validator.validate(name)

    # =========================================================================
    # UTILITY
    # =========================================================================

    def set_settings(self, settings):
        self.settings = settings
        self.editor.settings = settings

    def get_settings(self):
        return self.settings


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

selection_sets = SelectionSetEngine()

__all__ = ["SelectionSetEngine", "selection_sets"]