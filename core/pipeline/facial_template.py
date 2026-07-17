"""
core/pipeline/facial_template.py

Facial rig template definitions.

This module defines the logical structure of the facial rig.
The Rig Builder uses these templates to automatically generate
controllers, joints, constraints, and blendshape mappings.

Author: Maya FaceIT Team
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..logging.logger import log


# ---------------------------------------------------------
# Controller Definition
# ---------------------------------------------------------

@dataclass(slots=True)
class ControllerTemplate:
    """Template for a rig controller."""
    name: str
    region: str
    parent: Optional[str] = None
    shape: str = "circle"
    color: str = "yellow"
    size: float = 1.0
    mirror: bool = False


# ---------------------------------------------------------
# Joint Definition
# ---------------------------------------------------------

@dataclass(slots=True)
class JointTemplate:
    """Template for a rig joint."""
    name: str
    region: str
    parent: Optional[str] = None
    mirror: bool = False


# ---------------------------------------------------------
# Facial Region
# ---------------------------------------------------------

@dataclass(slots=True)
class FacialRegion:
    """A collection of controllers and joints for a facial region."""
    name: str
    controllers: List[ControllerTemplate] = field(default_factory=list)
    joints: List[JointTemplate] = field(default_factory=list)


# ---------------------------------------------------------
# Facial Template
# ---------------------------------------------------------

class FacialTemplate:
    """
    Complete facial rig template.

    Contains regions, controllers, and joints defining the entire rig structure.
    """

    def __init__(self):
        self.regions: Dict[str, FacialRegion] = {}

    def add_region(self, region: FacialRegion) -> None:
        """Add a facial region to the template."""
        self.regions[region.name] = region
        log.debug(f"Added facial region: {region.name}")

    def region(self, name: str) -> Optional[FacialRegion]:
        """Get a region by name."""
        return self.regions.get(name)

    def controller_count(self) -> int:
        """Total number of controllers across all regions."""
        return sum(len(r.controllers) for r in self.regions.values())

    def joint_count(self) -> int:
        """Total number of joints across all regions."""
        return sum(len(r.joints) for r in self.regions.values())

    def all_controllers(self) -> List[ControllerTemplate]:
        """Get all controllers from all regions."""
        data = []
        for region in self.regions.values():
            data.extend(region.controllers)
        return data

    def all_joints(self) -> List[JointTemplate]:
        """Get all joints from all regions."""
        data = []
        for region in self.regions.values():
            data.extend(region.joints)
        return data


# ---------------------------------------------------------
# Default Template
# ---------------------------------------------------------

def create_default_template() -> FacialTemplate:
    """Create a default facial rig template with common regions."""
    template = FacialTemplate()

    # Eyes
    eyes = FacialRegion("Eyes")
    eyes.controllers.extend([
        ControllerTemplate("L_eye_ctrl", "Eyes", mirror=True, color="blue"),
        ControllerTemplate("R_eye_ctrl", "Eyes", mirror=True, color="red"),
    ])
    eyes.joints.extend([
        JointTemplate("L_eye_jnt", "Eyes", mirror=True),
        JointTemplate("R_eye_jnt", "Eyes", mirror=True),
    ])
    template.add_region(eyes)

    # Jaw
    jaw = FacialRegion("Jaw")
    jaw.controllers.append(
        ControllerTemplate("jaw_ctrl", "Jaw", color="yellow")
    )
    jaw.joints.append(
        JointTemplate("jaw_jnt", "Jaw")
    )
    template.add_region(jaw)

    # Brows
    brows = FacialRegion("Brows")
    brows.controllers.extend([
        ControllerTemplate("L_brow_ctrl", "Brows", mirror=True, color="blue"),
        ControllerTemplate("R_brow_ctrl", "Brows", mirror=True, color="red"),
    ])
    template.add_region(brows)

    # Lips
    lips = FacialRegion("Lips")
    lips.controllers.append(
        ControllerTemplate("mouth_ctrl", "Lips", color="yellow")
    )
    template.add_region(lips)

    return template


# ---------------------------------------------------------
# Singleton
# ---------------------------------------------------------

facial_template = create_default_template()