# -*- coding: utf-8 -*-
"""
tools/selection_sets/editor.py

Low-level Maya set operations.
"""

import maya.cmds as cmds # type: ignore
from typing import List, Optional, Dict, Any, Union
from .types import SetInfo, SelectionSetType, SelectionSetState


class SelectionSetEditor:
    """
    Low-level Maya set operations using Maya's 'sets' command.
    """

    def __init__(self, settings):
        self.settings = settings

    # =========================================================================
    # CREATE / DELETE
    # =========================================================================

    def create_set(self, name: str, members: List[str],
                   set_type: Optional[SelectionSetType] = None) -> Optional[str]:
        """
        Create a Maya set.

        Args:
            name: Set name.
            members: List of components.
            set_type: Type of set.

        Returns:
            Set name if successful, else None.
        """
        if not members:
            return None

        # Determine set type if not provided
        if set_type is None:
            set_type = self._detect_type(members)

        # Build full name with prefix/suffix
        full_name = f"{self.settings.naming_prefix}{name}{self.settings.naming_suffix}"

        # Create the set
        try:
            # Use Maya's sets command
            # For component sets, we need to use the -type flag
            if set_type == SelectionSetType.VERTEX:
                set_node = cmds.sets(members, name=full_name, type=set_type.value)
            elif set_type == SelectionSetType.EDGE:
                set_node = cmds.sets(members, name=full_name, type=set_type.value)
            elif set_type == SelectionSetType.FACE:
                set_node = cmds.sets(members, name=full_name, type=set_type.value)
            elif set_type == SelectionSetType.OBJECT:
                set_node = cmds.sets(members, name=full_name)
            elif set_type == SelectionSetType.UV:
                set_node = cmds.sets(members, name=full_name, type=set_type.value)
            else:
                # Fallback: use default sets
                set_node = cmds.sets(members, name=full_name)

            if set_node:
                return set_node[0] if isinstance(set_node, list) else set_node
        except Exception as e:
            print(f"Error creating set '{name}': {e}")
        return None

    def delete_set(self, name: str) -> bool:
        """Delete a Maya set."""
        if not cmds.objExists(name):
            return False
        try:
            cmds.delete(name)
            return True
        except:
            return False

    def rename_set(self, old_name: str, new_name: str) -> bool:
        """Rename a Maya set."""
        if not cmds.objExists(old_name):
            return False
        if cmds.objExists(new_name):
            return False
        try:
            cmds.rename(old_name, new_name)
            return True
        except:
            return False

    # =========================================================================
    # QUERY
    # =========================================================================

    def list_sets(self, set_type: Optional[SelectionSetType] = None) -> List[str]:
        """List all sets (optionally filtered by type)."""
        # List all sets
        all_sets = cmds.ls(type='objectSet')
        if not all_sets:
            return []
        # Filter by type if specified
        if set_type is not None:
            filtered = []
            for s in all_sets:
                attr = f"{s}.setType"
                if cmds.objExists(attr):
                    s_type = cmds.getAttr(attr)
                    if s_type == set_type.value:
                        filtered.append(s)
            return filtered
        return all_sets

    def get_set_members(self, name: str) -> List[str]:
        """Get members of a set."""
        if not cmds.objExists(name):
            return []
        try:
            return cmds.sets(name, q=True) or []
        except:
            return []

    def get_set_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get information about a set."""
        if not cmds.objExists(name):
            return None
        members = self.get_set_members(name)
        # Detect type
        set_type = self._detect_type(members)
        return {
            'name': name,
            'members': members,
            'count': len(members),
            'type': set_type,
        }

    # =========================================================================
    # MODIFY
    # =========================================================================

    def add_to_set(self, name: str, members: List[str]) -> bool:
        """Add members to a set."""
        if not cmds.objExists(name) or not members:
            return False
        try:
            cmds.sets(members, add=name)
            return True
        except:
            return False

    def remove_from_set(self, name: str, members: List[str]) -> bool:
        """Remove members from a set."""
        if not cmds.objExists(name) or not members:
            return False
        try:
            cmds.sets(members, remove=name)
            return True
        except:
            return False

    def replace_members(self, name: str, members: List[str]) -> bool:
        """Replace all members of a set."""
        if not cmds.objExists(name):
            return False
        # Remove all current members, then add new ones
        try:
            current = self.get_set_members(name)
            if current:
                cmds.sets(current, remove=name)
            if members:
                cmds.sets(members, add=name)
            return True
        except:
            return False

    # =========================================================================
    # UTILITY
    # =========================================================================

    def _detect_type(self, members: List[str]) -> SelectionSetType:
        """Auto-detect set type from members."""
        if not members:
            return SelectionSetType.OBJECT
        # Check for component patterns
        if any('.vtx[' in m for m in members):
            return SelectionSetType.VERTEX
        if any('.e[' in m for m in members):
            return SelectionSetType.EDGE
        if any('.f[' in m for m in members):
            return SelectionSetType.FACE
        if any('.uv[' in m for m in members):
            return SelectionSetType.UV
        return SelectionSetType.OBJECT