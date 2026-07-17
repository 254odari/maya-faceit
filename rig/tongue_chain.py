"""
maya_faceit.rig.tongue_chain

Procedural tongue joint chain builder.

Responsibilities
----------------
* Create configurable tongue joint chains (default: 9 joints)
* Parent and orient joints
* Support rebuilding
* Store metadata
* Provide chain queries

This module ONLY creates the joint chain.
It does not build FK, IK, controls or deformation systems.

Target
------
Maya 2026
Python 3.11
"""

from __future__ import annotations

from dataclasses import dataclass, field

import maya.cmds as cmds # type: ignore

from .joints import joint_manager


# ------------------------------------------------------------
# Constants
# ------------------------------------------------------------

DEFAULT_JOINT_COUNT = 9

DEFAULT_LENGTH = 5.0

ROOT_POSITION = (0.0, 14.2, 4.1)


# ------------------------------------------------------------
# Data
# ------------------------------------------------------------

@dataclass(slots=True)
class TongueChain:

    joints: list[str] = field(default_factory=list)

    group: str | None = None

    root: str | None = None

    tip: str | None = None

    length: float = DEFAULT_LENGTH


# ------------------------------------------------------------
# Builder
# ------------------------------------------------------------

class TongueChainBuilder:

    def __init__(self):

        self.chain: TongueChain | None = None

    # -----------------------------------------------------

    def build(
        self,
        joint_count: int = DEFAULT_JOINT_COUNT,
        length: float = DEFAULT_LENGTH,
        parent: str | None = None,
    ) -> TongueChain:

        if joint_count < 3:

            raise ValueError(
                "Tongue requires at least 3 joints."
            )

        if self.exists():

            return self.chain

        group = self._create_group()

        spacing = length / (joint_count - 1)

        joints: list[str] = []

        previous = None

        for index in range(joint_count):

            name = f"C_Tongue_{index + 1:02d}_JNT"

            position = (

                ROOT_POSITION[0],

                ROOT_POSITION[1],

                ROOT_POSITION[2] + (spacing * index),

            )

            joint = joint_manager.create(

                name=name,

                position=position,

            )

            cmds.parent(joint, group)

            if previous:

                cmds.parent(joint, previous)

            previous = joint

            joints.append(joint)

        self._orient_chain(joints)

        if parent and cmds.objExists(parent):

            cmds.parent(joints[0], parent)

        self.chain = TongueChain(

            joints=joints,

            group=group,

            root=joints[0],

            tip=joints[-1],

            length=length,

        )

        return self.chain

    # -----------------------------------------------------

    def rebuild(
        self,
        joint_count: int = DEFAULT_JOINT_COUNT,
        length: float = DEFAULT_LENGTH,
        parent: str |None = None,
    ) -> TongueChain:

        self.delete()

        return self.build(

            joint_count,

            length,

            parent,

        )

    # -----------------------------------------------------

    def delete(self):

        if not self.chain:

            return

        if self.chain.group and cmds.objExists(self.chain.group):

            cmds.delete(self.chain.group)

        self.chain = None

    # -----------------------------------------------------

    def exists(self) -> bool:

        return self.chain is not None

    # -----------------------------------------------------

    def joints(self) -> list[str]:

        if not self.chain:

            return []

        return self.chain.joints

    # -----------------------------------------------------

    def root(self) -> str | None:

        if not self.chain:

            return None

        return self.chain.root

    # -----------------------------------------------------

    def tip(self) -> str | None:

        if not self.chain:

            return None

        return self.chain.tip

    # -----------------------------------------------------

    def _create_group(self) -> str:

        group = "Tongue_Joints_GRP"

        if cmds.objExists(group):

            cmds.delete(group)

        return cmds.group(

            empty=True,

            name=group,

        )

    # -----------------------------------------------------

    def _orient_chain(
        self,
        joints: list[str],
    ):

        if len(joints) < 2:

            return

        cmds.select(clear=True)

        cmds.joint(

            joints[0],

            edit=True,

            orientJoint="xyz",

            secondaryAxisOrient="yup",

            children=True,

            zeroScaleOrient=True,

        )

        cmds.joint(

            joints[-1],

            edit=True,

            orientJoint="none",

            children=False,

        )


# ------------------------------------------------------------
# Singleton
# ------------------------------------------------------------

tongue_chain_builder = TongueChainBuilder()