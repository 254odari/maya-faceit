"""
maya_faceit.rig.neck

High-level neck rig orchestrator.

Coordinates construction and management of the
neck subsystem.

Target
------
Maya 2026
Python 3.11
"""

from __future__ import annotations

from dataclasses import dataclass, asdict


# ------------------------------------------------------------
# Settings
# ------------------------------------------------------------

@dataclass(slots=True)
class NeckSettings:

    joint_count: int = 5

    enable_fk: bool = True

    enable_ik: bool = True

    enable_stretch: bool = True

    enable_squash: bool = True

    enable_volume: bool = True

    enable_twist: bool = True

    enable_spaces: bool = True

    enable_throat: bool = True

    enable_adams_apple: bool = True

    enable_swallow: bool = True

    enable_mocap: bool = True

    control_scale: float = 1.0

    preset: str = "Default"


# ------------------------------------------------------------
# Runtime State
# ------------------------------------------------------------

@dataclass(slots=True)
class NeckRigState:

    built: bool = False

    joints: list[str] | None = None

    controls: list[str] | None = None

    groups: list[str] | None = None


# ------------------------------------------------------------
# Builder
# ------------------------------------------------------------

class NeckRig:
    """
    High-level neck rig.

    This module coordinates all neck subsystems.

    Individual rigging logic is implemented in
    dedicated neck modules.
    """

    def __init__(self):

        self.settings = NeckSettings()

        self.state = NeckRigState()

    # -----------------------------------------------------

    def build(self):

        """
        Build the complete neck rig.
        """

        print("Building neck rig...")

        #
        # Future modules
        #
        # neck_chain.build()
        # neck_controls.build()
        # neck_attributes.build()
        # neck_fk.build()
        # neck_ik.build()
        # neck_stretch.build()
        # neck_volume.build()
        # neck_twist.build()
        # neck_spaces.build()
        # throat.build()
        # adams_apple.build()
        # swallow.build()
        # neck_visibility.build()
        # neck_solver.build()
        #

        self.state.built = True

        return self

    # -----------------------------------------------------

    def rebuild(self):

        self.delete()

        return self.build()

    # -----------------------------------------------------

    def delete(self):

        print("Deleting neck rig...")

        self.state = NeckRigState()

    # -----------------------------------------------------

    def validate(self) -> bool:

        if self.settings.joint_count < 3:
            return False

        if self.settings.joint_count > 9:
            return False

        return True

    # -----------------------------------------------------

    def apply_preset(

        self,

        preset: str,

    ):

        self.settings.preset = preset

    # -----------------------------------------------------

    def serialize(self):

        return asdict(self.settings)

    # -----------------------------------------------------

    @property
    def built(self):

        return self.state.built


# ------------------------------------------------------------
# Singleton
# ------------------------------------------------------------

neck = NeckRig()