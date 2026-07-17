"""
maya_faceit.landmark.visualization

Landmark visualization utilities.

Draws landmark points, labels, regions and debug
geometry inside Maya. This module is intended for
inspection only and does not modify the rig.

Target
------
Maya 2026
Python 3.11
"""

from __future__ import annotations

from dataclasses import dataclass

import maya.cmds as cmds

from .landmark_mapper import (
    MappingResult,
)

from .face_regions import (
    face_regions,
)


# ------------------------------------------------------------
# Data
# ------------------------------------------------------------

@dataclass(slots=True)
class VisualizationSettings:

    point_radius: float = 0.25

    show_labels: bool = True

    show_ids: bool = False

    show_regions: bool = True

    show_connections: bool = False

    show_symmetry: bool = False

    group_name: str = "Faceit_Landmarks_GRP"


# ------------------------------------------------------------
# Visualization
# ------------------------------------------------------------

class LandmarkVisualization:
    """
    Viewport visualization manager.
    """

    def __init__(self):

        self.settings = VisualizationSettings()

    # -----------------------------------------------------

    def draw(
        self,
        mapping: MappingResult,
    ):

        self.clear()

        if not mapping.success:
            return

        group = cmds.group(
            empty=True,
            name=self.settings.group_name,
        )

        for landmark in mapping.mapped.values():

            locator = cmds.spaceLocator(
                name=f"lm_{landmark.index:03d}"
            )[0]

            cmds.parent(locator, group)

            cmds.setAttr(
                locator + ".translateX",
                landmark.x,
            )

            cmds.setAttr(
                locator + ".translateY",
                landmark.y,
            )

            cmds.setAttr(
                locator + ".translateZ",
                landmark.z,
            )

            cmds.setAttr(
                locator + ".localScaleX",
                self.settings.point_radius,
            )

            cmds.setAttr(
                locator + ".localScaleY",
                self.settings.point_radius,
            )

            cmds.setAttr(
                locator + ".localScaleZ",
                self.settings.point_radius,
            )

            if self.settings.show_labels:

                cmds.annotate(

                    locator,

                    text=landmark.name,

                )

        if self.settings.show_regions:

            self.draw_regions(mapping)

    # -----------------------------------------------------

    def draw_regions(
        self,
        mapping: MappingResult,
    ):

        for region in face_regions.names():

            points = [

                lm

                for lm in mapping.mapped.values()

                if lm.region == region

            ]

            if len(points) < 2:
                continue

            for a, b in zip(points[:-1], points[1:]):

                curve = cmds.curve(

                    degree=1,

                    point=[

                        (a.x, a.y, a.z),

                        (b.x, b.y, b.z),

                    ],

                    name=f"{region}_CRV",

                )

                cmds.parent(

                    curve,

                    self.settings.group_name,

                )

    # -----------------------------------------------------

    def draw_connections(
        self,
        connections: list[tuple[int, int]],
        mapping: MappingResult,
    ):

        lookup = mapping.mapped

        for start, end in connections:

            if start not in lookup or end not in lookup:
                continue

            a = lookup[start]
            b = lookup[end]

            curve = cmds.curve(

                degree=1,

                point=[

                    (a.x, a.y, a.z),

                    (b.x, b.y, b.z),

                ],

            )

            cmds.parent(
                curve,
                self.settings.group_name,
            )

    # -----------------------------------------------------

    def clear(self):

        if cmds.objExists(
            self.settings.group_name
        ):

            cmds.delete(
                self.settings.group_name
            )

    # -----------------------------------------------------

    def hide(self):

        if cmds.objExists(
            self.settings.group_name
        ):

            cmds.hide(
                self.settings.group_name
            )

    # -----------------------------------------------------

    def show(self):

        if cmds.objExists(
            self.settings.group_name
        ):

            cmds.showHidden(
                self.settings.group_name
            )

    # -----------------------------------------------------

    def serialize(self):

        return {

            "point_radius":
                self.settings.point_radius,

            "show_labels":
                self.settings.show_labels,

            "show_ids":
                self.settings.show_ids,

            "show_regions":
                self.settings.show_regions,

            "show_connections":
                self.settings.show_connections,

            "show_symmetry":
                self.settings.show_symmetry,

        }


# ------------------------------------------------------------
# Singleton
# ------------------------------------------------------------

landmark_visualization = LandmarkVisualization()