# ui/models/rig_model.py

"""
ui/models/rig_model.py

Rig data model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class RigController:
    """A controller in the rig."""
    name: str
    shape: str = "circle"
    radius: float = 2.5
    color: str = "blue"
    locked_channels: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RigJoint:
    """A joint in the rig."""
    name: str
    parent: Optional[str] = None
    position: tuple = (0.0, 0.0, 0.0)
    rotation: tuple = (0.0, 0.0, 0.0)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RigModel:
    """Represents a facial rig."""
    name: str
    mesh: str = ""
    joint_prefix: str = "face_"
    controllers: List[RigController] = field(default_factory=list)
    joints: List[RigJoint] = field(default_factory=list)
    blendshape_node: Optional[str] = None
    template: str = "Default"
    is_built: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_statistics(self) -> Dict[str, int]:
        return {
            "joints": len(self.joints),
            "controllers": len(self.controllers),
            "blendshapes": 0,  # Will be populated from blendshape node
        }