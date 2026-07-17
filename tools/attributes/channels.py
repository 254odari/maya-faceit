# -*- coding: utf-8 -*-
"""
tools/attributes/channels.py

Channel (attribute) state management: locking, hiding, keyable, etc.
"""

import maya.cmds as cmds # type: ignore
from typing import List, Union, Optional


# =============================================================================
# LOCK / UNLOCK
# =============================================================================

def lock_attributes(node: str, attributes: Union[str, List[str]]) -> bool:
    """
    Lock attributes so they cannot be edited.

    Args:
        node: Node name.
        attributes: Attribute name or list of attribute names (without node prefix).

    Returns:
        True if successful.
    """
    if isinstance(attributes, str):
        attributes = [attributes]
    for attr in attributes:
        full = f"{node}.{attr}"
        if cmds.objExists(full):
            cmds.setAttr(full, lock=True)
    return True


def unlock_attributes(node: str, attributes: Union[str, List[str]]) -> bool:
    """
    Unlock attributes.

    Args:
        node: Node name.
        attributes: Attribute name or list.

    Returns:
        True if successful.
    """
    if isinstance(attributes, str):
        attributes = [attributes]
    for attr in attributes:
        full = f"{node}.{attr}"
        if cmds.objExists(full):
            cmds.setAttr(full, lock=False)
    return True


def is_locked(node: str, attribute: str) -> bool:
    """
    Check if an attribute is locked.

    Returns:
        True if locked.
    """
    full = f"{node}.{attribute}"
    if not cmds.objExists(full):
        return False
    return cmds.getAttr(full, lock=True)


# =============================================================================
# HIDE / SHOW (channel box visibility)
# =============================================================================

def hide_attributes(node: str, attributes: Union[str, List[str]]) -> bool:
    """
    Hide attributes from the channel box.

    Args:
        node: Node name.
        attributes: Attribute name or list.

    Returns:
        True if successful.
    """
    if isinstance(attributes, str):
        attributes = [attributes]
    for attr in attributes:
        full = f"{node}.{attr}"
        if cmds.objExists(full):
            cmds.setAttr(full, channelBox=False)
    return True


def show_attributes(node: str, attributes: Union[str, List[str]]) -> bool:
    """
    Show attributes in the channel box.

    Args:
        node: Node name.
        attributes: Attribute name or list.

    Returns:
        True if successful.
    """
    if isinstance(attributes, str):
        attributes = [attributes]
    for attr in attributes:
        full = f"{node}.{attr}"
        if cmds.objExists(full):
            cmds.setAttr(full, channelBox=True)
    return True


def is_hidden(node: str, attribute: str) -> bool:
    """
    Check if an attribute is hidden from the channel box.

    Returns:
        True if hidden.
    """
    full = f"{node}.{attribute}"
    if not cmds.objExists(full):
        return True
    return not cmds.getAttr(full, channelBox=True)


# =============================================================================
# KEYABLE
# =============================================================================

def set_keyable(node: str, attributes: Union[str, List[str]], keyable: bool = True) -> bool:
    """
    Set the keyable state of attributes.

    Args:
        node: Node name.
        attributes: Attribute name or list.
        keyable: True to make keyable, False to make non-keyable.

    Returns:
        True if successful.
    """
    if isinstance(attributes, str):
        attributes = [attributes]
    for attr in attributes:
        full = f"{node}.{attr}"
        if cmds.objExists(full):
            cmds.setAttr(full, keyable=keyable)
    return True


def is_keyable(node: str, attribute: str) -> bool:
    """
    Check if an attribute is keyable.

    Returns:
        True if keyable.
    """
    full = f"{node}.{attribute}"
    if not cmds.objExists(full):
        return False
    return cmds.getAttr(full, keyable=True)


# =============================================================================
# CHANNEL BOX VISIBILITY (convenience)
# =============================================================================

def set_channel_box_visibility(node: str, attributes: Union[str, List[str]], visible: bool = True) -> bool:
    """
    Show or hide attributes in the channel box (alias for show/hide attributes).

    Args:
        node: Node name.
        attributes: Attribute name or list.
        visible: True to show, False to hide.

    Returns:
        True if successful.
    """
    if visible:
        return show_attributes(node, attributes)
    else:
        return hide_attributes(node, attributes)