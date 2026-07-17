# -*- coding: utf-8 -*-
"""
tools/pose_tools/manager.py

Pose library management with caching.
"""

import time
from typing import List, Optional, Dict, Any
from .types import Pose, PoseInfo, PoseCategory, PoseState, PoseType, PoseAttribute
from .editor import PoseEditor


class PoseManager:
    """
    Manages pose libraries with caching and persistence.
    """

    def __init__(self, editor: PoseEditor):
        self.editor = editor
        self._cache: Dict[str, Pose] = {}
        self._library: Dict[str, Pose] = {}  # Full library (cached)

    # =========================================================================
    # POSE MANAGEMENT
    # =========================================================================

    def create_pose(self, name: str, attributes: List[Dict[str, Any]],
                    category: PoseCategory = PoseCategory.CUSTOM,
                    description: str = "",
                    tags: Optional[List[str]] = None) -> Optional[Pose]:
        """
        Create a new pose from attribute data.
        """
        if name in self._library:
            return None  # Already exists

        # Convert dict attributes to PoseAttribute objects
        pose_attrs = []
        for attr_data in attributes:
            pose_attrs.append(PoseAttribute(
                name=attr_data.get("name"),
                value=attr_data.get("value"),
                type=attr_data.get("type", "float")
            ))

        # Detect pose type
        pose_type = PoseType.MIXED
        if all(a.type == "float" and (a.name.endswith(("tx", "ty", "tz", "rx", "ry", "rz")) or "blendShape" in a.name) for a in pose_attrs):
            # Check if mostly controllers or blendshapes
            ctrl_count = sum(1 for a in pose_attrs if a.name.endswith(("tx", "ty", "tz", "rx", "ry", "rz")))
            bs_count = sum(1 for a in pose_attrs if "blendShape" in a.name)
            if ctrl_count > bs_count:
                pose_type = PoseType.CONTROLLER
            elif bs_count > ctrl_count:
                pose_type = PoseType.BLENDSHAPE
            else:
                pose_type = PoseType.MIXED
        else:
            pose_type = PoseType.ATTRIBUTE

        pose = Pose(
            name=name,
            category=category,
            pose_type=pose_type,
            state=PoseState.NORMAL,
            attributes=pose_attrs,
            description=description,
            tags=tags or [],
            created=time.ctime(),
            modified=time.ctime(),
        )
        self._library[name] = pose
        self._cache[name] = pose
        return pose

    def delete_pose(self, name: str) -> bool:
        """Delete a pose from the library."""
        if name in self._library:
            del self._library[name]
            if name in self._cache:
                del self._cache[name]
            return True
        return False

    def get_pose(self, name: str) -> Optional[Pose]:
        """Get a pose from the library (cached)."""
        if name in self._cache:
            return self._cache[name]
        # If not in cache but in library, load from library
        if name in self._library:
            self._cache[name] = self._library[name]
            return self._library[name]
        return None

    def get_pose_info(self, name: str) -> Optional[PoseInfo]:
        """Get pose information (without full attribute data)."""
        pose = self.get_pose(name)
        if not pose:
            return None
        return PoseInfo(
            name=pose.name,
            category=pose.category,
            pose_type=pose.pose_type,
            state=pose.state,
            description=pose.description,
            tags=pose.tags,
            attribute_count=len(pose.attributes),
            created=pose.created,
            modified=pose.modified,
        )

    def list_poses(self, category: Optional[PoseCategory] = None,
                   pose_type: Optional[PoseType] = None,
                   tags: Optional[List[str]] = None) -> List[PoseInfo]:
        """List all poses, optionally filtered."""
        poses = []
        for pose in self._library.values():
            # Apply filters
            if category and pose.category != category:
                continue
            if pose_type and pose.pose_type != pose_type:
                continue
            if tags:
                if not any(t in pose.tags for t in tags):
                    continue
            poses.append(PoseInfo(
                name=pose.name,
                category=pose.category,
                pose_type=pose.pose_type,
                state=pose.state,
                description=pose.description,
                tags=pose.tags,
                attribute_count=len(pose.attributes),
                created=pose.created,
                modified=pose.modified,
            ))
        return poses

    def update_pose(self, name: str, attributes: Optional[List[PoseAttribute]] = None,
                    description: Optional[str] = None,
                    tags: Optional[List[str]] = None) -> bool:
        """Update a pose's attributes and metadata."""
        pose = self.get_pose(name)
        if not pose:
            return False
        if attributes is not None:
            pose.attributes = attributes
        if description is not None:
            pose.description = description
        if tags is not None:
            pose.tags = tags
        pose.modified = time.ctime()
        self._cache[name] = pose
        self._library[name] = pose
        return True

    def clear_cache(self):
        """Clear the cache but keep library."""
        self._cache.clear()

    def get_library_size(self) -> int:
        """Get the number of poses in the library."""
        return len(self._library)