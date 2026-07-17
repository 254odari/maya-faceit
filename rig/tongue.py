"""
maya_faceit.rig.tongue

High-level tongue rig orchestrator.

Coordinates all tongue rig modules and exposes a
single API for building, rebuilding, deleting,
validating, and managing the tongue rig.

Target
------
Maya 2026
Python 3.11
"""

from __future__ import annotations

from dataclasses import dataclass

from .tongue_chain import tongue_chain
from .tongue_controls import tongue_controls
from .tongue_attributes import tongue_attributes
from .tongue_fk import tongue_fk
from .tongue_ik import tongue_ik
from .tongue_stretch import tongue_stretch
from .tongue_volume import tongue_volume
from .tongue_blend import tongue_blend
from .tongue_visibility import tongue_visibility
from .tongue_solver import tongue_solver
from .tongue_presets import tongue_presets


# ---------------------------------------------------------
# Settings
# ---------------------------------------------------------

@dataclass(slots=True)
class TongueSettings:

    joint_count: int = 7

    enable_fk: bool = True

    enable_ik: bool = True

    enable_stretch: bool = True

    enable_volume: bool = True

    enable_visibility: bool = True

    enable_blend: bool = True

    preset: str = "Default"


# ---------------------------------------------------------
# Main Builder
# ---------------------------------------------------------

class TongueRig:

    """
    Main tongue rig builder.
    """

    def __init__(self):

        self.settings = TongueSettings()

        self.chain = None
        self.controls = None
        self.master = None

        self.fk = None
        self.ik = None

        self.stretch = None
        self.volume = None

        self.blend = None

        self.visibility = None

    # -----------------------------------------------------

    def build(self):

        # ----------------------------
        # Chain
        # ----------------------------

        self.chain = tongue_chain.build(

            joint_count=self.settings.joint_count

        )

        # ----------------------------
        # Controls
        # ----------------------------

        self.controls = tongue_controls.build(

            self.chain

        )

        self.master = self.controls.master

        # ----------------------------
        # Attributes
        # ----------------------------

        tongue_attributes.build(

            self.master

        )

        # ----------------------------
        # FK
        # ----------------------------

        if self.settings.enable_fk:

            self.fk = tongue_fk.build(

                self.chain

            )

        # ----------------------------
        # IK
        # ----------------------------

        if self.settings.enable_ik:

            self.ik = tongue_ik.build(

                self.chain

            )

        # ----------------------------
        # Stretch
        # ----------------------------

        if self.settings.enable_stretch:

            self.stretch = tongue_stretch.build(

                joints=self.chain.joints,

                curve=self.ik.curve,

                master_control=self.master,

            )

        # ----------------------------
        # Volume
        # ----------------------------

        if self.settings.enable_volume:

            self.volume = tongue_volume.build(

                joints=self.chain.joints,

                stretch_node=self.stretch.blend,

                master_control=self.master,

            )

        # ----------------------------
        # Blend
        # ----------------------------

        if self.settings.enable_blend:

            self.blend = tongue_blend.build(

                fk_joints=self.fk.joints,

                ik_joints=self.ik.joints,

                bind_joints=self.chain.joints,

                master_control=self.master,

            )

        # ----------------------------
        # Visibility
        # ----------------------------

        if self.settings.enable_visibility:

            tongue_visibility.build(

                master_control=self.master,

                fk_group=self.fk.group,

                ik_group=self.ik.group,

                curve_group=self.ik.group,

                cluster_group=self.ik.group,

                helper_group=self.controls.helper_group,

                debug_group=self.controls.debug_group,

            )

        # ----------------------------
        # Solver
        # ----------------------------

        tongue_solver.build(

            master_control=self.master,

            fk_system=self.fk,

            ik_system=self.ik,

            stretch_system=self.stretch,

            volume_system=self.volume,

            blend_system=self.blend,

        )

        return self

    # -----------------------------------------------------

    def rebuild(self):

        self.delete()

        return self.build()

    # -----------------------------------------------------

    def delete(self):

        tongue_solver.disable()

        tongue_blend.delete()

        tongue_volume.delete()

        tongue_stretch.delete()

        tongue_ik.delete()

        tongue_fk.delete()

        tongue_controls.delete()

        tongue_chain.delete()

    # -----------------------------------------------------

    def apply_preset(

        self,

        preset: str,

    ):

        tongue_presets.apply(

            preset,

            self,

        )

    # -----------------------------------------------------

    def validate(self) -> bool:

        if self.settings.joint_count < 3:

            return False

        if self.settings.joint_count > 20:

            return False

        return True

    # -----------------------------------------------------

    def show_debug(self):

        if self.visibility:

            self.visibility.show_all()

    # -----------------------------------------------------

    def hide_debug(self):

        if self.visibility:

            self.visibility.hide_all()

    # -----------------------------------------------------

    def serialize(self):

        return {

            "joint_count": self.settings.joint_count,

            "preset": self.settings.preset,

            "fk": self.settings.enable_fk,

            "ik": self.settings.enable_ik,

            "stretch": self.settings.enable_stretch,

            "volume": self.settings.enable_volume,

            "blend": self.settings.enable_blend,

        }


# ---------------------------------------------------------
# Singleton
# ---------------------------------------------------------

tongue = TongueRig()