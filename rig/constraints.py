"""
maya_faceit.rig.constraints

Centralized constraint management for Maya Faceit.

Provides a clean abstraction over Maya constraint nodes.

Author: Your Name
"""

from __future__ import annotations

from dataclasses import dataclass

import maya.cmds as cmds # type: ignore


# ---------------------------------------------------------
# Constraint Data
# ---------------------------------------------------------

@dataclass(slots=True)
class Constraint:

    name: str
    node: str
    type: str


# ---------------------------------------------------------
# Builder
# ---------------------------------------------------------

class ConstraintBuilder:

    # --------------------------------------------------

    def parent(
        self,
        driver: str,
        driven: str,
        maintain_offset: bool = True,
    ) -> Constraint:

        node = cmds.parentConstraint(
            driver,
            driven,
            maintainOffset=maintain_offset,
        )[0]

        return Constraint(node, node, "parent")

    # --------------------------------------------------

    def point(
        self,
        driver: str,
        driven: str,
        maintain_offset: bool = True,
    ) -> Constraint:

        node = cmds.pointConstraint(
            driver,
            driven,
            maintainOffset=maintain_offset,
        )[0]

        return Constraint(node, node, "point")

    # --------------------------------------------------

    def orient(
        self,
        driver: str,
        driven: str,
        maintain_offset: bool = True,
    ) -> Constraint:

        node = cmds.orientConstraint(
            driver,
            driven,
            maintainOffset=maintain_offset,
        )[0]

        return Constraint(node, node, "orient")

    # --------------------------------------------------

    def scale(
        self,
        driver: str,
        driven: str,
        maintain_offset: bool = True,
    ) -> Constraint:

        node = cmds.scaleConstraint(
            driver,
            driven,
            maintainOffset=maintain_offset,
        )[0]

        return Constraint(node, node, "scale")

    # --------------------------------------------------

    def aim(
        self,
        driver: str,
        driven: str,
        aim_vector=(1, 0, 0),
        up_vector=(0, 1, 0),
        world_up_type="scene",
    ) -> Constraint:

        node = cmds.aimConstraint(
            driver,
            driven,
            aimVector=aim_vector,
            upVector=up_vector,
            worldUpType=world_up_type,
        )[0]

        return Constraint(node, node, "aim")

    # --------------------------------------------------

    def pole_vector(
        self,
        driver: str,
        handle: str,
    ) -> Constraint:

        node = cmds.poleVectorConstraint(
            driver,
            handle,
        )[0]

        return Constraint(node, node, "poleVector")

    # --------------------------------------------------

    def geometry(
        self,
        driver: str,
        driven: str,
    ) -> Constraint:

        node = cmds.geometryConstraint(
            driver,
            driven,
        )[0]

        return Constraint(node, node, "geometry")

    # --------------------------------------------------

    def normal(
        self,
        driver: str,
        driven: str,
    ) -> Constraint:

        node = cmds.normalConstraint(
            driver,
            driven,
        )[0]

        return Constraint(node, node, "normal")

    # --------------------------------------------------

    def tangent(
        self,
        driver: str,
        driven: str,
    ) -> Constraint:

        node = cmds.tangentConstraint(
            driver,
            driven,
        )[0]

        return Constraint(node, node, "tangent")

    # --------------------------------------------------

    def set_weight(
        self,
        constraint: str,
        target: str,
        value: float,
    ):

        alias = cmds.parentConstraint(
            constraint,
            query=True,
            weightAliasList=True,
        ) or []

        targets = cmds.parentConstraint(
            constraint,
            query=True,
            targetList=True,
        ) or []

        if target not in targets:
            return

        index = targets.index(target)

        cmds.setAttr(
            f"{constraint}.{alias[index]}",
            value,
        )

    # --------------------------------------------------

    def mute(
        self,
        constraint: str,
    ):

        if cmds.objExists(constraint):
            cmds.setAttr(
                constraint + ".nodeState",
                1,
            )

    # --------------------------------------------------

    def unmute(
        self,
        constraint: str,
    ):

        if cmds.objExists(constraint):
            cmds.setAttr(
                constraint + ".nodeState",
                0,
            )

    # --------------------------------------------------

    def delete(
        self,
        constraint: str,
    ):

        if cmds.objExists(constraint):
            cmds.delete(constraint)

    # --------------------------------------------------

    def exists(
        self,
        constraint: str,
    ) -> bool:

        return cmds.objExists(constraint)

    # --------------------------------------------------

    def list_constraints(
        self,
        node: str,
    ) -> list[str]:

        constraints = cmds.listConnections(
            node,
            type="constraint",
        )

        return constraints or []


# ---------------------------------------------------------
# Singleton
# ---------------------------------------------------------

constraint_builder = ConstraintBuilder()