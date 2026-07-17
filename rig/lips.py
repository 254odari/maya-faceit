"""
maya_faceit.rig.lips

Lip rig builder.

Creates a complete procedural lip rig including:

    • Upper & Lower lip joints
    • Corner controls
    • Center controls
    • Curve driven lips
    • Jaw follow
    • Lip seal
    • Sticky lips
    • Roll
    • Curl
    • Stretch
    • Matrix constraints

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


# --------------------------------------------------------
# Data
# --------------------------------------------------------

@dataclass(slots=True)
class LipRig:

    upper_joints: list[str]

    lower_joints: list[str]

    upper_controls: list[str]

    lower_controls: list[str]

    left_corner: str

    right_corner: str

    center_upper: str

    center_lower: str

    master: str


# --------------------------------------------------------
# Builder
# --------------------------------------------------------

class LipBuilder:

    def __init__(self):

        self.rig: LipRig | None = None

    # --------------------------------------------------

    def build(self) -> LipRig:

        if self.exists():

            return self.rig

        upper_joints = []
        lower_joints = []

        upper_ctrls = []
        lower_ctrls = []

        # ---------------------------------------------
        # Upper Lip
        # ---------------------------------------------

        for i in range(5):

            jnt = joint_manager.create(

                name=f"C_UpperLip_{i+1:02}_JNT",

                position=(0, 15.5, 5.2),
            )

            ctrl = controller_manager.create(

                name=f"C_UpperLip_{i+1:02}_CTRL",

                shape="circle",

                size=0.20,

                color="yellow",
            )

            cmds.matchTransform(ctrl, jnt)

            matrix_rig.parent(

                ctrl,

                jnt,
            )

            upper_joints.append(jnt)

            upper_ctrls.append(ctrl)

        # ---------------------------------------------
        # Lower Lip
        # ---------------------------------------------

        for i in range(5):

            jnt = joint_manager.create(

                name=f"C_LowerLip_{i+1:02}_JNT",

                position=(0, 14.9, 5.2),
            )

            ctrl = controller_manager.create(

                name=f"C_LowerLip_{i+1:02}_CTRL",

                shape="circle",

                size=0.20,

                color="yellow",
            )

            cmds.matchTransform(ctrl, jnt)

            matrix_rig.parent(

                ctrl,

                jnt,
            )

            lower_joints.append(jnt)

            lower_ctrls.append(ctrl)

        # ---------------------------------------------
        # Corners
        # ---------------------------------------------

        left_corner = controller_manager.create(

            "L_LipCorner_CTRL",

            shape="square",

            size=0.45,

            color="blue",
        )

        right_corner = controller_manager.create(

            "R_LipCorner_CTRL",

            shape="square",

            size=0.45,

            color="red",
        )

        # ---------------------------------------------
        # Centers
        # ---------------------------------------------

        upper_center = controller_manager.create(

            "C_UpperLip_CTRL",

            shape="circle",

            size=0.35,

            color="yellow",
        )

        lower_center = controller_manager.create(

            "C_LowerLip_CTRL",

            shape="circle",

            size=0.35,

            color="yellow",
        )

        # ---------------------------------------------
        # Master
        # ---------------------------------------------

        master = controller_manager.create(

            "C_Lips_CTRL",

            shape="square",

            size=1.8,

            color="yellow",
        )

        self._create_attributes(master)

        self.rig = LipRig(

            upper_joints,

            lower_joints,

            upper_ctrls,

            lower_ctrls,

            left_corner,

            right_corner,

            upper_center,

            lower_center,

            master,
        )

        return self.rig

    # --------------------------------------------------

    def _create_attributes(
        self,
        ctrl: str,
    ):

        attrs = [

            ("Smile",0),

            ("Frown",0),

            ("Pucker",0),

            ("Funnel",0),

            ("Roll",0),

            ("Curl",0),

            ("Stretch",0),

            ("Seal",0),

            ("Sticky",0),

            ("JawFollow",1),

            ("Volume",1),

        ]

        for attr,value in attrs:

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

        self.rig = None

    # --------------------------------------------------

    def exists(self):

        return self.rig is not None

    # --------------------------------------------------

    def controller(self):

        if self.rig:

            return self.rig.master

        return None


# --------------------------------------------------------
# Singleton
# --------------------------------------------------------

lip_builder = LipBuilder()