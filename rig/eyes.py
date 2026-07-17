"""
maya_faceit.rig.eyes

Eye rig builder.

Creates the complete eye rig including:

    • Left Eye
    • Right Eye
    • Eye Aim Controls
    • Master Eye Control
    • Matrix Constraints
    • Look At
    • Auto Follow
    • Space Switching

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


# ----------------------------------------------------------
# Data
# ----------------------------------------------------------

@dataclass(slots=True)
class EyeRig:

    left_joint: str
    right_joint: str

    left_ctrl: str
    right_ctrl: str

    master_ctrl: str

    left_aim: str
    right_aim: str


# ----------------------------------------------------------
# Builder
# ----------------------------------------------------------

class EyesBuilder:

    def __init__(self):

        self.rig: EyeRig | None = None

    # --------------------------------------------------

    def build(self) -> EyeRig:

        if self.exists():

            return self.rig

        # --------------------------------------------------
        # Joints
        # --------------------------------------------------

        left_joint = joint_manager.create(

            name="L_Eye_JNT",

            position=(-3.2, 16.5, 6.8),
        )

        right_joint = joint_manager.create(

            name="R_Eye_JNT",

            position=(3.2, 16.5, 6.8),
        )

        # --------------------------------------------------
        # Eye Controls
        # --------------------------------------------------

        left_ctrl = controller_manager.create(

            name="L_Eye_CTRL",

            shape="circle",

            size=0.8,

            color="blue",
        )

        right_ctrl = controller_manager.create(

            name="R_Eye_CTRL",

            shape="circle",

            size=0.8,

            color="red",
        )

        # --------------------------------------------------
        # Aim Controls
        # --------------------------------------------------

        left_aim = controller_manager.create(

            name="L_EyeAim_CTRL",

            shape="square",

            size=0.4,

            color="cyan",
        )

        right_aim = controller_manager.create(

            name="R_EyeAim_CTRL",

            shape="square",

            size=0.4,

            color="cyan",
        )

        # --------------------------------------------------
        # Master Control
        # --------------------------------------------------

        master = controller_manager.create(

            name="C_Eyes_CTRL",

            shape="square",

            size=2.5,

            color="yellow",
        )

        # --------------------------------------------------
        # Match Positions
        # --------------------------------------------------

        cmds.matchTransform(left_ctrl, left_joint)
        cmds.matchTransform(right_ctrl, right_joint)

        cmds.matchTransform(left_aim, left_joint)
        cmds.matchTransform(right_aim, right_joint)

        # Move aim controls forward

        cmds.move(
            4,
            left_aim,
            z=True,
            relative=True,
        )

        cmds.move(
            4,
            right_aim,
            z=True,
            relative=True,
        )

        # --------------------------------------------------
        # Matrix Constraints
        # --------------------------------------------------

        matrix_rig.parent(

            "LeftEye",

            left_ctrl,

            left_joint,
        )

        matrix_rig.parent(

            "RightEye",

            right_ctrl,

            right_joint,
        )

        # --------------------------------------------------
        # Attributes
        # --------------------------------------------------

        self._create_attributes(master)

        # --------------------------------------------------

        self.rig = EyeRig(

            left_joint,

            right_joint,

            left_ctrl,

            right_ctrl,

            master,

            left_aim,

            right_aim,
        )

        return self.rig

    # --------------------------------------------------

    def _create_attributes(
        self,
        ctrl: str,
    ):

        attrs = [

            ("FollowHead", 1),

            ("LookAt", 1),

            ("Convergence", 0),

            ("Divergence", 0),

            ("Blink", 0),

            ("UpperLidFollow", 1),

            ("LowerLidFollow", 1),

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

    def rebuild(self):

        if self.rig:

            self.delete()

        self.build()

    # --------------------------------------------------

    def delete(self):

        if not self.rig:

            return

        objects = [

            self.rig.left_ctrl,

            self.rig.right_ctrl,

            self.rig.left_joint,

            self.rig.right_joint,

            self.rig.left_aim,

            self.rig.right_aim,

            self.rig.master_ctrl,

        ]

        for obj in objects:

            if cmds.objExists(obj):

                cmds.delete(obj)

        self.rig = None

    # --------------------------------------------------

    def exists(self):

        return self.rig is not None

    # --------------------------------------------------

    def controller(self):

        if self.rig is None:

            return None

        return self.rig.master_ctrl


# ----------------------------------------------------------
# Singleton
# ----------------------------------------------------------

eyes_builder = EyesBuilder()