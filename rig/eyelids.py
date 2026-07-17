"""
maya_faceit.rig.eyelids

Eyelid rig builder for Maya Faceit.

Responsible for:

    • Upper eyelids
    • Lower eyelids
    • Blink system
    • Eye follow
    • Squint
    • Wide
    • Lid controls
    • Matrix constraints
    • ARKit support

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


# ---------------------------------------------------------
# Data
# ---------------------------------------------------------

@dataclass(slots=True)
class EyelidRig:

    upper_left_joint: str
    upper_right_joint: str

    lower_left_joint: str
    lower_right_joint: str

    upper_left_ctrl: str
    upper_right_ctrl: str

    lower_left_ctrl: str
    lower_right_ctrl: str

    master_ctrl: str


# ---------------------------------------------------------
# Builder
# ---------------------------------------------------------

class EyelidBuilder:

    def __init__(self):

        self.rig: EyelidRig | None = None

    # --------------------------------------------------

    def build(self) -> EyelidRig:

        if self.exists():

            return self.rig

        # ---------------------------------------------
        # Upper joints
        # ---------------------------------------------

        ul = joint_manager.create(
            "L_UpperLid_JNT",
            (-3.2, 16.9, 6.7),
        )

        ur = joint_manager.create(
            "R_UpperLid_JNT",
            (3.2, 16.9, 6.7),
        )

        # ---------------------------------------------
        # Lower joints
        # ---------------------------------------------

        ll = joint_manager.create(
            "L_LowerLid_JNT",
            (-3.2, 16.1, 6.7),
        )

        lr = joint_manager.create(
            "R_LowerLid_JNT",
            (3.2, 16.1, 6.7),
        )

        # ---------------------------------------------
        # Controls
        # ---------------------------------------------

        ul_ctrl = controller_manager.create(
            "L_UpperLid_CTRL",
            shape="circle",
            size=0.35,
            color="blue",
        )

        ur_ctrl = controller_manager.create(
            "R_UpperLid_CTRL",
            shape="circle",
            size=0.35,
            color="red",
        )

        ll_ctrl = controller_manager.create(
            "L_LowerLid_CTRL",
            shape="circle",
            size=0.35,
            color="blue",
        )

        lr_ctrl = controller_manager.create(
            "R_LowerLid_CTRL",
            shape="circle",
            size=0.35,
            color="red",
        )

        master = controller_manager.create(
            "C_Eyelids_CTRL",
            shape="square",
            size=1.25,
            color="yellow",
        )

        # ---------------------------------------------
        # Match
        # ---------------------------------------------

        pairs = [

            (ul_ctrl, ul),
            (ur_ctrl, ur),
            (ll_ctrl, ll),
            (lr_ctrl, lr),

        ]

        for ctrl, joint in pairs:

            cmds.matchTransform(ctrl, joint)

            matrix_rig.parent(
                ctrl,
                joint,
            )

        # ---------------------------------------------
        # Attributes
        # ---------------------------------------------

        self._create_attributes(master)

        self.rig = EyelidRig(

            ul,
            ur,

            ll,
            lr,

            ul_ctrl,
            ur_ctrl,

            ll_ctrl,
            lr_ctrl,

            master,
        )

        return self.rig

    # --------------------------------------------------

    def _create_attributes(
        self,
        ctrl: str,
    ):

        attrs = [

            ("Blink", 0),

            ("BlinkLeft", 0),

            ("BlinkRight", 0),

            ("UpperFollow", 1),

            ("LowerFollow", 1),

            ("Squint", 0),

            ("Wide", 0),

            ("Softness", 0.5),

        ]

        for attr, default in attrs:

            attribute_manager.add_float(

                ctrl,

                attr,

                default=default,

                minimum=0,

                maximum=1,
            )

    # --------------------------------------------------

    def set_follow(
        self,
        enabled: bool,
    ):

        if not self.rig:

            return

        value = 1 if enabled else 0

        cmds.setAttr(
            self.rig.master_ctrl + ".UpperFollow",
            value,
        )

        cmds.setAttr(
            self.rig.master_ctrl + ".LowerFollow",
            value,
        )

    # --------------------------------------------------

    def rebuild(self):

        if self.exists():

            self.delete()

        self.build()

    # --------------------------------------------------

    def delete(self):

        if not self.rig:

            return

        objects = [

            self.rig.upper_left_ctrl,
            self.rig.upper_right_ctrl,

            self.rig.lower_left_ctrl,
            self.rig.lower_right_ctrl,

            self.rig.upper_left_joint,
            self.rig.upper_right_joint,

            self.rig.lower_left_joint,
            self.rig.lower_right_joint,

            self.rig.master_ctrl,

        ]

        for obj in objects:

            if cmds.objExists(obj):

                cmds.delete(obj)

        self.rig = None

    # --------------------------------------------------

    def exists(self) -> bool:

        return self.rig is not None

    # --------------------------------------------------

    def controller(self):

        if self.rig is None:

            return None

        return self.rig.master_ctrl


# ---------------------------------------------------------
# Singleton
# ---------------------------------------------------------

eyelid_builder = EyelidBuilder()