"""
maya_faceit.rig.cheeks

Cheek rig builder.

Responsible for:

    • Left / Right cheek joints
    • Upper and lower cheek controls
    • Smile support
    • Puff support
    • Squint support
    • Jaw follow
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
class CheekRig:

    left_upper_joint: str
    right_upper_joint: str

    left_lower_joint: str
    right_lower_joint: str

    left_upper_ctrl: str
    right_upper_ctrl: str

    left_lower_ctrl: str
    right_lower_ctrl: str

    master_ctrl: str


# ---------------------------------------------------------
# Builder
# ---------------------------------------------------------

class CheekBuilder:

    def __init__(self):

        self.rig: CheekRig | None = None

    # --------------------------------------------------

    def build(self) -> CheekRig:

        if self.exists():

            return self.rig

        # --------------------------------------------------
        # Joints
        # --------------------------------------------------

        lu_joint = joint_manager.create(

            name="L_UpperCheek_JNT",

            position=(-3.6, 15.8, 5.5),
        )

        ru_joint = joint_manager.create(

            name="R_UpperCheek_JNT",

            position=(3.6, 15.8, 5.5),
        )

        ll_joint = joint_manager.create(

            name="L_LowerCheek_JNT",

            position=(-3.8, 14.8, 5.2),
        )

        rl_joint = joint_manager.create(

            name="R_LowerCheek_JNT",

            position=(3.8, 14.8, 5.2),
        )

        # --------------------------------------------------
        # Controls
        # --------------------------------------------------

        lu_ctrl = controller_manager.create(

            name="L_UpperCheek_CTRL",

            shape="circle",

            size=0.35,

            color="blue",
        )

        ru_ctrl = controller_manager.create(

            name="R_UpperCheek_CTRL",

            shape="circle",

            size=0.35,

            color="red",
        )

        ll_ctrl = controller_manager.create(

            name="L_LowerCheek_CTRL",

            shape="circle",

            size=0.35,

            color="blue",
        )

        rl_ctrl = controller_manager.create(

            name="R_LowerCheek_CTRL",

            shape="circle",

            size=0.35,

            color="red",
        )

        master = controller_manager.create(

            name="C_Cheeks_CTRL",

            shape="square",

            size=1.8,

            color="yellow",
        )

        # --------------------------------------------------
        # Match transforms
        # --------------------------------------------------

        pairs = [

            (lu_ctrl, lu_joint),
            (ru_ctrl, ru_joint),
            (ll_ctrl, ll_joint),
            (rl_ctrl, rl_joint),

        ]

        for ctrl, joint in pairs:

            cmds.matchTransform(ctrl, joint)

            matrix_rig.parent(

                ctrl,

                joint,
            )

        self._create_attributes(master)

        self.rig = CheekRig(

            lu_joint,
            ru_joint,

            ll_joint,
            rl_joint,

            lu_ctrl,
            ru_ctrl,

            ll_ctrl,
            rl_ctrl,

            master,
        )

        return self.rig

    # --------------------------------------------------

    def _create_attributes(
        self,
        ctrl: str,
    ):

        attributes = [

            ("Puff", 0),

            ("Squint", 0),

            ("SmileFollow", 1),

            ("JawFollow", 1),

            ("Volume", 1),

            ("Compress", 0),

            ("Stretch", 0),

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

        objects = [

            self.rig.left_upper_joint,
            self.rig.right_upper_joint,

            self.rig.left_lower_joint,
            self.rig.right_lower_joint,

            self.rig.left_upper_ctrl,
            self.rig.right_upper_ctrl,

            self.rig.left_lower_ctrl,
            self.rig.right_lower_ctrl,

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

cheek_builder = CheekBuilder()