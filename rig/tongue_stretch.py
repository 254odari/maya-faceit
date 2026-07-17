"""
maya_faceit.rig.tongue_stretch

Procedural tongue stretch and squash system.

Creates a spline-based stretch network that supports
automatic stretching, squash, and animator controls.

Target
------
Maya 2026
Python 3.11
"""

from __future__ import annotations

from dataclasses import dataclass, field

import maya.cmds as cmds


# ---------------------------------------------------------
# Data
# ---------------------------------------------------------

@dataclass(slots=True)
class TongueStretchRig:

    curve_info: str | None = None

    multiply: str | None = None

    divide: str | None = None

    condition: str | None = None

    blend: str | None = None

    rest_length: float = 0.0

    joints: list[str] = field(default_factory=list)


# ---------------------------------------------------------
# Builder
# ---------------------------------------------------------

class TongueStretchBuilder:

    def __init__(self):

        self.rig = TongueStretchRig()

    # -----------------------------------------------------

    def build(

        self,

        joints: list[str],

        curve: str,

        master_control: str,

    ) -> TongueStretchRig:

        self.delete()

        self.rig.joints = joints

        curve_shape = cmds.listRelatives(

            curve,

            shapes=True,

            fullPath=True,

        )[0]

        curve_info = cmds.createNode(

            "curveInfo",

            name="Tongue_CurveInfo",

        )

        cmds.connectAttr(

            curve_shape + ".worldSpace[0]",

            curve_info + ".inputCurve",

            force=True,

        )

        rest_length = cmds.getAttr(

            curve_info + ".arcLength"

        )

        self.rig.rest_length = rest_length

        divide = cmds.createNode(

            "multiplyDivide",

            name="Tongue_Stretch_Divide",

        )

        cmds.setAttr(

            divide + ".operation",

            2,

        )

        cmds.connectAttr(

            curve_info + ".arcLength",

            divide + ".input1X",

            force=True,

        )

        cmds.setAttr(

            divide + ".input2X",

            rest_length,

        )

        blend = cmds.createNode(

            "blendColors",

            name="Tongue_Stretch_Blend",

        )

        cmds.setAttr(

            blend + ".color2R",

            1.0,

        )

        cmds.connectAttr(

            divide + ".outputX",

            blend + ".color1R",

            force=True,

        )

        cmds.connectAttr(

            master_control + ".autoStretch",

            blend + ".blender",

            force=True,

        )

        for joint in joints[:-1]:

            cmds.connectAttr(

                blend + ".outputR",

                joint + ".scaleX",

                force=True,

            )

        self.rig.curve_info = curve_info

        self.rig.divide = divide

        self.rig.blend = blend

        return self.rig

    # -----------------------------------------------------

    def enable(self, state: bool):

        if not self.rig.blend:

            return

        cmds.setAttr(

            self.rig.blend + ".blender",

            state,

        )

    # -----------------------------------------------------

    def disable(self):

        self.enable(False)

    # -----------------------------------------------------

    def delete(self):

        for node in (

            self.rig.curve_info,

            self.rig.divide,

            self.rig.multiply,

            self.rig.condition,

            self.rig.blend,

        ):

            if node and cmds.objExists(node):

                cmds.delete(node)

        self.rig = TongueStretchRig()


# ---------------------------------------------------------
# Singleton
# ---------------------------------------------------------

tongue_stretch = TongueStretchBuilder()