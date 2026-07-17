# -*- coding: utf-8 -*-
"""
tools/selection_sets/manager.py

Higher-level set management with caching and validation.
"""

import time
from typing import List, Optional, Dict, Any
from .types import SetInfo, SelectionSetType, SelectionSetState
from .editor import SelectionSetEditor


class SetManager:
    """
    Manages selection sets with caching and additional logic.
    """

    def __init__(self, editor: SelectionSetEditor):
        self.editor = editor
        self._cache: Dict[str, SetInfo] = {}

    # =========================================================================
    # CREATE / DELETE / RENAME
    # =========================================================================

    def create_set(self, name: str, members: List[str],
                   set_type: Optional[SelectionSetType] = None,
                   description: str = "",
                   tags: Optional[List[str]] = None) -> Optional[SetInfo]:
        """Create a new selection set."""
        # Check if set already exists
        if self.editor.get_set_members(name):
            return None

        full_name = f"{self.editor.settings.naming_prefix}{name}{self.editor.settings.naming_suffix}"
        set_node = self.editor.create_set(full_name, members, set_type)
        if not set_node:
            return None

        info = SetInfo(
            name=set_node,
            set_type=set_type or self.editor._detect_type(members),
            state=SelectionSetState.NORMAL,
            members=members,
            count=len(members),
            description=description,
            tags=tags or [],
            created=time.ctime(),
            modified=time.ctime(),
        )
        self._cache[set_node] = info
        return info

    def delete_set(self, name: str) -> bool:
        """Delete a selection set."""
        if name in self._cache:
            del self._cache[name]
        return self.editor.delete_set(name)

    def rename_set(self, old_name: str, new_name: str) -> bool:
        """Rename a selection set."""
        if not self.editor.rename_set(old_name, new_name):
            return False
        # Update cache
        if old_name in self._cache:
            info = self._cache.pop(old_name)
            info.name = new_name
            info.modified = time.ctime()
            self._cache[new_name] = info
        return True

    # =========================================================================
    # QUERY
    # =========================================================================

    def list_sets(self, set_type: Optional[SelectionSetType] = None) -> List[SetInfo]:
        """List all sets, optionally filtered by type."""
        names = self.editor.list_sets(set_type)
        result = []
        for n in names:
            info = self.get_set_info(n)
            if info:
                result.append(info)
        return result

    def get_set_info(self, name: str) -> Optional[SetInfo]:
        """Get set information (cached)."""
        # Check cache first
        if name in self._cache:
            return self._cache[name]
        # Fetch from Maya
        data = self.editor.get_set_info(name)
        if not data:
            return None
        info = SetInfo(
            name=name,
            set_type=data['type'],
            state=SelectionSetState.NORMAL,
            members=data['members'],
            count=data['count'],
        )
        self._cache[name] = info
        return info

    def get_set_members(self, name: str) -> List[str]:
        """Get members of a set."""
        return self.editor.get_set_members(name)

    # =========================================================================
    # MODIFY
    # =========================================================================

    def update_set_members(self, name: str, members: List[str]) -> bool:
        """Replace all members of a set."""
        if not self.editor.replace_members(name, members):
            return False
        # Update cache
        if name in self._cache:
            self._cache[name].members = members
            self._cache[name].count = len(members)
            self._cache[name].modified = time.ctime()
        return True

    def add_to_set(self, name: str, members: List[str]) -> bool:
        """Add members to a set."""
        if not self.editor.add_to_set(name, members):
            return False
        # Update cache
        if name in self._cache:
            current = self._cache[name].members
            self._cache[name].members = current + members
            self._cache[name].count = len(self._cache[name].members)
            self._cache[name].modified = time.ctime()
        return True

    def remove_from_set(self, name: str, members: List[str]) -> bool:
        """Remove members from a set."""
        if not self.editor.remove_from_set(name, members):
            return False
        # Update cache
        if name in self._cache:
            current = self._cache[name].members
            self._cache[name].members = [m for m in current if m not in members]
            self._cache[name].count = len(self._cache[name].members)
            self._cache[name].modified = time.ctime()
        return True

    def clear_cache(self):
        """Clear internal cache."""
        self._cache.clear()