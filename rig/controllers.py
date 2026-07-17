"""
maya_faceit.rig.controllers

Controller creation and management.

This module provides the primary API for creating animation
controllers used throughout Maya Faceit.

Author: Your Name
"""

from __future__ import annotations

from dataclasses import dataclass

import maya.cmds as cmds # type: ignore

from .attributes import AttributeManager
from .controller_shapes import controller_shapes
from .utilities import (
    create_offset_group,
    lock_channels,
    match_transform,
)


# ----------------------------------------------------------
# Data Classes
# ----------------------------------------------------------

@dataclass(slots=True)
class Controller:

    name: str
    transform: str
    zero: str | None = None
    offset: str | None = None
    auto: str | None = None


# ----------------------------------------------------------
# Builder
# ----------------------------------------------------------

class ControllerBuilder:

    COLORS = {
        "center": 17,
        "left": 6,
        "right": 13,
        "yellow": 17,
        "red": 13,
        "blue": 6,
        "green": 14,
    }

    def __init__(self):

        self.attributes = AttributeManager()

    # --------------------------------------------------

    def create(
        self,
        name: str,
        shape: str = "circle",
        size: float = 1.0,
        color: str = "center",
        match: str | None = None,
        parent: str | None = None,
        zero: bool = True,
        offset: bool = False,
    ) -> Controller:
        """
        Create a controller.
        """

        ctrl = controller_shapes.create(
            shape,
            name,
        )

        controller_shapes.scale(
            ctrl,
            size,
        )

        controller_shapes.color(
            ctrl,
            self.COLORS.get(color, 17),
        )

        if match:

            match_transform(
                match,
                ctrl,
            )

        if parent:

            cmds.parent(
                ctrl,
                parent,
            )

        zero_grp = None

        if zero:

            zero_grp = create_offset_group(
                ctrl,
                "_ZERO",
            )

        offset_grp = None

        if offset:

            offset_grp = create_offset_group(
                ctrl,
                "_OFFSET",
            )

        return Controller(
            name=name,
            transform=ctrl,
            zero=zero_grp,
            offset=offset_grp,
        )

    # --------------------------------------------------

    def add_float(
        self,
        controller: str,
        name: str,
        default=0.0,
        minimum=None,
        maximum=None,
    ):

        self.attributes.add_float(
            controller,
            name,
            default=default,
            minimum=minimum,
            maximum=maximum,
        )

    # --------------------------------------------------

    def add_bool(
        self,
        controller: str,
        name: str,
        default=False,
    ):

        self.attributes.add_bool(
            controller,
            name,
            default=default,
        )

    # --------------------------------------------------

    def add_enum(
        self,
        controller: str,
        name: str,
        values,
    ):

        self.attributes.add_enum(
            controller,
            name,
            values,
        )

    # --------------------------------------------------

    def lock(
        self,
        controller: str,
        translate=False,
        rotate=False,
        scale=True,
        visibility=True,
    ):

        lock_channels(
            controller,
            translate=translate,
            rotate=rotate,
            scale=scale,
            visibility=visibility,
        )

    # --------------------------------------------------

    def set_color(
        self,
        controller: str,
        color: str,
    ):

        controller_shapes.color(
            controller,
            self.COLORS.get(color, 17),
        )

    # --------------------------------------------------

    def set_shape(
        self,
        controller: str,
        shape: str,
    ):

        controller_shapes.replace_shape(
            controller,
            shape,
        )

    # --------------------------------------------------

    def set_size(
        self,
        controller: str,
        scale: float,
    ):

        controller_shapes.scale(
            controller,
            scale,
        )

    # --------------------------------------------------

    def create_gimbal(
        self,
        controller: str,
        scale: float = 0.8,
    ) -> str:
        """
        Create a gimbal controller.
        """

        gimbal = controller_shapes.create(
            "circle",
            controller + "_GMB",
        )

        controller_shapes.scale(
            gimbal,
            scale,
        )

        match_transform(
            controller,
            gimbal,
        )

        cmds.parent(
            gimbal,
            controller,
        )

        return gimbal

    # --------------------------------------------------

    def delete(
        self,
        controller: str,
    ):

        if cmds.objExists(controller):

            cmds.delete(controller)


# ----------------------------------------------------------
# Singleton
# ----------------------------------------------------------

controller_builder = ControllerBuilder()