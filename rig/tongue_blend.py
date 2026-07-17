"""
maya_faceit.rig.tongue_blend

FK / IK blending system for the tongue rig.

Uses blendMatrix and offsetParentMatrix for
high-performance matrix-based blending.

Target
------
Maya 2026
Python 3.11
"""

from __future__ import annotations

from dataclasses import dataclass, field

import maya.cmds as cmds # type: ignore


# ------------------------------------------------------------
# Data
# ------------------------------------------------------------

@dataclass(slots=True)
class BlendNode:

    bind_joint: str

    blend_matrix: str

    mult_matrix: str | None = None


@dataclass(slots=True)
class TongueBlendRig:

    nodes: list[str] = field(default_factory=list)

    blends: list[BlendNode] = field(default_factory=list)

    built: bool = False


# ------------------------------------------------------------
# Builder
# ------------------------------------------------------------

class TongueBlendBuilder:

    def __init__(self):

        self.rig = TongueBlendRig()

    # -----------------------------------------------------

    def build(

        self,

        fk_joints: list[str],

        ik_joints: list[str],

        bind_joints: list[str],

        master_control: str,

    ) -> TongueBlendRig:

        self.delete()

        count = min(

            len(fk_joints),

            len(ik_joints),

            len(bind_joints),

        )

        for i in range(count):

            blend = cmds.createNode(

                "blendMatrix",

                name=f"{bind_joints[i]}_BlendMatrix",

            )

            cmds.connectAttr(

                fk_joints[i] + ".worldMatrix[0]",

                blend + ".inputMatrix",

                force=True,

            )

            cmds.connectAttr(

                ik_joints[i] + ".worldMatrix[0]",

                blend + ".target[0].targetMatrix",

                force=True,

            )

            cmds.connectAttr(

                master_control + ".fkIkBlend",

                blend + ".target[0].weight",

                force=True,

            )

            cmds.connectAttr(

                blend + ".outputMatrix",

                bind_joints[i] + ".offsetParentMatrix",

                force=True,

            )

            self.rig.nodes.append(blend)

            self.rig.blends.append(

                BlendNode(

                    bind_joint=bind_joints[i],

                    blend_matrix=blend,

                )

            )

        self._connect_visibility(

            master_control,

        )

        self.rig.built = True

        return self.rig

    # -----------------------------------------------------

    def _connect_visibility(

        self,

        master_control: str,

    ):

        if not cmds.attributeQuery(

            "fkControls",

            node=master_control,

            exists=True,

        ):

            cmds.addAttr(

                master_control,

                longName="fkControls",

                attributeType="bool",

                defaultValue=True,

                keyable=True,

            )

        if not cmds.attributeQuery(

            "ikControls",

            node=master_control,

            exists=True,

        ):

            cmds.addAttr(

                master_control,

                longName="ikControls",

                attributeType="bool",

                defaultValue=True,

                keyable=True,

            )

    # -----------------------------------------------------

    def set_blend(

        self,

        value: float,

        master_control: str,

    ):

        value = max(

            0.0,

            min(

                1.0,

                value,

            ),

        )

        cmds.setAttr(

            master_control + ".fkIkBlend",

            value,

        )

    # -----------------------------------------------------

    def delete(self):

        for node in self.rig.nodes:

            if cmds.objExists(node):

                cmds.delete(node)

        self.rig = TongueBlendRig()


# ------------------------------------------------------------
# Singleton
# ------------------------------------------------------------

tongue_blend = TongueBlendBuilder()