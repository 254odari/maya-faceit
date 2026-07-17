# -*- coding: utf-8 -*-
"""
tools/pose_tools/exporter.py

Export/import poses to/from JSON/XML.
"""

import json
import os
from typing import List, Optional, Dict, Any
from .types import Pose, PoseCategory, PoseType
from .editor import PoseEditor
from .manager import PoseManager


class PoseExporter:
    """
    Handles export/import of poses.
    """

    def __init__(self, editor: PoseEditor, manager: PoseManager):
        self.editor = editor
        self.manager = manager

    def export(self, filepath: str, names: Optional[List[str]] = None,
               format: str = "json") -> bool:
        """
        Export poses to a file.

        Args:
            filepath: Path to save the file.
            names: List of pose names to export. If None, exports all.
            format: "json" (default).

        Returns:
            True if successful.
        """
        # Get poses to export
        if names is None:
            poses = list(self.manager._library.values())
        else:
            poses = [self.manager.get_pose(n) for n in names if self.manager.get_pose(n)]

        if not poses:
            return False

        # Build data structure
        data = [p.to_dict() for p in poses]

        # Write to file
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                if format == "json":
                    json.dump(data, f, indent=2, default=str)
                else:
                    # XML or other formats can be added
                    return False
            return True
        except Exception as e:
            print(f"Error exporting poses: {e}")
            return False

    def import_poses(self, filepath: str, overwrite: bool = False) -> int:
        """
        Import poses from a file.

        Args:
            filepath: Path to the file.
            overwrite: If True, overwrite existing poses.

        Returns:
            Number of poses imported.
        """
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

            # Check if pose already exists
            if self.manager.get_pose(name) and not overwrite:
                continue

            # Create pose from dict
            pose = Pose.from_dict(item)
            # Add to manager
            self.manager._library[name] = pose
            self.manager._cache[name] = pose
            imported += 1

        return imported