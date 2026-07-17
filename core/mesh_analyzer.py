"""
core/mesh_analyzer.py

Mesh analysis utilities for Maya Faceit.

Responsible for:

    • Polygon statistics
    • Bounding box analysis
    • World dimensions
    • Center calculation
    • Symmetry estimation
    • Vertex count
    • Face count
    • Edge count
    • UV detection
    • History detection
    • Shape validation

Author: Your Name
"""

from __future__ import annotations

from dataclasses import dataclass

import maya.cmds as cmds # type: ignore

from maya_faceit.exceptions import ValidationError
from maya_faceit.core.logger import log


# -------------------------------------------------------------
# Data Container
# -------------------------------------------------------------

@dataclass(slots=True)
class MeshInfo:

    mesh: str

    vertices: int

    edges: int

    faces: int

    triangles: int

    uv_sets: int

    width: float

    height: float

    depth: float

    center: tuple

    history: bool


# -------------------------------------------------------------
# Mesh Analyzer
# -------------------------------------------------------------

class MeshAnalyzer:

    # ---------------------------------------------------------

    def analyze(self, mesh: str) -> MeshInfo:

        self.validate(mesh)

        vertices = cmds.polyEvaluate(mesh, vertex=True)

        edges = cmds.polyEvaluate(mesh, edge=True)

        faces = cmds.polyEvaluate(mesh, face=True)

        triangles = cmds.polyEvaluate(mesh, triangle=True)

        uv_sets = len(cmds.polyUVSet(mesh, q=True, allUVSets=True) or [])

        bbox = cmds.exactWorldBoundingBox(mesh)

        width = bbox[3] - bbox[0]

        height = bbox[4] - bbox[1]

        depth = bbox[5] - bbox[2]

        center = (

            (bbox[0] + bbox[3]) * 0.5,

            (bbox[1] + bbox[4]) * 0.5,

            (bbox[2] + bbox[5]) * 0.5,

        )

        history = bool(cmds.listHistory(mesh))

        info = MeshInfo(

            mesh=mesh,

            vertices=vertices,

            edges=edges,

            faces=faces,

            triangles=triangles,

            uv_sets=uv_sets,

            width=width,

            height=height,

            depth=depth,

            center=center,

            history=history,

        )

        log.info(f"Mesh analyzed: {mesh}")

        return info

    # ---------------------------------------------------------

    @staticmethod
    def validate(mesh: str):

        if not cmds.objExists(mesh):

            raise ValidationError(f"{mesh} does not exist.")

        shapes = cmds.listRelatives(

            mesh,

            shapes=True,

            fullPath=True

        ) or []

        if not shapes:

            raise ValidationError(

                f"{mesh} has no mesh shape."

            )

        if cmds.nodeType(shapes[0]) != "mesh":

            raise ValidationError(

                f"{mesh} is not a polygon mesh."

            )

    # ---------------------------------------------------------

    @staticmethod
    def bounding_box(mesh: str):

        return cmds.exactWorldBoundingBox(mesh)

    # ---------------------------------------------------------

    @staticmethod
    def dimensions(mesh: str):

        bbox = cmds.exactWorldBoundingBox(mesh)

        return (

            bbox[3] - bbox[0],

            bbox[4] - bbox[1],

            bbox[5] - bbox[2],

        )

    # ---------------------------------------------------------

    @staticmethod
    def center(mesh: str):

        bbox = cmds.exactWorldBoundingBox(mesh)

        return (

            (bbox[0] + bbox[3]) * .5,

            (bbox[1] + bbox[4]) * .5,

            (bbox[2] + bbox[5]) * .5,

        )

    # ---------------------------------------------------------

    @staticmethod
    def has_history(mesh: str):

        return bool(cmds.listHistory(mesh))

    # ---------------------------------------------------------

    @staticmethod
    def uv_sets(mesh: str):

        return cmds.polyUVSet(

            mesh,

            q=True,

            allUVSets=True

        ) or []

    # ---------------------------------------------------------

    @staticmethod
    def vertex_count(mesh: str):

        return cmds.polyEvaluate(

            mesh,

            vertex=True

        )

    # ---------------------------------------------------------

    @staticmethod
    def edge_count(mesh: str):

        return cmds.polyEvaluate(

            mesh,

            edge=True

        )

    # ---------------------------------------------------------

    @staticmethod
    def face_count(mesh: str):

        return cmds.polyEvaluate(

            mesh,

            face=True

        )

    # ---------------------------------------------------------

    @staticmethod
    def triangle_count(mesh: str):

        return cmds.polyEvaluate(

            mesh,

            triangle=True

        )

    # ---------------------------------------------------------

    @staticmethod
    def is_centered(mesh: str, tolerance=0.001):

        center = MeshAnalyzer.center(mesh)

        return abs(center[0]) <= tolerance

    # ---------------------------------------------------------

    @staticmethod
    def world_scale(mesh: str):

        width, height, depth = MeshAnalyzer.dimensions(mesh)

        return max(width, height, depth)


# -------------------------------------------------------------
# Singleton
# -------------------------------------------------------------

mesh_analyzer = MeshAnalyzer()