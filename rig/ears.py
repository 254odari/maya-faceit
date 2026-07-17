"""
maya_faceit.rig.ears

Ear rig builder.

Creates:

    • Left ear rig
    • Right ear rig
    • Root and tip joints
    • Ear controls
    • Master ear control
    • Matrix-driven connections

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
class EarRig:

    left_root_joint: str
    left_tip_joint: str

    right_root_joint: str
    right_tip_joint: str

    left_ctrl: str
    right_ctrl: str

    master_ctrl: str


# ---------------------------------------------------------
# Builder
# ---------------------------------------------------------

class EarBuilder:

    def __init__(self):

        self.rig: EarRig | None = None

    # --------------------------------------------------

    def build(self) -> EarRig:

        if self.exists():
            return self.rig

        # --------------------------------------------------
        # Left joints
        # --------------------------------------------------

        left_root = joint_manager.create(
            name="L_EarRoot_JNT",
            position=(-6.0, 15.9, -0.4),
        )

        left_tip = joint_manager.create(
            name="L_EarTip_JNT",
            position=(-6.7, 16.2, -0.3),
        )

        cmds.parent(left_tip, left_root)

        # --------------------------------------------------
        # Right joints
        # --------------------------------------------------

        right_root = joint_manager.create(
            name="R_EarRoot_JNT",
            position=(6.0, 15.9, -0.4),
        )

        right_tip = joint_manager.create(
            name="R_EarTip_JNT",
            position=(6.7, 16.2, -0.3),
        )

        cmds.parent(right_tip, right_root)

        # --------------------------------------------------
        # Controls
        # --------------------------------------------------

        left_ctrl = controller_manager.create(
            name="L_Ear_CTRL",
            shape="circle",
            size=0.45,
            color="blue",
        )

        right_ctrl = controller_manager.create(
            name="R_Ear_CTRL",
            shape="circle",
            size=0.45,
            color="red",
        )

        master = controller_manager.create(
            name="C_Ears_CTRL",
            shape="square",
            size=1.4,
            color="yellow",
        )

        cmds.matchTransform(left_ctrl, left_root)
        cmds.matchTransform(right_ctrl, right_root)

        matrix_rig.parent(left_ctrl, left_root)
        matrix_rig.parent(right_ctrl, right_root)

        self._create_attributes(master)

        self.rig = EarRig(

            left_root,
            left_tip,

            right_root,
            right_tip,

            left_ctrl,
            right_ctrl,

            master,
        )

        return self.rig

    # --------------------------------------------------

    def _create_attributes(self, ctrl: str):

        attrs = [

            ("EarFlop", 0),

            ("EarRotate", 0),

            ("FollowHead", 1),

            ("FollowJaw", 0),

            ("SecondaryMotion", 1),

            ("Symmetry", 1),

        ]

        for name, value in attrs:

            attribute_manager.add_float(

                ctrl,

                name,

                default=value,

               minimum=0,

                maximum=1,
            )

    # --------------------------------------------------

    def rebuild(self):

        self.delete()
        return self.build()

    # --------------------------------------------------

    def delete(self):

        if not self.rig:
            return

        objects = [

            self.rig.left_root_joint,
            self.rig.left_tip_joint,

            self.rig.right_root_joint,
            self.rig.right_tip_joint,

            self.rig.left_ctrl,
            self.rig.right_ctrl,

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

        if self.rig:
            return self.rig.master_ctrl

        return None


# ---------------------------------------------------------
# Singleton
# ---------------------------------------------------------

ear_builder = EarBuilder()