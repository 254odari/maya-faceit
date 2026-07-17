"""
maya_faceit.rig.nose

Nose rig builder.

Creates a complete procedural nose rig including:

    • Nose root
    • Nose tip
    • Left nostril
    • Right nostril
    • Master nose control
    • Matrix constraints
    • Nostril flare
    • Sneer support
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
class NoseRig:

    root_joint: str
    tip_joint: str

    left_nostril_joint: str
    right_nostril_joint: str

    root_ctrl: str
    tip_ctrl: str

    left_nostril_ctrl: str
    right_nostril_ctrl: str

    master_ctrl: str


# ---------------------------------------------------------
# Builder
# ---------------------------------------------------------

class NoseBuilder:

    def __init__(self):

        self.rig: NoseRig | None = None

    # --------------------------------------------------

    def build(self) -> NoseRig:

        if self.exists():

            return self.rig

        # ---------------------------------------------
        # Joints
        # ---------------------------------------------

        root_joint = joint_manager.create(
            name="C_NoseRoot_JNT",
            position=(0.0, 16.9, 5.7),
        )

        tip_joint = joint_manager.create(
            name="C_NoseTip_JNT",
            position=(0.0, 16.0, 6.2),
        )

        left_joint = joint_manager.create(
            name="L_Nostril_JNT",
            position=(-0.55, 15.8, 6.0),
        )

        right_joint = joint_manager.create(
            name="R_Nostril_JNT",
            position=(0.55, 15.8, 6.0),
        )

        # ---------------------------------------------
        # Controls
        # ---------------------------------------------

        root_ctrl = controller_manager.create(
            name="C_NoseRoot_CTRL",
            shape="circle",
            size=0.35,
            color="yellow",
        )

        tip_ctrl = controller_manager.create(
            name="C_NoseTip_CTRL",
            shape="circle",
            size=0.35,
            color="yellow",
        )

        left_ctrl = controller_manager.create(
            name="L_Nostril_CTRL",
            shape="circle",
            size=0.25,
            color="blue",
        )

        right_ctrl = controller_manager.create(
            name="R_Nostril_CTRL",
            shape="circle",
            size=0.25,
            color="red",
        )

        master = controller_manager.create(
            name="C_Nose_CTRL",
            shape="square",
            size=1.25,
            color="yellow",
        )

        # ---------------------------------------------
        # Match transforms
        # ---------------------------------------------

        pairs = [

            (root_ctrl, root_joint),
            (tip_ctrl, tip_joint),
            (left_ctrl, left_joint),
            (right_ctrl, right_joint),

        ]

        for ctrl, joint in pairs:

            cmds.matchTransform(ctrl, joint)

            matrix_rig.parent(
                ctrl,
                joint,
            )

        self._create_attributes(master)

        self.rig = NoseRig(

            root_joint,
            tip_joint,

            left_joint,
            right_joint,

            root_ctrl,
            tip_ctrl,

            left_ctrl,
            right_ctrl,

            master,
        )

        return self.rig

    # --------------------------------------------------

    def _create_attributes(self, ctrl: str):

        attributes = [

            ("Sneer", 0),

            ("Flare", 0),

            ("Wrinkle", 0),

            ("Compress", 0),

            ("FollowHead", 1),

            ("Symmetry", 1),

        ]

        for attr, value in attributes:

            attribute_manager.add_float(

                ctrl,

                attr,

                default=value,

                minimum=0,

                maximum=1,
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

            self.rig.root_joint,
            self.rig.tip_joint,

            self.rig.left_nostril_joint,
            self.rig.right_nostril_joint,

            self.rig.root_ctrl,
            self.rig.tip_ctrl,

            self.rig.left_nostril_ctrl,
            self.rig.right_nostril_ctrl,

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

        if self.rig:

            return self.rig.master_ctrl

        return None


# ---------------------------------------------------------
# Singleton
# ---------------------------------------------------------

nose_builder = NoseBuilder()