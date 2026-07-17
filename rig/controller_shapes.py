"""
maya_faceit.rig.controller_shapes

Controller shape library for Maya Faceit.

Provides a centralized API for creating NURBS curve controller
shapes used throughout the facial rigging system.

Author: Your Name
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import maya.cmds as cmds # type: ignore


# ----------------------------------------------------------
# Shape Definition
# ----------------------------------------------------------

@dataclass(slots=True)
class ShapePreset:
    """Represents a controller shape preset."""

    name: str
    degree: int
    points: list[tuple[float, float, float]]
    closed: bool = True


# ----------------------------------------------------------
# Built-in Shapes
# ----------------------------------------------------------

SHAPES: dict[str, ShapePreset] = {

    "circle": ShapePreset(
        name="circle",
        degree=3,
        points=[],
    ),

    "square": ShapePreset(
        name="square",
        degree=1,
        points=[
            (-1,0,-1),
            (-1,0,1),
            (1,0,1),
            (1,0,-1),
            (-1,0,-1),
        ]
    ),

    "triangle": ShapePreset(
        name="triangle",
        degree=1,
        points=[
            (0,0,1),
            (-1,0,-1),
            (1,0,-1),
            (0,0,1),
        ]
    ),

    "diamond": ShapePreset(
        name="diamond",
        degree=1,
        points=[
            (0,0,1),
            (-1,0,0),
            (0,0,-1),
            (1,0,0),
            (0,0,1),
        ]
    ),
}


# ----------------------------------------------------------
# Controller Shape Library
# ----------------------------------------------------------

class ControllerShapeLibrary:
    """
    Creates and manages controller curve shapes.
    """

    def __init__(self):

        self.custom_shapes = {}

    # ------------------------------------------------------

    def available_shapes(self) -> list[str]:

        return sorted(
            list(SHAPES.keys()) +
            list(self.custom_shapes.keys())
        )

    # ------------------------------------------------------

    def exists(self, shape_name: str) -> bool:

        return (
            shape_name in SHAPES or
            shape_name in self.custom_shapes
        )

    # ------------------------------------------------------

    def create(
        self,
        shape: str,
        name: str,
    ) -> str:
        """
        Create a controller curve.
        """

        if shape == "circle":

            ctrl = cmds.circle(
                name=name,
                normal=(0,1,0),
                constructionHistory=False,
            )[0]

            return ctrl

        if shape not in SHAPES:

            raise ValueError(
                f"Unknown controller shape: {shape}"
            )

        preset = SHAPES[shape]

        ctrl = cmds.curve(
            degree=preset.degree,
            point=preset.points,
            name=name,
        )

        if preset.closed:

            cmds.closeCurve(
                ctrl,
                replaceOriginal=True
            )

        return ctrl

    # ------------------------------------------------------

    def scale(
        self,
        controller: str,
        factor: float,
    ):

        cmds.scale(
            factor,
            factor,
            factor,
            controller,
            relative=True,
        )

        cmds.makeIdentity(
            controller,
            apply=True,
            scale=True,
        )

    # ------------------------------------------------------

    def color(
        self,
        controller: str,
        color: int,
    ):

        shapes = cmds.listRelatives(
            controller,
            shapes=True,
            fullPath=True,
        ) or []

        for shape in shapes:

            cmds.setAttr(
                shape + ".overrideEnabled",
                1
            )

            cmds.setAttr(
                shape + ".overrideColor",
                color
            )

    # ------------------------------------------------------

    def replace_shape(
        self,
        controller: str,
        shape_name: str,
    ):
        """
        Replace a controller's curve shape.
        """

        temp = self.create(
            shape_name,
            "__tempShape__"
        )

        source = cmds.listRelatives(
            temp,
            shapes=True,
            fullPath=True,
        )[0]

        target = cmds.listRelatives(
            controller,
            shapes=True,
            fullPath=True,
        ) or []

        for old in target:

            cmds.delete(old)

        cmds.parent(
            source,
            controller,
            shape=True,
            relative=True,
        )

        cmds.delete(temp)

    # ------------------------------------------------------

    def register(
        self,
        preset: ShapePreset,
    ):

        self.custom_shapes[preset.name] = preset

    # ------------------------------------------------------

    def load_directory(
        self,
        directory: str | Path,
    ):
        """
        Placeholder for loading controller shapes from JSON
        or Maya ASCII files.
        """

        pass


# ----------------------------------------------------------
# Singleton
# ----------------------------------------------------------

controller_shapes = ControllerShapeLibrary()