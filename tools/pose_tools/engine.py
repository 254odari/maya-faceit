# -*- coding: utf-8 -*-
"""
tools/pose_tools/engine.py

Main facade for pose operations.
"""

import maya.cmds as cmds # type: ignore
from typing import List, Optional, Dict, Any, Union
from .types import (
    Pose, PoseInfo, PoseCategory, PoseType, PoseState,
    PoseBlendMode, PoseAttribute, PoseReport
)
from .settings import DEFAULT_POSE_SETTINGS
from .editor import PoseEditor
from .manager import PoseManager
from .blend import PoseBlender
from .mirror import PoseMirror
from .exporter import PoseExporter
from .validation import PoseValidator


class PoseEngine:
    """
    Main facade for all pose operations.
    """

    def __init__(self, settings=None):
        self.settings = settings or DEFAULT_POSE_SETTINGS
        self.editor = PoseEditor(self.settings)
        self.manager = PoseManager(self.editor)
        self.blender = PoseBlender(self.editor, self.manager)
        self.mirror = PoseMirror(self.editor, self.manager)
        self.exporter = PoseExporter(self.editor, self.manager)
        self.validator = PoseValidator(self.editor, self.manager)

    # =========================================================================
    # CAPTURE / CREATE
    # =========================================================================

    def capture(self, name: str,
                objects: Optional[List[str]] = None,
                attributes: Optional[List[str]] = None,
                category: PoseCategory = PoseCategory.CUSTOM,
                description: str = "",
                tags: Optional[List[str]] = None) -> Optional[Pose]:
        """
        Capture current scene state as a pose.

        Args:
            name: Pose name.
            objects: Objects to capture from. If None, uses selection.
            attributes: Specific attributes. If None, captures all keyable.
            category: Pose category.
            description: Description.
            tags: Tags for the pose.

        Returns:
            The created Pose object, or None on failure.
        """
        attrs = self.editor.capture_from_scene(objects, attributes)
        if not attrs:
            return None
        # Convert to dict for creation
        attr_dicts = [{"name": a.name, "value": a.value, "type": a.type} for a in attrs]
        return self.manager.create_pose(name, attr_dicts, category, description, tags)

    def capture_controllers(self, name: str,
                            controllers: Optional[List[str]] = None,
                            category: PoseCategory = PoseCategory.EXPRESSION) -> Optional[Pose]:
        """Capture only controller transforms as a pose."""
        if controllers is None:
            controllers = self.editor.get_controller_list()
        attrs = self.editor.capture_controllers(controllers)
        if not attrs:
            return None
        attr_dicts = [{"name": a.name, "value": a.value, "type": a.type} for a in attrs]
        return self.manager.create_pose(name, attr_dicts, category)

    def capture_blendshapes(self, name: str,
                            blendshape_nodes: Optional[List[str]] = None,
                            category: PoseCategory = PoseCategory.EXPRESSION) -> Optional[Pose]:
        """Capture only blendshape weights as a pose."""
        if blendshape_nodes is None:
            blendshape_nodes = self.editor.get_blendshape_nodes()
        attrs = self.editor.capture_blendshapes(blendshape_nodes)
        if not attrs:
            return None
        attr_dicts = [{"name": a.name, "value": a.value, "type": a.type} for a in attrs]
        return self.manager.create_pose(name, attr_dicts, category)

    # =========================================================================
    # APPLY
    # =========================================================================

    def apply(self, name: str, blend_factor: float = 1.0,
              blend_mode: PoseBlendMode = PoseBlendMode.OVERWRITE) -> PoseReport:
        """
        Apply a pose to the scene.

        Args:
            name: Pose name.
            blend_factor: Blending factor (0-1).
            blend_mode: Blending mode.

        Returns:
            PoseReport with results.
        """
        pose = self.manager.get_pose(name)
        if not pose:
            return PoseReport(success=False, operation="apply", pose_name=name,
                              errors=[f"Pose '{name}' not found."])

        # Apply the pose
        modified = self.editor.apply_to_scene(pose.attributes, blend_factor, blend_mode.value)

        report = PoseReport(
            success=modified > 0,
            operation="apply",
            pose_name=name,
            modified_count=modified,
        )
        if modified == 0:
            report.warnings.append("No attributes were modified.")
        return report

    def apply_pose_object(self, pose: Pose, blend_factor: float = 1.0,
                          blend_mode: PoseBlendMode = PoseBlendMode.OVERWRITE) -> PoseReport:
        """Apply a Pose object directly."""
        modified = self.editor.apply_to_scene(pose.attributes, blend_factor, blend_mode.value)
        return PoseReport(
            success=modified > 0,
            operation="apply",
            pose_name=pose.name,
            modified_count=modified,
        )

    # =========================================================================
    # BLENDING
    # =========================================================================

    def blend(self, pose1: str, pose2: str, result_name: str,
              blend_factor: float = 0.5,
              mode: PoseBlendMode = PoseBlendMode.AVERAGE) -> Optional[Pose]:
        """
        Blend two poses into a new pose.

        Returns:
            The new blended Pose.
        """
        return self.blender.blend_poses(pose1, pose2, result_name, blend_factor, mode)

    # =========================================================================
    # MIRROR
    # =========================================================================

    def mirror_pose(self, name: str, result_name: Optional[str] = None,
                    axis: str = "x") -> Optional[Pose]:
        """
        Mirror a pose.

        Returns:
            The mirrored Pose.
        """
        return self.mirror.mirror_pose(name, result_name, axis)

    # =========================================================================
    # LIBRARY MANAGEMENT
    # =========================================================================

    def list_poses(self, category: Optional[PoseCategory] = None,
                   pose_type: Optional[PoseType] = None) -> List[PoseInfo]:
        """List all poses in the library."""
        return self.manager.list_poses(category, pose_type)

    def get_pose(self, name: str) -> Optional[Pose]:
        """Get a pose from the library."""
        return self.manager.get_pose(name)

    def get_pose_info(self, name: str) -> Optional[PoseInfo]:
        """Get pose information."""
        return self.manager.get_pose_info(name)

    def delete_pose(self, name: str) -> bool:
        """Delete a pose from the library."""
        return self.manager.delete_pose(name)

    def update_pose(self, name: str, **kwargs) -> bool:
        """Update a pose's metadata or attributes."""
        return self.manager.update_pose(name, **kwargs)

    def clear_library(self):
        """Clear the entire pose library."""
        # We'll need a method to clear the manager's library
        self.manager._library.clear()
        self.manager.clear_cache()

    # =========================================================================
    # EXPORT / IMPORT
    # =========================================================================

    def export(self, filepath: str, names: Optional[List[str]] = None,
               format: str = "json") -> bool:
        """Export poses to a file."""
        return self.exporter.export(filepath, names, format)

    def import_poses(self, filepath: str, overwrite: bool = False) -> int:
        """Import poses from a file."""
        return self.exporter.import_poses(filepath, overwrite)

    # =========================================================================
    # VALIDATION
    # =========================================================================

    def validate(self, name: str) -> Dict[str, Any]:
        """Validate a pose."""
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

pose_tools = PoseEngine()

__all__ = ["PoseEngine", "pose_tools"]