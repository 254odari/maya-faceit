"""
maya_faceit.rig.tongue_volume

Automatic tongue volume preservation.

Maintains believable tongue thickness during
stretch and squash operations.

Target
------
Maya 2026
Python 3.11
"""

from __future__ import annotations

from dataclasses import dataclass, field

import math
import maya.cmds as cmds


# ------------------------------------------------------------
# Data
# ------------------------------------------------------------

@dataclass(slots=True)
class TongueVolumeRig:

    nodes: list[str] = field(default_factory=list)

    joints: list[str] = field(default_factory=list)

    enabled: bool = True

    algorithm: str = "sqrt"


# ------------------------------------------------------------
# Builder
# ------------------------------------------------------------

class TongueVolumeBuilder:

    def __init__(self):

        self.rig = TongueVolumeRig()

    # -----------------------------------------------------

    def build(

        self,

        joints: list[str],

        stretch_node: str,

        master_control: str,

    ) -> TongueVolumeRig:

        self.delete()

        self.rig.joints = joints

        count = len(joints)

        for index, joint in enumerate(joints[:-1]):

            weight = self._weight(

                index,

                count,

            )

            volume = cmds.createNode(

                "multiplyDivide",

                name=f"{joint}_Volume_MD",

            )

            cmds.setAttr(

                volume + ".operation",

                3,

            )

            cmds.connectAttr(

                stretch_node + ".outputR",

                volume + ".input1X",

                force=True,

            )

            cmds.setAttr(

                volume + ".input2X",

                0.5,

            )

            power = cmds.createNode(

                "multiplyDivide",

                name=f"{joint}_Weight_MD",

            )

            cmds.connectAttr(

                volume + ".outputX",

                power + ".input1X",

                force=True,

            )

            cmds.setAttr(

                power + ".input2X",

                weight,

            )

            reverse = cmds.createNode(

                "plusMinusAverage",

                name=f"{joint}_Reverse_PMA",

            )

            cmds.setAttr(

                reverse + ".operation",

                2,

            )

            cmds.setAttr(

                reverse + ".input1D[0]",

                2,

            )

            cmds.connectAttr(

                power + ".outputX",

                reverse + ".input1D[1]",

                force=True,

            )

            blend = cmds.createNode(

                "blendColors",

                name=f"{joint}_Volume_BC",

            )

            cmds.connectAttr(

                reverse + ".output1D",

                blend + ".color1R",

                force=True,

            )

            cmds.setAttr(

                blend + ".color2R",

                1,

            )

            cmds.connectAttr(

                master_control + ".volume",

                blend + ".blender",

                force=True,

            )

            cmds.connectAttr(

                blend + ".outputR",

                joint + ".scaleY",

                force=True,

            )

            cmds.connectAttr(

                blend + ".outputR",

                joint + ".scaleZ",

                force=True,

            )

            self.rig.nodes.extend(

                [

                    volume,

                    power,

                    reverse,

                    blend,

                ]

            )

        return self.rig

    # -----------------------------------------------------

    def enable(

        self,

        state: bool,

    ):

        self.rig.enabled = state

    # -----------------------------------------------------

    def set_algorithm(

        self,

        algorithm: str,

    ):

        self.rig.algorithm = algorithm

    # -----------------------------------------------------

    def delete(self):

        for node in self.rig.nodes:

            if cmds.objExists(node):

                cmds.delete(node)

        self.rig = TongueVolumeRig()

    # -----------------------------------------------------

    @staticmethod

    def _weight(

        index: int,

        count: int,

    ) -> float:

        if count <= 1:

            return 1.0

        t = index / (count - 1)

        return 0.15 + (0.85 * math.sqrt(t))


# ------------------------------------------------------------
# Singleton
# ------------------------------------------------------------

tongue_volume = TongueVolumeBuilder()