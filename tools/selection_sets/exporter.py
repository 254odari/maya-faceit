# -*- coding: utf-8 -*-
"""
tools/selection_sets/exporter.py

Export/import selection sets to/from JSON.
"""

import json
import os
from typing import List, Optional, Dict, Any
from .editor import SelectionSetEditor
from .manager import SetManager
from .types import SetInfo, SelectionSetType


class SelectionSetExporter:
    """
    Handles export/import of selection sets.
    """

    def __init__(self, editor: SelectionSetEditor):
        self.editor = editor
        self.manager = SetManager(editor)

    # =========================================================================
    # EXPORT
    # =========================================================================

    def export(self, filepath: str, names: Optional[List[str]] = None) -> bool:
        """
        Export selection sets to a JSON file.

        Args:
            filepath: Path to save the JSON file.
            names: List of set names to export. If None, exports all.

        Returns:
            True if successful.
        """
        # Get sets to export
        if names is None:
            sets = self.manager.list_sets()
        else:
            sets = []
            for n in names:
                info = self.manager.get_set_info(n)
                if info:
                    sets.append(info)

        if not sets:
            return False

        # Build data structure
        data = []
        for s in sets:
            item = {
                'name': s.name,
                'type': s.set_type.value if s.set_type else 'object',
                'members': s.members,
                'description': s.description,
                'tags': s.tags,
                'metadata': s.metadata,
            }
            data.append(item)

        # Write to file
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            return True
        except Exception as e:
            print(f"Error exporting sets: {e}")
            return False

    # =========================================================================
    # IMPORT
    # =========================================================================

    def import_sets(self, filepath: str, overwrite: bool = False) -> int:
        """
        Import selection sets from a JSON file.

        Args:
            filepath: Path to the JSON file.
            overwrite: If True, overwrite existing sets.

        Returns:
            Number of sets imported.
        """
        # Read file
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"Error reading file: {e}")
            return 0

        if not isinstance(data, list):
            return 0

        imported = 0
        for item in data:
            name = item.get('name')
            if not name:
                continue

            # Check if set already exists
            existing = self.manager.get_set_info(name)
            if existing and not overwrite:
                continue

            members = item.get('members', [])
            set_type_str = item.get('type', 'object')
            set_type = None
            try:
                set_type = SelectionSetType(set_type_str)
            except ValueError:
                pass

            # Create or replace the set
            if existing and overwrite:
                # Replace all members
                self.manager.update_set_members(name, members)
                imported += 1
            else:
                # Create new set
                info = self.manager.create_set(
                    name=name,
                    members=members,
                    set_type=set_type,
                    description=item.get('description', ''),
                    tags=item.get('tags', [])
                )
                if info:
                    # Update metadata
                    if 'metadata' in item:
                        info.metadata = item['metadata']
                    imported += 1

        return imported