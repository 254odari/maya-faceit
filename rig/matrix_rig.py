"""
maya_faceit.rig.matrix_rig

Matrix-based rigging utilities for Maya Faceit.

Provides high-performance matrix constraints using modern Maya
nodes (offsetParentMatrix workflow).

Target:
    Maya 2026
    Python 3.11
"""

from __future__ import annotations

from dataclasses import dataclass, field

import maya.cmds as cmds # type: ignore


# ---------------------------------------------------------
# Data
# ---------------------------------------------------------

@dataclass(slots=True)
class MatrixConstraint:

    name: str
    driver: str
    driven: str
    nodes: list[str] = field(default_factory=list)


# ---------------------------------------------------------
# Matrix Rig Builder
# ---------------------------------------------------------

class MatrixRig:

    def __init__(self):

        self.constraints: dict[str, MatrixConstraint] = {}

    # -----------------------------------------------------
    # Internal
    # -----------------------------------------------------

    def _register(
        self,
        name: str,
        driver: str,
        driven: str,
        nodes: list[str],
    ) -> MatrixConstraint:

        constraint = MatrixConstraint(
            name=name,
            driver=driver,
            driven=driven,
            nodes=nodes,
        )

        self.constraints[name] = constraint

        return constraint

    # -----------------------------------------------------
    # Matrix Parent
    # -----------------------------------------------------

    def parent(
        self,
        name: str,
        driver: str,
        driven: str,
    ) -> MatrixConstraint:
        """
        Matrix parent using offsetParentMatrix.
        """

        mult = cmds.createNode(
            "multMatrix",
            name=f"{name}_MM"
        )

        decomp = cmds.createNode(
            "decomposeMatrix",
            name=f"{name}_DCM"
        )

        cmds.connectAttr(
            f"{driver}.worldMatrix[0]",
            f"{mult}.matrixIn[0]",
            force=True,
        )

        cmds.connectAttr(
            f"{driven}.parentInverseMatrix[0]",
            f"{mult}.matrixIn[1]",
            force=True,
        )

        cmds.connectAttr(
            f"{mult}.matrixSum",
            f"{decomp}.inputMatrix",
            force=True,
        )

        cmds.connectAttr(
            f"{decomp}.outputTranslate",
            f"{driven}.translate",
            force=True,
        )

        cmds.connectAttr(
            f"{decomp}.outputRotate",
            f"{driven}.rotate",
            force=True,
        )

        cmds.connectAttr(
            f"{decomp}.outputScale",
            f"{driven}.scale",
            force=True,
        )

        return self._register(
            name,
            driver,
            driven,
            [mult, decomp],
        )

    # -----------------------------------------------------
    # Offset Parent Matrix
    # -----------------------------------------------------

    def offset_parent(
        self,
        driver: str,
        driven: str,
    ):
        """
        Connect driver directly to offsetParentMatrix.
        """

        cmds.connectAttr(
            f"{driver}.worldMatrix[0]",
            f"{driven}.offsetParentMatrix",
            force=True,
        )

    # -----------------------------------------------------
    # Blend Matrix
    # -----------------------------------------------------

    def blend(
        self,
        name: str,
        drivers: list[str],
        driven: str,
    ) -> MatrixConstraint:

        blend = cmds.createNode(
            "blendMatrix",
            name=f"{name}_BM"
        )

        for index, drv in enumerate(drivers):

            cmds.connectAttr(
                f"{drv}.worldMatrix[0]",
                f"{blend}.target[{index}].targetMatrix",
                force=True,
            )

        cmds.connectAttr(
            f"{blend}.outputMatrix",
            f"{driven}.offsetParentMatrix",
            force=True,
        )

        return self._register(
            name,
            ",".join(drivers),
            driven,
            [blend],
        )

    # -----------------------------------------------------
    # Aim Matrix
    # -----------------------------------------------------

    def aim(
        self,
        name: str,
        driver: str,
        target: str,
        driven: str,
    ) -> MatrixConstraint:

        aim = cmds.createNode(
            "aimMatrix",
            name=f"{name}_AIM"
        )

        cmds.connectAttr(
            f"{driver}.worldMatrix[0]",
            f"{aim}.inputMatrix",
            force=True,
        )

        cmds.connectAttr(
            f"{target}.worldMatrix[0]",
            f"{aim}.primaryTargetMatrix",
            force=True,
        )

        cmds.connectAttr(
            f"{aim}.outputMatrix",
            f"{driven}.offsetParentMatrix",
            force=True,
        )

        return self._register(
            name,
            driver,
            driven,
            [aim],
        )

    # -----------------------------------------------------
    # Space Switching
    # -----------------------------------------------------

    def space_switch(
        self,
        name: str,
        spaces: list[str],
        driven: str,
    ) -> MatrixConstraint:

        blend = cmds.createNode(
            "blendMatrix",
            name=f"{name}_SPACE"
        )

        for i, space in enumerate(spaces):

            cmds.connectAttr(
                f"{space}.worldMatrix[0]",
                f"{blend}.target[{i}].targetMatrix",
                force=True,
            )

        cmds.connectAttr(
            f"{blend}.outputMatrix",
            f"{driven}.offsetParentMatrix",
            force=True,
        )

        return self._register(
            name,
            ",".join(spaces),
            driven,
            [blend],
        )

    # -----------------------------------------------------
    # Delete
    # -----------------------------------------------------

    def delete(
        self,
        name: str,
    ):

        constraint = self.constraints.get(name)

        if constraint is None:
            return

        for node in constraint.nodes:

            if cmds.objExists(node):
                cmds.delete(node)

        del self.constraints[name]

    # -----------------------------------------------------
    # Query
    # -----------------------------------------------------

    def exists(
        self,
        name: str,
    ) -> bool:

        return name in self.constraints

    def get(
        self,
        name: str,
    ) -> MatrixConstraint | None:

        return self.constraints.get(name)

    def list_constraints(self) -> list[str]:

        return sorted(self.constraints.keys())

    def clear(self):

        for name in list(self.constraints.keys()):
            self.delete(name)


# ---------------------------------------------------------
# Singleton
# ---------------------------------------------------------

matrix_rig = MatrixRig()