"""
maya_faceit.rig.visibility

Global visibility manager for Maya Faceit.

This module manages visibility for every rig
component and allows each subsystem to register
its own display groups.

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
class VisibilityGroup:
    """Registered visibility group."""

    name: str
    node: str
    category: str


@dataclass(slots=True)
class VisibilityState:
    """Runtime state."""

    groups: dict[str, VisibilityGroup] = field(default_factory=dict)

    built: bool = False


# ------------------------------------------------------------
# Manager
# ------------------------------------------------------------

class VisibilityManager:
    """
    Global rig visibility manager.
    """

    DEFAULT_GROUPS = (
        "Controllers",
        "Joints",
        "Helpers",
        "Debug",
        "Geometry",
        "Landmarks",
        "BlendShapes",
        "Tongue",
        "Jaw",
        "Eyes",
        "Eyelids",
        "Brows",
        "Cheeks",
        "Nose",
        "Ears",
        "Forehead",
        "Neck",
    )

    def __init__(self):

        self.state = VisibilityState()

    # -----------------------------------------------------

    def register(

        self,

        name: str,

        node: str,

        category: str = "General",

    ):

        if not cmds.objExists(node):
            raise RuntimeError(f"{node} does not exist.")

        self.state.groups[name] = VisibilityGroup(

            name=name,

            node=node,

            category=category,

        )

    # -----------------------------------------------------

    def unregister(

        self,

        name: str,

    ):

        self.state.groups.pop(name, None)

    # -----------------------------------------------------

    def exists(

        self,

        name: str,

    ) -> bool:

        return name in self.state.groups

    # -----------------------------------------------------

    def show(

        self,

        name: str,

    ):

        group = self.state.groups.get(name)

        if not group:

            return

        if cmds.objExists(group.node):

            cmds.setAttr(

                group.node + ".visibility",

                True,

            )

    # -----------------------------------------------------

    def hide(

        self,

        name: str,

    ):

        group = self.state.groups.get(name)

        if not group:

            return

        if cmds.objExists(group.node):

            cmds.setAttr(

                group.node + ".visibility",

                False,

            )

    # -----------------------------------------------------

    def toggle(

        self,

        name: str,

    ):

        group = self.state.groups.get(name)

        if not group:

            return

        state = cmds.getAttr(

            group.node + ".visibility"

        )

        cmds.setAttr(

            group.node + ".visibility",

            not state,

        )

    # -----------------------------------------------------

    def show_all(self):

        for name in self.state.groups:

            self.show(name)

    # -----------------------------------------------------

    def hide_all(self):

        for name in self.state.groups:

            self.hide(name)

    # -----------------------------------------------------

    def hide_category(

        self,

        category: str,

    ):

        for group in self.state.groups.values():

            if group.category == category:

                self.hide(group.name)

    # -----------------------------------------------------

    def show_category(

        self,

        category: str,

    ):

        for group in self.state.groups.values():

            if group.category == category:

                self.show(group.name)

    # -----------------------------------------------------

    def playback_mode(self):
        """
        Lightweight viewport mode.

        Hides helpers and debug nodes.
        """

        self.hide_category("Helpers")

        self.hide_category("Debug")

    # -----------------------------------------------------

    def rigging_mode(self):
        """
        Display everything.
        """

        self.show_all()

    # -----------------------------------------------------

    def animator_mode(self):
        """
        Animator-friendly display.
        """

        self.hide_category("Helpers")

        self.hide_category("Debug")

        self.show_category("Controllers")

    # -----------------------------------------------------

    def export_mode(self):
        """
        Export display.
        """

        self.hide_category("Controllers")

        self.hide_category("Helpers")

        self.hide_category("Debug")

        self.show_category("Geometry")

        self.show_category("Joints")

    # -----------------------------------------------------

    def serialize(self):

        return {

            name: {

                "node": group.node,

                "category": group.category,

            }

            for name, group in self.state.groups.items()

        }

    # -----------------------------------------------------

    def restore(

        self,

        data: dict,

    ):

        self.state.groups.clear()

        for name, info in data.items():

            if cmds.objExists(info["node"]):

                self.register(

                    name,

                    info["node"],

                    info["category"],

                )

    # -----------------------------------------------------

    def clear(self):

        self.state.groups.clear()

        self.state.built = False

    # -----------------------------------------------------

    def registered_groups(self):

        return sorted(self.state.groups.keys())


# ------------------------------------------------------------
# Singleton
# ------------------------------------------------------------

visibility = VisibilityManager()