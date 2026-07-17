"""
maya_faceit.rig.brows

Eyebrow rig builder.

Creates a complete eyebrow rig including:

    • Left / Right brow joints
    • Inner, Middle and Outer controls
    • Master brow control
    • Matrix constraints
    • Brow attributes
    • Symmetry support

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
class BrowRig:

    left_joints: list[str]
    right_joints: list[str]

    left_controls: list[str]
    right_controls: list[str]

    master: str


# ---------------------------------------------------------
# Builder
# ---------------------------------------------------------

class BrowBuilder:

    def __init__(self):

        self.rig: BrowRig | None = None

    # --------------------------------------------------

    def build(self) -> BrowRig:

        if self.exists():

            return self.rig

        left_joints = []
        right_joints = []

        left_controls = []
        right_controls = []

        regions = [

            ("Inner", 0.0),
            ("Middle", 0.7),
            ("Outer", 1.4),

        ]

        # --------------------------------------------------
        # Left Brow
        # --------------------------------------------------

        for region, offset in regions:

            joint = joint_manager.create(

                name=f"L_Brow{region}_JNT",

                position=(-2.5 - offset, 18.0, 5.8),
            )

            ctrl = controller_manager.create(

                name=f"L_Brow{region}_CTRL",

                shape="circle",

                size=0.30,

                color="blue",
            )

            cmds.matchTransform(ctrl, joint)

            matrix_rig.parent(

                ctrl,

                joint,
            )

            left_joints.append(joint)
            left_controls.append(ctrl)

        # --------------------------------------------------
        # Right Brow
        # --------------------------------------------------

        for region, offset in regions:

            joint = joint_manager.create(

                name=f"R_Brow{region}_JNT",

                position=(2.5 + offset, 18.0, 5.8),
            )

            ctrl = controller_manager.create(

                name=f"R_Brow{region}_CTRL",

                shape="circle",

                size=0.30,

                color="red",
            )

            cmds.matchTransform(ctrl, joint)

            matrix_rig.parent(

                ctrl,

                joint,
            )

            right_joints.append(joint)
            right_controls.append(ctrl)

        # --------------------------------------------------
        # Master Control
        # --------------------------------------------------

        master = controller_manager.create(

            name="C_Brows_CTRL",

            shape="square",

            size=2.0,

            color="yellow",
        )

        self._create_attributes(master)

        self.rig = BrowRig(

            left_joints,
            right_joints,

            left_controls,
            right_controls,

            master,
        )

        return self.rig

    # --------------------------------------------------

    def _create_attributes(
        self,
        ctrl: str,
    ):

        attributes = [

            ("Raise", 0),

            ("Lower", 0),

            ("InnerUp", 0),

            ("OuterUp", 0),

            ("Compress", 0),

            ("Spread", 0),

            ("FollowHead", 1),

            ("Symmetry", 1),

        ]

        for name, value in attributes:

            attribute_manager.add_float(

                ctrl,

                name,

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

        objects = (

            self.rig.left_joints
            + self.rig.right_joints
            + self.rig.left_controls
            + self.rig.right_controls
            + [self.rig.master]
        )

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

            return self.rig.master

        return None


# ---------------------------------------------------------
# Singleton
# ---------------------------------------------------------

brow_builder = BrowBuilder()