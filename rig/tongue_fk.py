"""
maya_faceit.rig.tongue_fk

FK tongue rig builder.

Builds a complete animator-friendly FK rig
from a tongue joint chain.

Target
------
Maya 2026
Python 3.11
"""

from __future__ import annotations

from dataclasses import dataclass, field

import maya.cmds as cmds # type: ignore

from .tongue_chain import TongueChain
from .tongue_controls import (
    tongue_controls,
    ControlData,
)


# ------------------------------------------------------------
# Data
# ------------------------------------------------------------

@dataclass(slots=True)
class TongueFKRig:

    controls: list[ControlData] = field(default_factory=list)

    joints: list[str] = field(default_factory=list)

    group: str | None = None


# ------------------------------------------------------------
# Builder
# ------------------------------------------------------------

class TongueFKBuilder:

    def __init__(self):

        self.rig = TongueFKRig()

    # ------------------------------------------------------

    def build(
        self,
        chain: TongueChain,
    ) -> TongueFKRig:

        self.delete()

        group = cmds.group(
            empty=True,
            name="Tongue_FK_GRP",
        )

        controls = tongue_controls.create_fk(
            chain.joints,
        )

        self._parent_controls(controls)

        self._connect_controls(
            controls,
            chain.joints,
        )

        if controls:

            cmds.parent(
                controls[0].zero,
                group,
            )

        self.rig.controls = controls
        self.rig.joints = chain.joints
        self.rig.group = group

        return self.rig

    # ------------------------------------------------------

    def delete(self):

        if (
            self.rig.group
            and cmds.objExists(self.rig.group)
        ):
            cmds.delete(self.rig.group)

        self.rig = TongueFKRig()

    # ------------------------------------------------------

    def controls(self):

        return self.rig.controls

    # ------------------------------------------------------

    def joints(self):

        return self.rig.joints

    # ------------------------------------------------------

    def set_visibility(
        self,
        visible: bool,
    ):

        tongue_controls.set_fk_visibility(
            visible,
        )

    # ------------------------------------------------------
    # Internal
    # ------------------------------------------------------

    def _parent_controls(
        self,
        controls: list[ControlData],
    ):

        for parent, child in zip(
            controls[:-1],
            controls[1:],
        ):

            cmds.parent(
                child.zero,
                parent.control,
            )

    # ------------------------------------------------------

    def _connect_controls(
        self,
        controls: list[ControlData],
        joints: list[str],
    ):

        for ctrl, joint in zip(
            controls,
            joints,
        ):

            self._connect_matrix(
                ctrl.control,
                joint,
            )

    # ------------------------------------------------------

    @staticmethod
    def _connect_matrix(
        control: str,
        joint: str,
    ):

        mult = cmds.createNode(
            "multMatrix",
            name=f"{joint}_MM",
        )

        decomp = cmds.createNode(
            "decomposeMatrix",
            name=f"{joint}_DCM",
        )

        cmds.connectAttr(
            control + ".worldMatrix[0]",
            mult + ".matrixIn[0]",
            force=True,
        )

        parent = cmds.listRelatives(
            joint,
            parent=True,
        )

        if parent:

            cmds.connectAttr(
                parent[0] + ".worldInverseMatrix[0]",
                mult + ".matrixIn[1]",
                force=True,
            )

        cmds.connectAttr(
            mult + ".matrixSum",
            decomp + ".inputMatrix",
            force=True,
        )

        cmds.connectAttr(
            decomp + ".outputTranslate",
            joint + ".translate",
            force=True,
        )

        cmds.connectAttr(
            decomp + ".outputRotate",
            joint + ".rotate",
            force=True,
        )

        cmds.connectAttr(
            decomp + ".outputScale",
            joint + ".scale",
            force=True,
        )


# ------------------------------------------------------------
# Singleton
# ------------------------------------------------------------

tongue_fk = TongueFKBuilder()