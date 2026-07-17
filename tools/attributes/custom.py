# -*- coding: utf-8 -*-
"""
tools/attributes/custom.py

Custom (user-defined) attribute management.
"""

import maya.cmds as cmds # type: ignore
from typing import List, Optional, Any, Union


# =============================================================================
# ADD / DELETE
# =============================================================================

def add_custom_attribute(node: str, name: str, attr_type: str = "float",
                         default: Any = None, **kwargs) -> bool:
    """
    Add a custom attribute to a node.

    Args:
        node: Node name.
        name: Attribute name.
        attr_type: "float", "double", "int", "long", "bool", "enum", "string".
        default: Default value.
        **kwargs: Additional arguments to cmds.addAttr.

    Returns:
        True if successful.
    """
    if not cmds.objExists(node):
        return False
    # Check if attribute already exists
    if cmds.objExists(f"{node}.{name}"):
        return False

    # Build addAttr arguments
    args = {"longName": name, "attributeType": attr_type}
    if default is not None:
        args["defaultValue"] = default
    args.update(kwargs)

    try:
        cmds.addAttr(node, **args)
        return True
    except:
        return False


def delete_custom_attribute(node: str, name: str) -> bool:
    """
    Delete a custom attribute from a node.

    Args:
        node: Node name.
        name: Attribute name.

    Returns:
        True if successful.
    """
    full = f"{node}.{name}"
    if not cmds.objExists(full):
        return False
    try:
        cmds.deleteAttr(full)
        return True
    except:
        return False


# =============================================================================
# GET / SET
# =============================================================================

def get_custom_attribute(node: str, name: str) -> Optional[Any]:
    """
    Get the value of a custom attribute.

    Returns:
        Attribute value, or None if not found.
    """
    full = f"{node}.{name}"
    if not cmds.objExists(full):
        return None
    try:
        return cmds.getAttr(full)
    except:
        return None


def set_custom_attribute(node: str, name: str, value: Any) -> bool:
    """
    Set the value of a custom attribute.

    Returns:
        True if successful.
    """
    full = f"{node}.{name}"
    if not cmds.objExists(full):
        return False
    try:
        cmds.setAttr(full, value)
        return True
    except:
        return False


# =============================================================================
# LIST / QUERY
# =============================================================================

def list_custom_attributes(node: str) -> List[str]:
    """
    List all custom (user-defined) attributes on a node.

    Returns:
        List of attribute names.
    """
    if not cmds.objExists(node):
        return []
    return cmds.listAttr(node, userDefined=True) or []


def has_custom_attribute(node: str, name: str) -> bool:
    """
    Check if a node has a specific custom attribute.

    Returns:
        True if exists.
    """
    return cmds.objExists(f"{node}.{name}")


# =============================================================================
# CONVENIENCE FACTORIES
# =============================================================================

def add_float_attribute(node: str, name: str, default: float = 0.0,
                        min_val: Optional[float] = None,
                        max_val: Optional[float] = None) -> bool:
    """Add a float attribute with optional min/max."""
    kwargs = {}
    if min_val is not None:
        kwargs["minValue"] = min_val
    if max_val is not None:
        kwargs["maxValue"] = max_val
    return add_custom_attribute(node, name, "float", default, **kwargs)


def add_int_attribute(node: str, name: str, default: int = 0,
                      min_val: Optional[int] = None,
                      max_val: Optional[int] = None) -> bool:
    """Add an integer attribute with optional min/max."""
    kwargs = {}
    if min_val is not None:
        kwargs["minValue"] = min_val
    if max_val is not None:
        kwargs["maxValue"] = max_val
    return add_custom_attribute(node, name, "int", default, **kwargs)


def add_bool_attribute(node: str, name: str, default: bool = False) -> bool:
    """Add a boolean (bool) attribute."""
    return add_custom_attribute(node, name, "bool", default)


def add_string_attribute(node: str, name: str, default: str = "") -> bool:
    """Add a string attribute."""
    return add_custom_attribute(node, name, "string", default)


def add_enum_attribute(node: str, name: str,
                       enum_names: List[str],
                       default: int = 0) -> bool:
    """
    Add an enumeration attribute.

    Args:
        node: Node name.
        name: Attribute name.
        enum_names: List of string labels.
        default: Index of default value.

    Returns:
        True if successful.
    """
    if not enum_names:
        return False
    enum_str = ":".join(enum_names)
    return add_custom_attribute(node, name, "enum", default, enumName=enum_str)