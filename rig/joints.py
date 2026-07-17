"""
maya_faceit.rig.joints

Joint creation and management for Maya Faceit.

This module provides a centralized API for creating,
orienting, mirroring, and managing facial joints.

Author: Your Name
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import maya.cmds as cmds # type: ignore


# ---------------------------------------------------------
# Data Classes
# ---------------------------------------------------------

@dataclass(slots=True)
class JointData:
    """Represents a facial joint."""

    name: str
    position: tuple[float, float, float]
    parent: str | None = None


# ---------------------------------------------------------
# Joint Builder
# ---------------------------------------------------------

class JointBuilder:
    """Utility class for creating and managing joints."""

    DEFAULT_RADIUS = 0.25

    # -----------------------------------------------------

    def create(
        self,
        name: str,
        position=(0.0, 0.0, 0.0),
        parent: str | None = None,
        radius: float | None = None,
    ) -> str:
        """
        Create a single joint.
        """

        cmds.select(clear=True)

        joint = cmds.joint(
            name=name,
            position=position,
            radius=radius or self.DEFAULT_RADIUS,
        )

        if parent:
            cmds.parent(joint, parent)

        return joint

    # -----------------------------------------------------

    def create_chain(
        self,
        joints: Iterable[JointData],
    ) -> list[str]:
        """
        Create a joint hierarchy from JointData.
        """

        created = []

        for data in joints:

            joint = self.create(
                name=data.name,
                position=data.position,
            )

            if data.parent:
                cmds.parent(joint, data.parent)

            created.append(joint)

        return created

    # -----------------------------------------------------

    def orient(
        self,
        root: str,
        orient="xyz",
        secondary="yup",
    ):
        """
        Orient an entire joint hierarchy.
        """

        cmds.joint(
            root,
            edit=True,
            orientJoint=orient,
            secondaryAxisOrient=secondary,
            children=True,
            zeroScaleOrient=True,
        )

    # -----------------------------------------------------

    def freeze_orientation(
        self,
        joint: str,
    ):
        """
        Freeze joint orientation.
        """

        cmds.makeIdentity(
            joint,
            apply=True,
            rotate=True,
        )

    # -----------------------------------------------------

    def mirror(
        self,
        root: str,
        mirrorYZ=True,
        search="L_",
        replace="R_",
    ) -> list[str]:
        """
        Mirror a joint hierarchy.
        """

        return cmds.mirrorJoint(
            root,
            mirrorYZ=mirrorYZ,
            mirrorBehavior=True,
            searchReplace=(search, replace),
        )

    # -----------------------------------------------------

    def duplicate(
        self,
        root: str,
        name: str | None = None,
    ) -> str:
        """
        Duplicate a joint hierarchy.
        """

        duplicate = cmds.duplicate(
            root,
            renameChildren=True,
        )[0]

        if name:
            duplicate = cmds.rename(
                duplicate,
                name,
            )

        return duplicate

    # -----------------------------------------------------

    def set_radius(
        self,
        joint: str,
        radius: float,
    ):
        """
        Set joint display radius.
        """

        cmds.setAttr(
            f"{joint}.radius",
            radius,
        )

    # -----------------------------------------------------

    def parent(
        self,
        joint: str,
        parent: str,
    ):
        """
        Parent a joint.
        """

        cmds.parent(
            joint,
            parent,
        )

    # -----------------------------------------------------

    def unparent(
        self,
        joint: str,
    ):
        """
        Parent joint to world.
        """

        cmds.parent(
            joint,
            world=True,
        )

    # -----------------------------------------------------

    def hierarchy(
        self,
        root: str,
    ) -> list[str]:
        """
        Return the joint hierarchy.
        """

        joints = cmds.listRelatives(
            root,
            allDescendents=True,
            type="joint",
            fullPath=False,
        ) or []

        joints.reverse()

        return [root] + joints

    # -----------------------------------------------------

    def exists(
        self,
        joint: str,
    ) -> bool:
        """
        Check if a joint exists.
        """

        return cmds.objExists(joint)

    # -----------------------------------------------------

    def delete(
        self,
        joint: str,
    ):
        """
        Delete a joint hierarchy.
        """

        if cmds.objExists(joint):
            cmds.delete(joint)

    # -----------------------------------------------------

    def build_from_landmarks(
        self,
        landmarks: dict[str, tuple[float, float, float]],
        suffix: str = "_JNT",
    ) -> list[str]:
        """
        Build joints directly from solved landmark positions.
        """

        created = []

        for name, position in landmarks.items():

            joint = self.create(
                name=f"{name}{suffix}",
                position=position,
            )

            created.append(joint)

        return created


# ---------------------------------------------------------
# Singleton
# ---------------------------------------------------------

joint_builder = JointBuilder()