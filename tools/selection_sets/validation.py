# -*- coding: utf-8 -*-
"""
tools/selection_sets/validation.py

Validation for selection sets.
"""

import maya.cmds as cmds # type: ignore
from typing import Dict, Any, List
from .editor import SelectionSetEditor
from .manager import SetManager


class SelectionSetValidator:
    """
    Validate selection sets for integrity.
    """

    def __init__(self, editor: SelectionSetEditor):
        self.editor = editor
        self.manager = SetManager(editor)

    def validate(self, name: str) -> Dict[str, Any]:
        """
        Validate a selection set.

        Checks:
            - Set exists
            - Members exist
            - Members are of the correct type (if set_type specified)
        """
        result = {
            'name': name,
            'valid': True,
            'warnings': [],
            'errors': [],
            'details': {}
        }

        # Check existence
        info = self.manager.get_set_info(name)
        if not info:
            result['valid'] = False
            result['errors'].append(f"Set '{name}' does not exist.")
            return result

        # Check members
        members = self.editor.get_set_members(name)
        if not members:
            result['warnings'].append("Set is empty.")

        # Check each member exists
        missing = []
        for m in members:
            if not cmds.objExists(m):
                missing.append(m)
        if missing:
            result['errors'].append(f"Missing members: {', '.join(missing[:10])}")
            result['valid'] = False

        # Check member types match set type
        if info.set_type and info.set_type != 'mixed':
            expected = info.set_type.value
            for m in members:
                if not m.startswith(expected):
                    result['warnings'].append(f"Member '{m}' may not match set type '{expected}'.")

        result['details'] = {
            'count': len(members),
            'type': info.set_type.value if info.set_type else 'unknown',
        }

        return result