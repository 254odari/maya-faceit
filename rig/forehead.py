"""
maya_faceit.rig.forehead

High-level forehead rig module.

Coordinates construction and management of the
forehead rig.

Target
------
Maya 2026
Python 3.11
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional


# ------------------------------------------------------------
# Settings
# ------------------------------------------------------------

@dataclass(slots=True)
class ForeheadSettings:

    joint_count: int = 7

    enable_wrinkles: bool = True

    enable_skin_slide: bool = True

    enable_stretch: bool = True

    enable_squash: bool = True

    enable_volume: bool = True

    mirror: bool = True

    control_scale: float = 1.0

    preset: str = "Default"


# ------------------------------------------------------------
# Rig State
# ------------------------------------------------------------

@dataclass(slots=True)
class ForeheadRigState:

    built: bool = False

    joints: list[str] | None = None

    controls: list[str] | None = None

    groups: list[str] | None = None


# ------------------------------------------------------------
# Builder
# ------------------------------------------------------------

class ForeheadRig:

    """
    Main forehead rig builder.

    This module orchestrates the forehead subsystem.
    Individual builders are implemented in dedicated
    modules.
    """

    def __init__(self):

        self.settings = ForeheadSettings()

        self.state = ForeheadRigState()

    # --------------------------------------------------------

    def build(self):

        """
        Build complete forehead rig.
        """

        print("Building forehead rig...")

        self.state.built = True

        return self

    # --------------------------------------------------------

    def rebuild(self):

        self.delete()

        return self.build()

    # --------------------------------------------------------

    def delete(self):

        print("Deleting forehead rig...")

        self.state = ForeheadRigState()

    # --------------------------------------------------------

    def validate(self) -> bool:

        if self.settings.joint_count < 5:

            return False

        if self.settings.joint_count > 11:

            return False

        return True

    # --------------------------------------------------------

    def mirror(self):

        print("Mirroring forehead rig...")

    # --------------------------------------------------------

    def apply_preset(

        self,

        preset: str,

    ):

        self.settings.preset = preset

    # --------------------------------------------------------

    def serialize(self):

        return asdict(self.settings)

    # --------------------------------------------------------

    @property
    def built(self):

        return self.state.built


# ------------------------------------------------------------
# Singleton
# ------------------------------------------------------------

forehead = ForeheadRig()