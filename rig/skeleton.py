"""
maya_faceit.rig.skeleton

Facial skeleton builder for Maya Faceit.

Responsible for creating, validating and rebuilding the
complete facial joint hierarchy.

Author: Your Name
"""

from __future__ import annotations

from dataclasses import dataclass, field

import maya.cmds as cmds # type: ignore

from .joints import (
    JointBuilder,
    JointData,
)

from ..core.logger import log


# ---------------------------------------------------------
# Skeleton Data
# ---------------------------------------------------------

@dataclass(slots=True)
class Skeleton:

    root: str

    joints: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------
# Builder
# ---------------------------------------------------------

class SkeletonBuilder:

    ROOT_NAME = "Face_Rig_JNT_GRP"

    def __init__(self):

        self.joints = JointBuilder()

        self._registry: dict[str, str] = {}

        self._root: str | None = None

    # --------------------------------------------------

    @property
    def root(self):

        return self._root

    # --------------------------------------------------

    @property
    def registry(self):

        return self._registry

    # --------------------------------------------------

    def create_root(
        self,
        name: str | None = None,
    ) -> str:

        name = name or self.ROOT_NAME

        if cmds.objExists(name):

            self._root = name
            return name

        self._root = cmds.createNode(
            "transform",
            name=name,
        )

        log.info(f"Created skeleton root: {self._root}")

        return self._root

    # --------------------------------------------------

    def add_joint(
        self,
        name: str,
        position=(0.0, 0.0, 0.0),
        parent: str | None = None,
    ) -> str:

        joint = self.joints.create(
            name=name,
            position=position,
        )

        if parent:

            cmds.parent(
                joint,
                parent,
            )

        elif self._root:

            cmds.parent(
                joint,
                self._root,
            )

        self._registry[name] = joint

        return joint

    # --------------------------------------------------

    def build_from_landmarks(
        self,
        landmarks: dict[str, tuple],
    ) -> Skeleton:

        self.create_root()

        for name, position in landmarks.items():

            self.add_joint(
                f"{name}_JNT",
                position,
            )

        return Skeleton(
            root=self._root,
            joints=self._registry.copy(),
        )

    # --------------------------------------------------

    def build_from_template(
        self,
        template: list[JointData],
    ) -> Skeleton:

        self.create_root()

        for data in template:

            parent = None

            if data.parent:

                parent = self._registry.get(data.parent)

            joint = self.add_joint(
                data.name,
                data.position,
                parent,
            )

            self._registry[data.name] = joint

        return Skeleton(
            root=self._root,
            joints=self._registry.copy(),
        )

    # --------------------------------------------------

    def orient(
        self,
        root: str | None = None,
    ):

        root = root or self._root

        if not root:
            return

        children = cmds.listRelatives(
            root,
            children=True,
            type="joint",
        ) or []

        for joint in children:

            self.joints.orient(joint)

    # --------------------------------------------------

    def mirror(
        self,
        left_root: str,
    ):

        self.joints.mirror(left_root)

    # --------------------------------------------------

    def hierarchy(self):

        if not self._root:

            return []

        return cmds.listRelatives(
            self._root,
            allDescendents=True,
            fullPath=False,
        ) or []

    # --------------------------------------------------

    def exists(
        self,
        name: str,
    ) -> bool:

        return name in self._registry

    # --------------------------------------------------

    def joint(
        self,
        name: str,
    ) -> str | None:

        return self._registry.get(name)

    # --------------------------------------------------

    def delete(self):

        if self._root and cmds.objExists(self._root):

            cmds.delete(self._root)

        self._registry.clear()

        self._root = None

    # --------------------------------------------------

    def rebuild(
        self,
        template: list[JointData],
    ) -> Skeleton:

        self.delete()

        return self.build_from_template(template)


# ---------------------------------------------------------
# Singleton
# ---------------------------------------------------------

skeleton_builder = SkeletonBuilder()