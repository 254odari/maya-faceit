"""
maya_faceit.rig.jaw

Jaw rig builder for Maya Faceit.

Responsible for creating the complete jaw rig,
including:

    • Jaw Joint
    • Jaw Controller
    • Open / Close
    • Side
    • Forward
    • Auto Follow
    • SDK connections
    • Matrix constraints
    • Rig rebuilding

Target:
    Maya 2026
    Python 3.11
"""

from __future__ import annotations

from dataclasses import dataclass

import maya.cmds as cmds # type: ignore

from .controllers import controller_manager
from .joints import joint_manager
from .matrix_rig import matrix_rig
from .attributes import attribute_manager
from .driver_network import driver_network


# ----------------------------------------------------------
# Data
# ----------------------------------------------------------

@dataclass(slots=True)
class JawRig:

    joint: str

    controller: str

    group: str


# ----------------------------------------------------------
# Builder
# ----------------------------------------------------------

class JawBuilder:

    def __init__(self):

        self.rig: JawRig | None = None

    # --------------------------------------------------

    def build(
        self,
        position=(0.0, 14.5, 1.8),
    ) -> JawRig:
        """
        Build the jaw rig.
        """

        if self.exists():

            return self.rig

        # ---------------------------------------------
        # Joint
        # ---------------------------------------------

        joint = joint_manager.create(

            name="C_Jaw_JNT",

            position=position,
        )

        # ---------------------------------------------
        # Controller
        # ---------------------------------------------

        ctrl = controller_manager.create(

            name="C_Jaw_CTRL",

            shape="circle",

            size=2.5,

            color="yellow",
        )

        cmds.matchTransform(
            ctrl,
            joint,
        )

        grp = cmds.group(

            ctrl,

            name="C_Jaw_CTRL_GRP",
        )

        cmds.matchTransform(
            grp,
            joint,
        )

        # ---------------------------------------------
        # Matrix Parent
        # ---------------------------------------------

        matrix_rig.parent(

            "Jaw",

            ctrl,

            joint,
        )

        # ---------------------------------------------
        # Attributes
        # ---------------------------------------------

        self._create_attributes(ctrl)

        # ---------------------------------------------
        # Drivers
        # ---------------------------------------------

        self._build_driver_network(ctrl)

        # ---------------------------------------------
        # Save
        # ---------------------------------------------

        self.rig = JawRig(

            joint,

            ctrl,

            grp,
        )

        return self.rig

    # --------------------------------------------------

    def _create_attributes(
        self,
        ctrl: str,
    ):

        attrs = [

            ("Open", 0.0),

            ("Forward", 0.0),

            ("Side", 0.0),

            ("AutoFollow", 1.0),

            ("Volume", 1.0),

        ]

        for name, default in attrs:

            attribute_manager.add_float(

                ctrl,

                name,

                default=default,

                minimum=-10,

                maximum=10,
            )

    # --------------------------------------------------

    def _build_driver_network(
        self,
        ctrl: str,
    ):

        # Open

        driver_network.multiply(

            name="Jaw_Open",

            input1=f"{ctrl}.Open",

            input2=-25,

            output="C_Jaw_JNT.rotateX",
        )

        # Side

        driver_network.multiply(

            name="Jaw_Side",

            input1=f"{ctrl}.Side",

            input2=15,

            output="C_Jaw_JNT.rotateY",
        )

        # Forward

        driver_network.multiply(

            name="Jaw_Forward",

            input1=f"{ctrl}.Forward",

            input2=2,

            output="C_Jaw_JNT.translateZ",
        )

    # --------------------------------------------------

    def mirror(self):

        pass

    # --------------------------------------------------

    def rebuild(self):

        if self.rig:

            self.delete()

        self.build()

    # --------------------------------------------------

    def delete(self):

        if not self.rig:

            return

        if cmds.objExists(self.rig.group):

            cmds.delete(self.rig.group)

        if cmds.objExists(self.rig.joint):

            cmds.delete(self.rig.joint)

        self.rig = None

    # --------------------------------------------------

    def exists(self):

        return self.rig is not None

    # --------------------------------------------------

    def controller(self):

        return None if self.rig is None else self.rig.controller

    # --------------------------------------------------

    def joint(self):

        return None if self.rig is None else self.rig.joint


# ----------------------------------------------------------
# Singleton
# ----------------------------------------------------------

jaw_builder = JawBuilder()