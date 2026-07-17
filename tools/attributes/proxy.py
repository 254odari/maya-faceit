# -*- coding: utf-8 -*-
"""
tools/attributes/proxy.py

Proxy/driven attribute management: connections, drivers, driven attributes.
"""

import maya.cmds as cmds # type: ignore
from typing import List, Optional, Tuple, Union, Any


# =============================================================================
# CONNECT / DISCONNECT
# =============================================================================

def connect_attribute(source: str, target: str, force: bool = False) -> bool:
    """
    Connect two attributes.

    Args:
        source: Full source attribute (e.g., "node1.attr").
        target: Full target attribute (e.g., "node2.attr").
        force: If True, replace existing connections.

    Returns:
        True if successful.
    """
    if not cmds.objExists(source) or not cmds.objExists(target):
        return False
    try:
        cmds.connectAttr(source, target, force=force)
        return True
    except:
        return False


def disconnect_attribute(attr: str) -> bool:
    """
    Disconnect all connections to/from an attribute.

    Args:
        attr: Full attribute name.

    Returns:
        True if successful.
    """
    if not cmds.objExists(attr):
        return False
    try:
        cmds.disconnectAttr(attr)
        return True
    except:
        return False


# =============================================================================
# QUERY CONNECTIONS
# =============================================================================

def get_source_connections(attr: str) -> List[str]:
    """
    Get all source connections to an attribute (incoming connections).

    Returns:
        List of source attribute names.
    """
    if not cmds.objExists(attr):
        return []
    return cmds.listConnections(attr, source=True, plugs=True) or []


def get_target_connections(attr: str) -> List[str]:
    """
    Get all target connections from an attribute (outgoing connections).

    Returns:
        List of target attribute names.
    """
    if not cmds.objExists(attr):
        return []
    return cmds.listConnections(attr, source=False, plugs=True) or []


# =============================================================================
# DRIVER / DRIVEN
# =============================================================================

def create_proxy_attribute(node: str, name: str,
                           source: Optional[str] = None,
                           value: Optional[Any] = None) -> bool:
    """
    Create a proxy attribute that mirrors another attribute or a constant value.

    Args:
        node: Node to add the proxy attribute to.
        name: Proxy attribute name.
        source: Source attribute to connect (optional).
        value: Constant value to set (if no source).

    Returns:
        True if successful.
    """
    if not cmds.objExists(node):
        return False
    if cmds.objExists(f"{node}.{name}"):
        return False

    # Create the attribute
    try:
        cmds.addAttr(node, longName=name, attributeType="float")
        if source and cmds.objExists(source):
            cmds.connectAttr(source, f"{node}.{name}")
        elif value is not None:
            cmds.setAttr(f"{node}.{name}", value)
        return True
    except:
        return False


def is_driven(attr: str) -> bool:
    """
    Check if an attribute is driven (has incoming connections).

    Returns:
        True if driven.
    """
    if not cmds.objExists(attr):
        return False
    return len(cmds.listConnections(attr, source=True, plugs=True)) > 0


def is_driver(attr: str) -> bool:
    """
    Check if an attribute drives others (has outgoing connections).

    Returns:
        True if driver.
    """
    if not cmds.objExists(attr):
        return False
    return len(cmds.listConnections(attr, source=False, plugs=True)) > 0


def get_driver(attr: str) -> Optional[str]:
    """
    Get the driver (source) of a driven attribute.

    Returns:
        Source attribute name, or None if not driven.
    """
    if not is_driven(attr):
        return None
    sources = cmds.listConnections(attr, source=True, plugs=True)
    return sources[0] if sources else None


def get_driven_attributes(attr: str) -> List[str]:
    """
    Get all attributes driven by the given attribute.

    Returns:
        List of target attribute names.
    """
    if not cmds.objExists(attr):
        return []
    return cmds.listConnections(attr, source=False, plugs=True) or []