"""
maya_faceit.rig.spaces

Matrix-based space switching system for Maya Faceit.

Provides modern space switching using blendMatrix and
offsetParentMatrix for high-performance rigs.

Target:
    Maya 2026
    Python 3.11
"""

from __future__ import annotations

from dataclasses import dataclass, field

import maya.cmds as cmds # type: ignore


# ----------------------------------------------------------
# Data
# ----------------------------------------------------------

@dataclass(slots=True)
class Space:

    name: str

    controller: str

    spaces: list[str] = field(default_factory=list)

    blend_node: str = ""

    enum_attribute: str = ""


# ----------------------------------------------------------
# Space Manager
# ----------------------------------------------------------

class SpaceManager:

    def __init__(self):

        self.space_systems: dict[str, Space] = {}

    # --------------------------------------------------

    def create(
        self,
        name: str,
        controller: str,
        spaces: list[str],
        attribute: str = "space",
    ) -> Space:
        """
        Create a matrix-based space switch.
        """

        if not cmds.objExists(controller):
            raise RuntimeError(f"{controller} does not exist.")

        blend = cmds.createNode(
            "blendMatrix",
            name=f"{name}_BLEND"
        )

        # Connect each space matrix
        for index, space in enumerate(spaces):

            cmds.connectAttr(
                f"{space}.worldMatrix[0]",
                f"{blend}.target[{index}].targetMatrix",
                force=True,
            )

        # Output

        cmds.connectAttr(
            f"{blend}.outputMatrix",
            f"{controller}.offsetParentMatrix",
            force=True,
        )

        # Enum attribute

        if not cmds.attributeQuery(
            attribute,
            node=controller,
            exists=True,
        ):

            enum = ":".join(spaces)

            cmds.addAttr(
                controller,
                longName=attribute,
                attributeType="enum",
                enumName=enum,
                keyable=True,
            )

        space = Space(

            name=name,

            controller=controller,

            spaces=spaces,

            blend_node=blend,

            enum_attribute=attribute,
        )

        self.space_systems[name] = space

        return space

    # --------------------------------------------------

    def add_space(
        self,
        system_name: str,
        target: str,
    ):

        system = self.space_systems.get(system_name)

        if system is None:
            return

        index = len(system.spaces)

        cmds.connectAttr(

            f"{target}.worldMatrix[0]",

            f"{system.blend_node}.target[{index}].targetMatrix",

            force=True,
        )

        system.spaces.append(target)

        enum = ":".join(system.spaces)

        cmds.addAttr(

            system.controller,

            edit=True,

            enumName=enum,

            longName=system.enum_attribute,
        )

    # --------------------------------------------------

    def remove(
        self,
        name: str,
    ):

        system = self.space_systems.get(name)

        if system is None:
            return

        if cmds.objExists(system.blend_node):
            cmds.delete(system.blend_node)

        del self.space_systems[name]

    # --------------------------------------------------

    def exists(
        self,
        name: str,
    ) -> bool:

        return name in self.space_systems

    # --------------------------------------------------

    def get(
        self,
        name: str,
    ) -> Space | None:

        return self.space_systems.get(name)

    # --------------------------------------------------

    def list_spaces(self) -> list[str]:

        return sorted(self.space_systems.keys())

    # --------------------------------------------------

    def clear(self):

        for name in list(self.space_systems.keys()):
            self.remove(name)


# ----------------------------------------------------------
# Singleton
# ----------------------------------------------------------

space_manager = SpaceManager()