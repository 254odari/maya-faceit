# -*- coding: utf-8 -*-
"""
tools/pose_tools/types.py

Enums and dataclasses for poses.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple


# =============================================================================
# ENUMS
# =============================================================================

class PoseCategory(Enum):
    """Category of a pose."""
    EXPRESSION = "expression"
    ARKIT = "arkit"
    FACS = "facs"
    CUSTOM = "custom"
    NEUTRAL = "neutral"
    MOUTH = "mouth"
    EYE = "eye"
    BROW = "brow"
    JAW = "jaw"
    CHEEK = "cheek"


class PoseType(Enum):
    """Type of pose data."""
    CONTROLLER = "controller"      # Controller transforms
    BLENDSHAPE = "blendshape"      # Blendshape weights
    ATTRIBUTE = "attribute"        # Custom attributes
    MIXED = "mixed"               # Combination of above


class PoseState(Enum):
    """State of a pose."""
    NORMAL = "normal"
    LOCKED = "locked"
    READ_ONLY = "read_only"
    TEMPORARY = "temporary"


class PoseBlendMode(Enum):
    """Blending mode for combining poses."""
    OVERWRITE = "overwrite"        # Replace all values
    ADD = "add"                    # Add values
    SUBTRACT = "subtract"          # Subtract values
    AVERAGE = "average"            # Average values
    MAX = "max"                    # Take maximum values
    MIN = "min"                    # Take minimum values
    CROSSFADE = "crossfade"        # Crossfade between poses


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class PoseAttribute:
    """
    A single attribute value in a pose.
    """
    name: str                      # Full attribute name (e.g., "jaw_ctrl.tx")
    value: float
    type: str = "float"            # "float", "bool", "int", "enum"


@dataclass
class Pose:
    """
    Definition of a pose.
    """
    name: str
    category: PoseCategory = PoseCategory.CUSTOM
    pose_type: PoseType = PoseType.MIXED
    state: PoseState = PoseState.NORMAL
    attributes: List[PoseAttribute] = field(default_factory=list)  # All attribute values
    description: str = ""
    tags: List[str] = field(default_factory=list)
    thumbnail: Optional[bytes] = None
    author: str = "unknown"
    created: str = ""
    modified: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_controllers(self) -> Dict[str, float]:
        """Get controller transform values (tx, ty, tz, rx, ry, rz, sx, sy, sz)."""
        result = {}
        for attr in self.attributes:
            # Controller attributes typically have transform names
            if any(attr.name.endswith(suffix) for suffix in ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"]):
                result[attr.name] = attr.value
        return result

    def get_blendshapes(self) -> Dict[str, float]:
        """Get blendshape weight values."""
        result = {}
        for attr in self.attributes:
            # Blendshape attributes typically have ".weight" or are blendshape targets
            if ".weight" in attr.name or "blendShape" in attr.name:
                result[attr.name] = attr.value
        return result

    def get_attributes_by_type(self, attr_type: str) -> Dict[str, float]:
        """Get attributes of a specific type."""
        return {a.name: a.value for a in self.attributes if a.type == attr_type}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for serialization."""
        return {
            "name": self.name,
            "category": self.category.value,
            "pose_type": self.pose_type.value,
            "state": self.state.value,
            "attributes": [{"name": a.name, "value": a.value, "type": a.type} for a in self.attributes],
            "description": self.description,
            "tags": self.tags,
            "author": self.author,
            "created": self.created,
            "modified": self.modified,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Pose":
        """Create a Pose from a dict."""
        attrs = [
            PoseAttribute(
                name=a["name"],
                value=a["value"],
                type=a.get("type", "float")
            )
            for a in data.get("attributes", [])
        ]
        return cls(
            name=data["name"],
            category=PoseCategory(data.get("category", "custom")),
            pose_type=PoseType(data.get("pose_type", "mixed")),
            state=PoseState(data.get("state", "normal")),
            attributes=attrs,
            description=data.get("description", ""),
            tags=data.get("tags", []),
            author=data.get("author", "unknown"),
            created=data.get("created", ""),
            modified=data.get("modified", ""),
            metadata=data.get("metadata", {}),
        )


@dataclass
class PoseInfo:
    """Information about a pose (without full attribute data)."""
    name: str
    category: PoseCategory
    pose_type: PoseType
    state: PoseState
    description: str
    tags: List[str]
    attribute_count: int
    created: str
    modified: str


@dataclass
class PoseReport:
    """Report of a pose operation."""
    success: bool = True
    operation: str = ""
    pose_name: str = ""
    modified_count: int = 0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)