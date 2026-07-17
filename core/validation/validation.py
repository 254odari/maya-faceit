"""
core/validation.py

Central validation utilities for Maya Faceit.

Provides validation functions for:

    - Maya nodes
    - Meshes
    - Transforms
    - Joints
    - BlendShapes
    - Controllers
    - Attributes
    - Files
    - Directories
    - Namespaces

Author: Your Name
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import maya.cmds as cmds # type: ignore

from maya_faceit.exceptions import ValidationError
from maya_faceit.core.logger import log


class Validator:
    """Central validation engine."""

    # ---------------------------------------------------------
    # Generic
    # ---------------------------------------------------------

    @staticmethod
    def exists(node: str) -> bool:
        return cmds.objExists(node)

    @staticmethod
    def require_exists(node: str):

        if not cmds.objExists(node):
            raise ValidationError(
                f'Node "{node}" does not exist.'
            )

    # ---------------------------------------------------------
    # Type Validation
    # ---------------------------------------------------------

    @staticmethod
    def node_type(node: str, expected: str):

        Validator.require_exists(node)

        actual = cmds.nodeType(node)

        if actual != expected:

            raise ValidationError(

                f'Expected "{expected}" '

                f'but got "{actual}".'

            )

    # ---------------------------------------------------------
    # Transform
    # ---------------------------------------------------------

    @staticmethod
    def transform(node: str):

        Validator.node_type(node, "transform")

    # ---------------------------------------------------------
    # Joint
    # ---------------------------------------------------------

    @staticmethod
    def joint(node: str):

        Validator.node_type(node, "joint")

    # ---------------------------------------------------------
    # Mesh
    # ---------------------------------------------------------

    @staticmethod
    def mesh(node: str):

        Validator.require_exists(node)

        shapes = cmds.listRelatives(
            node,
            shapes=True,
            fullPath=True,
        ) or []

        if not shapes:

            raise ValidationError(
                f'"{node}" has no shape.'
            )

        if cmds.nodeType(shapes[0]) != "mesh":

            raise ValidationError(
                f'"{node}" is not a mesh.'
            )

    # ---------------------------------------------------------
    # BlendShape
    # ---------------------------------------------------------

    @staticmethod
    def blendshape(node: str):

        Validator.node_type(
            node,
            "blendShape"
        )

    # ---------------------------------------------------------
    # Controller
    # ---------------------------------------------------------

    @staticmethod
    def controller(node: str):

        Validator.transform(node)

        shapes = cmds.listRelatives(
            node,
            shapes=True,
            fullPath=True
        ) or []

        if not shapes:

            raise ValidationError(

                f"{node} has no controller shape."

            )

    # ---------------------------------------------------------
    # Attributes
    # ---------------------------------------------------------

    @staticmethod
    def attribute(node: str, attribute: str):

        Validator.require_exists(node)

        if not cmds.attributeQuery(
            attribute,
            node=node,
            exists=True
        ):

            raise ValidationError(

                f"{node}.{attribute} "

                "does not exist."

            )

    # ---------------------------------------------------------
    # Selection
    # ---------------------------------------------------------

    @staticmethod
    def selection(count: int | None = None):

        selection = cmds.ls(selection=True)

        if not selection:

            raise ValidationError(

                "Nothing is selected."

            )

        if count is not None:

            if len(selection) != count:

                raise ValidationError(

                    f"Expected {count} "

                    f"selected object(s)."

                )

        return selection

    # ---------------------------------------------------------
    # File
    # ---------------------------------------------------------

    @staticmethod
    def file(path: str):

        if not Path(path).exists():

            raise ValidationError(

                f"File not found:\n{path}"

            )

    # ---------------------------------------------------------
    # Directory
    # ---------------------------------------------------------

    @staticmethod
    def directory(path: str):

        if not Path(path).is_dir():

            raise ValidationError(

                f"Directory not found:\n{path}"

            )

    # ---------------------------------------------------------
    # Namespace
    # ---------------------------------------------------------

    @staticmethod
    def namespace(namespace: str):

        if not cmds.namespace(exists=namespace):

            raise ValidationError(

                f'Namespace "{namespace}" '

                "does not exist."

            )

    # ---------------------------------------------------------
    # Duplicate Names
    # ---------------------------------------------------------

    @staticmethod
    def unique_names(nodes: Iterable[str]):

        duplicates = []

        seen = set()

        for node in nodes:

            short = node.split("|")[-1]

            if short in seen:

                duplicates.append(short)

            seen.add(short)

        if duplicates:

            raise ValidationError(

                "Duplicate node names found:\n"

                + "\n".join(duplicates)

            )

    # ---------------------------------------------------------
    # Freeze Transforms
    # ---------------------------------------------------------

    @staticmethod
    def frozen(node: str):

        Validator.transform(node)

        values = cmds.xform(
            node,
            query=True,
            translation=True,
            worldSpace=False
        )

        if any(abs(v) > 1e-5 for v in values):

            raise ValidationError(

                f"{node} "

                "has unfrozen transforms."

            )

    # ---------------------------------------------------------
    # History
    # ---------------------------------------------------------

    @staticmethod
    def history(node: str):

        history = cmds.listHistory(node)

        if history and len(history) > 1:

            log.warning(

                f"{node} contains history."

            )

    # ---------------------------------------------------------
    # Visibility
    # ---------------------------------------------------------

    @staticmethod
    def visible(node: str):

        Validator.require_exists(node)

        if not cmds.getAttr(

            f"{node}.visibility"

        ):

            raise ValidationError(

                f"{node} is hidden."

            )


# ---------------------------------------------------------
# Singleton
# ---------------------------------------------------------

validator = Validator()