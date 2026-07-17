"""
maya_faceit.rig.tongue_visibility

Visibility manager for the tongue rig.

Handles manual and automatic visibility of
controls, helpers, spline objects and debug
nodes.

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
class VisibilityGroup:

    name: str

    node: str


@dataclass(slots=True)
class TongueVisibilityRig:

    groups: list[VisibilityGroup] = field(default_factory=list)

    reverse_node: str | None = None

    built: bool = False


# ---------------------------------------------------------
# Builder
# ---------------------------------------------------------

class TongueVisibilityBuilder:

    def __init__(self):

        self.rig = TongueVisibilityRig()

    # -----------------------------------------------------

    def build(

        self,

        master_control: str,

        fk_group: str,

        ik_group: str,

        curve_group: str,

        cluster_group: str,

        helper_group: str,

        debug_group: str,

    ) -> TongueVisibilityRig:

        self.delete()

        self._ensure_attributes(master_control)

        self._connect_visibility(

            master_control,

            "showFK",

            fk_group,

        )

        self._connect_visibility(

            master_control,

            "showIK",

            ik_group,

        )

        self._connect_visibility(

            master_control,

            "showCurve",

            curve_group,

        )

        self._connect_visibility(

            master_control,

            "showClusters",

            cluster_group,

        )

        self._connect_visibility(

            master_control,

            "showHelpers",

            helper_group,

        )

        self._connect_visibility(

            master_control,

            "showDebug",

            debug_group,

        )

        self._build_auto_visibility(

            master_control,

            fk_group,

            ik_group,

        )

        self.rig.groups.extend([

            VisibilityGroup("FK", fk_group),

            VisibilityGroup("IK", ik_group),

            VisibilityGroup("Curve", curve_group),

            VisibilityGroup("Clusters", cluster_group),

            VisibilityGroup("Helpers", helper_group),

            VisibilityGroup("Debug", debug_group),

        ])

        self.rig.built = True

        return self.rig

    # -----------------------------------------------------

    def _ensure_attributes(

        self,

        control: str,

    ):

        attributes = [

            ("showTongue", True),

            ("showFK", True),

            ("showIK", True),

            ("showCurve", False),

            ("showClusters", False),

            ("showHelpers", False),

            ("showDebug", False),

            ("autoVisibility", True),

        ]

        for attr, default in attributes:

            if cmds.attributeQuery(

                attr,

                node=control,

                exists=True,

            ):

                continue

            cmds.addAttr(

                control,

                longName=attr,

                attributeType="bool",

                defaultValue=default,

                keyable=True,

            )

    # -----------------------------------------------------

    def _connect_visibility(

        self,

        control: str,

        attribute: str,

        group: str,

    ):

        if not cmds.objExists(group):

            return

        cmds.connectAttr(

            f"{control}.{attribute}",

            f"{group}.visibility",

            force=True,

        )

    # -----------------------------------------------------

    def _build_auto_visibility(

        self,

        control: str,

        fk_group: str,

        ik_group: str,

    ):

        reverse = cmds.createNode(

            "reverse",

            name="Tongue_FKIK_Visibility_Reverse",

        )

        cmds.connectAttr(

            f"{control}.fkIkBlend",

            f"{reverse}.inputX",

            force=True,

        )

        fk_condition = cmds.createNode(

            "condition",

            name="Tongue_FK_Visibility_Condition",

        )

        ik_condition = cmds.createNode(

            "condition",

            name="Tongue_IK_Visibility_Condition",

        )

        cmds.setAttr(fk_condition + ".operation", 0)
        cmds.setAttr(ik_condition + ".operation", 0)

        cmds.connectAttr(

            reverse + ".outputX",

            fk_condition + ".firstTerm",

            force=True,

        )

        cmds.setAttr(

            fk_condition + ".secondTerm",

            0.5,

        )

        cmds.setAttr(

            fk_condition + ".colorIfTrueR",

            1,

        )

        cmds.setAttr(

            fk_condition + ".colorIfFalseR",

            0,

        )

        cmds.connectAttr(

            f"{control}.fkIkBlend",

            ik_condition + ".firstTerm",

            force=True,

        )

        cmds.setAttr(

            ik_condition + ".secondTerm",

            0.5,

        )

        cmds.setAttr(

            ik_condition + ".colorIfTrueR",

            1,

        )

        cmds.setAttr(

            ik_condition + ".colorIfFalseR",

            0,

        )

        cmds.connectAttr(

            fk_condition + ".outColorR",

            fk_group + ".visibility",

            force=True,

        )

        cmds.connectAttr(

            ik_condition + ".outColorR",

            ik_group + ".visibility",

            force=True,

        )

        self.rig.reverse_node = reverse

    # -----------------------------------------------------

    def set_visibility(

        self,

        group_name: str,

        state: bool,

    ):

        for group in self.rig.groups:

            if group.name.lower() == group_name.lower():

                if cmds.objExists(group.node):

                    cmds.setAttr(

                        group.node + ".visibility",

                        state,

                    )

                return

    # -----------------------------------------------------

    def show_all(self):

        for group in self.rig.groups:

            if cmds.objExists(group.node):

                cmds.setAttr(

                    group.node + ".visibility",

                    True,

                )

    # -----------------------------------------------------

    def hide_all(self):

        for group in self.rig.groups:

            if cmds.objExists(group.node):

                cmds.setAttr(

                    group.node + ".visibility",

                    False,

                )

    # -----------------------------------------------------

    def delete(self):

        if (

            self.rig.reverse_node

            and cmds.objExists(self.rig.reverse_node)

        ):

            cmds.delete(self.rig.reverse_node)

        self.rig = TongueVisibilityRig()


# ---------------------------------------------------------
# Singleton
# ---------------------------------------------------------

tongue_visibility = TongueVisibilityBuilder()