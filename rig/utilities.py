"""
maya_faceit.rig.utilities

Rig-specific utility functions used throughout the rigging
framework.

These helpers wrap common Maya operations for creating,
organizing, and managing rig objects.

Author: Your Name
"""

from __future__ import annotations

from typing import Iterable, Sequence

import maya.cmds as cmds # type: ignore


# ---------------------------------------------------------
# Transform Utilities
# ---------------------------------------------------------

def create_transform(
    name: str,
    parent: str | None = None,
) -> str:
    """
    Create an empty transform node.

    Args:
        name: Transform name.
        parent: Optional parent transform.

    Returns:
        Name of the created transform.
    """

    node = cmds.createNode("transform", name=name)

    if parent:
        cmds.parent(node, parent)

    return node


# ---------------------------------------------------------

def match_transform(
    source: str,
    target: str,
    translation: bool = True,
    rotation: bool = True,
    scale: bool = False,
):
    """
    Match target transform to source.
    """

    if translation:

        pos = cmds.xform(source, q=True, ws=True, t=True)

        cmds.xform(target, ws=True, t=pos)

    if rotation:

        rot = cmds.xform(source, q=True, ws=True, ro=True)

        cmds.xform(target, ws=True, ro=rot)

    if scale:

        scl = cmds.xform(source, q=True, r=True, s=True)

        cmds.xform(target, r=True, s=scl)


# ---------------------------------------------------------

def snap(source: str, target: str):
    """
    Snap target onto source.
    """

    match_transform(source, target)


# ---------------------------------------------------------
# Groups
# ---------------------------------------------------------

def create_offset_group(
    node: str,
    suffix: str = "_OFF",
) -> str:
    """
    Create an offset group above a node.
    """

    grp = cmds.group(empty=True, name=node + suffix)

    match_transform(node, grp)

    parent = cmds.listRelatives(node, parent=True)

    if parent:

        cmds.parent(grp, parent[0])

    cmds.parent(node, grp)

    return grp


# ---------------------------------------------------------

def create_zero_group(
    node: str,
) -> str:
    """
    Create a zero group.
    """

    return create_offset_group(node, "_ZERO")


# ---------------------------------------------------------
# Channels
# ---------------------------------------------------------

def lock_channels(
    node: str,
    translate=False,
    rotate=False,
    scale=False,
    visibility=False,
):
    """
    Lock transform channels.
    """

    attrs = []

    if translate:
        attrs += ["tx", "ty", "tz"]

    if rotate:
        attrs += ["rx", "ry", "rz"]

    if scale:
        attrs += ["sx", "sy", "sz"]

    if visibility:
        attrs.append("v")

    for attr in attrs:

        cmds.setAttr(
            f"{node}.{attr}",
            lock=True,
            keyable=False,
            channelBox=False,
        )


# ---------------------------------------------------------

def unlock_channels(node: str):
    """
    Unlock all transform channels.
    """

    attrs = [
        "tx","ty","tz",
        "rx","ry","rz",
        "sx","sy","sz",
        "v"
    ]

    for attr in attrs:

        cmds.setAttr(
            f"{node}.{attr}",
            lock=False,
            keyable=True,
        )


# ---------------------------------------------------------
# Display
# ---------------------------------------------------------

def set_color(
    node: str,
    color: int,
):
    """
    Set viewport color override.
    """

    shapes = cmds.listRelatives(
        node,
        shapes=True,
        fullPath=True,
    ) or []

    for shape in shapes:

        cmds.setAttr(shape + ".overrideEnabled", 1)

        cmds.setAttr(shape + ".overrideColor", color)


# ---------------------------------------------------------

def hide(node: str):

    cmds.setAttr(node + ".visibility", 0)


def show(node: str):

    cmds.setAttr(node + ".visibility", 1)


# ---------------------------------------------------------
# Freeze
# ---------------------------------------------------------

def freeze(node: str):

    cmds.makeIdentity(
        node,
        apply=True,
        translate=True,
        rotate=True,
        scale=True,
    )


# ---------------------------------------------------------
# Parenting
# ---------------------------------------------------------

def safe_parent(
    child: str,
    parent: str | None,
):
    """
    Parent safely.
    """

    if parent:

        cmds.parent(child, parent)


# ---------------------------------------------------------
# Connections
# ---------------------------------------------------------

def connect(
    source: str,
    destination: str,
    force=True,
):
    """
    Connect attributes.
    """

    cmds.connectAttr(
        source,
        destination,
        force=force,
    )


# ---------------------------------------------------------

def disconnect(
    source: str,
    destination: str,
):
    """
    Disconnect attributes.
    """

    if cmds.isConnected(source, destination):

        cmds.disconnectAttr(source, destination)


# ---------------------------------------------------------
# Cleanup
# ---------------------------------------------------------

def delete_if_exists(node: str):

    if cmds.objExists(node):

        cmds.delete(node)


# ---------------------------------------------------------

def exists(node: str) -> bool:

    return cmds.objExists(node)