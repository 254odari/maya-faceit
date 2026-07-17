# -*- coding: utf-8 -*-
"""
maya_faceit.utils.matrix
~~~~~~~~~~~~~~~~~~~~~~~~

Matrix utilities using Maya's OpenMaya.
"""

import maya.api.OpenMaya as om2 # type: ignore
from typing import Tuple, List, Optional


class MatrixUtils:
    """Utility functions for working with Maya matrices."""

    @staticmethod
    def identity() -> om2.MMatrix:
        """Return an identity matrix."""
        return om2.MMatrix()

    @staticmethod
    def translation_matrix(t: Tuple[float, float, float]) -> om2.MMatrix:
        """Create a translation matrix."""
        m = om2.MMatrix()
        om2.MTransformationMatrix(m).setTranslation(om2.MVector(t[0], t[1], t[2]), om2.MSpace.kWorld)
        return m

    @staticmethod
    def rotation_matrix(r: Tuple[float, float, float],
                        rotation_order: str = "xyz") -> om2.MMatrix:
        """Create a rotation matrix from Euler angles."""
        # Use MTransformationMatrix to set rotation
        m = om2.MMatrix()
        tfm = om2.MTransformationMatrix(m)
        # Set rotation in specified order
        euler = om2.MEulerRotation(r[0], r[1], r[2], rotation_order)
        tfm.setRotation(euler)
        return tfm.asMatrix()

    @staticmethod
    def scale_matrix(s: Tuple[float, float, float]) -> om2.MMatrix:
        """Create a scale matrix."""
        m = om2.MMatrix()
        m.setElement(0, 0, s[0])
        m.setElement(1, 1, s[1])
        m.setElement(2, 2, s[2])
        return m

    @staticmethod
    def compose_matrix(t: Tuple[float, float, float],
                       r: Tuple[float, float, float],
                       s: Tuple[float, float, float]) -> om2.MMatrix:
        """Compose a matrix from translation, rotation, scale."""
        # Use MTransformationMatrix
        m = om2.MMatrix()
        tfm = om2.MTransformationMatrix(m)
        tfm.setTranslation(om2.MVector(t[0], t[1], t[2]), om2.MSpace.kWorld)
        euler = om2.MEulerRotation(r[0], r[1], r[2])
        tfm.setRotation(euler)
        tfm.setScale(om2.MVector(s[0], s[1], s[2]), om2.MSpace.kWorld)
        return tfm.asMatrix()

    @staticmethod
    def decompose_matrix(m: om2.MMatrix) -> Tuple[Tuple[float, float, float],
                                                   Tuple[float, float, float],
                                                   Tuple[float, float, float]]:
        """Decompose a matrix into translation, rotation (Euler), scale."""
        tfm = om2.MTransformationMatrix(m)
        t = tfm.translation(om2.MSpace.kWorld)
        euler = tfm.rotation()
        s = tfm.scale(om2.MSpace.kWorld)
        return (t.x, t.y, t.z), (euler.x, euler.y, euler.z), (s.x, s.y, s.z)

    @staticmethod
    def mirror_matrix(axis: str = "x") -> om2.MMatrix:
        """Return a mirror matrix along the specified axis."""
        m = om2.MMatrix()
        if axis == "x":
            m.setElement(0, 0, -1.0)
        elif axis == "y":
            m.setElement(1, 1, -1.0)
        else:  # z
            m.setElement(2, 2, -1.0)
        return m

    @staticmethod
    def get_world_matrix(node: str) -> Optional[om2.MMatrix]:
        """Get the world matrix of a node."""
        import maya.cmds as cmds # type: ignore
        if not cmds.objExists(node):
            return None
        mat = cmds.xform(node, q=True, ws=True, matrix=True)
        # Convert list of 16 floats to MMatrix
        m = om2.MMatrix()
        for i in range(4):
            for j in range(4):
                m.setElement(i, j, mat[i*4 + j])
        return m

    @staticmethod
    def set_world_matrix(node: str, m: om2.MMatrix) -> bool:
        """Set the world matrix of a node."""
        import maya.cmds as cmds # type: ignore
        if not cmds.objExists(node):
            return False
        # Convert MMatrix to list
        mat = [m.getElement(i, j) for i in range(4) for j in range(4)]
        cmds.xform(node, ws=True, matrix=mat)
        return True

    @staticmethod
    def multiply(a: om2.MMatrix, b: om2.MMatrix) -> om2.MMatrix:
        """Multiply two matrices."""
        return a * b