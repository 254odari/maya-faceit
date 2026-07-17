"""
maya_faceit.rig.attributes

Utilities for creating and managing Maya attributes used by
the Maya Faceit rigging framework.

This module provides a high-level API for adding custom attributes
to controllers and rig nodes, with support for float, integer,
boolean, enum, and string types.

Author: Your Name
"""

from __future__ import annotations

from typing import Any, Iterable, Optional, List, Union

import maya.cmds as cmds # type: ignore


class AttributeManager:
    """
    Manager for creating and manipulating custom attributes on Maya nodes.

    Usage:
        attr_mgr = AttributeManager()
        attr_mgr.add_float("CTRL_Head", "Follow", default=1.0, min=0, max=1)
        attr_mgr.add_enum("CTRL_Head", "Space", values=["World", "Local"])
        attr_mgr.lock_attributes("CTRL_Head", ["tx", "ty", "tz"])
    """

    # ----------------------------------------------------------
    # Add Attributes
    # ----------------------------------------------------------

    def add_float(
        self,
        node: str,
        name: str,
        default: float = 0.0,
        minimum: Optional[float] = None,
        maximum: Optional[float] = None,
        keyable: bool = True,
    ) -> None:
        """
        Add a float attribute to a node.

        Args:
            node: Node name.
            name: Attribute name.
            default: Default value.
            minimum: Minimum value (optional).
            maximum: Maximum value (optional).
            keyable: Whether the attribute is keyable.
        """
        if not cmds.objExists(node):
            raise RuntimeError(f"Node '{node}' does not exist.")

        if cmds.attributeQuery(name, node=node, exists=True):
            return  # Attribute already exists; skip.

        cmds.addAttr(
            node,
            longName=name,
            attributeType="float",
            defaultValue=default,
            keyable=keyable,
        )
        if minimum is not None:
            cmds.setAttr(f"{node}.{name}", edit=True, minValue=minimum)
        if maximum is not None:
            cmds.setAttr(f"{node}.{name}", edit=True, maxValue=maximum)

    def add_int(
        self,
        node: str,
        name: str,
        default: int = 0,
        minimum: Optional[int] = None,
        maximum: Optional[int] = None,
        keyable: bool = True,
    ) -> None:
        """
        Add an integer attribute to a node.

        Args:
            node: Node name.
            name: Attribute name.
            default: Default value.
            minimum: Minimum value (optional).
            maximum: Maximum value (optional).
            keyable: Whether the attribute is keyable.
        """
        if not cmds.objExists(node):
            raise RuntimeError(f"Node '{node}' does not exist.")

        if cmds.attributeQuery(name, node=node, exists=True):
            return

        cmds.addAttr(
            node,
            longName=name,
            attributeType="long",
            defaultValue=default,
            keyable=keyable,
        )
        if minimum is not None:
            cmds.setAttr(f"{node}.{name}", edit=True, minValue=minimum)
        if maximum is not None:
            cmds.setAttr(f"{node}.{name}", edit=True, maxValue=maximum)

    def add_bool(
        self,
        node: str,
        name: str,
        default: bool = False,
        keyable: bool = True,
    ) -> None:
        """
        Add a boolean attribute to a node.

        Args:
            node: Node name.
            name: Attribute name.
            default: Default value.
            keyable: Whether the attribute is keyable.
        """
        if not cmds.objExists(node):
            raise RuntimeError(f"Node '{node}' does not exist.")

        if cmds.attributeQuery(name, node=node, exists=True):
            return

        cmds.addAttr(
            node,
            longName=name,
            attributeType="bool",
            defaultValue=default,
            keyable=keyable,
        )

    def add_enum(
        self,
        node: str,
        name: str,
        values: List[str],
        default_index: int = 0,
        keyable: bool = True,
    ) -> None:
        """
        Add an enum attribute to a node.

        Args:
            node: Node name.
            name: Attribute name.
            values: List of enum string values.
            default_index: Index of the default value.
            keyable: Whether the attribute is keyable.
        """
        if not cmds.objExists(node):
            raise RuntimeError(f"Node '{node}' does not exist.")

        if cmds.attributeQuery(name, node=node, exists=True):
            return

        if not values:
            raise ValueError("Enum must have at least one value.")

        enum_string = ":".join(values)
        cmds.addAttr(
            node,
            longName=name,
            attributeType="enum",
            enumName=enum_string,
            defaultValue=default_index,
            keyable=keyable,
        )

    def add_string(
        self,
        node: str,
        name: str,
        default: str = "",
        keyable: bool = True,
    ) -> None:
        """
        Add a string attribute to a node.

        Args:
            node: Node name.
            name: Attribute name.
            default: Default string value.
            keyable: Whether the attribute is keyable.
        """
        if not cmds.objExists(node):
            raise RuntimeError(f"Node '{node}' does not exist.")

        if cmds.attributeQuery(name, node=node, exists=True):
            return

        cmds.addAttr(
            node,
            longName=name,
            dataType="string",
            keyable=keyable,
        )
        cmds.setAttr(f"{node}.{name}", default, type="string")

    # ----------------------------------------------------------
    # Lock / Unlock Attributes
    # ----------------------------------------------------------

    def lock_attributes(
        self,
        node: str,
        attributes: Iterable[str],
        keyable: bool = False,
        channel_box: bool = False,
    ) -> None:
        """
        Lock specified attributes on a node.

        Args:
            node: Node name.
            attributes: List of attribute names.
            keyable: Whether to set keyable to False.
            channel_box: Whether to hide from channel box.
        """
        if not cmds.objExists(node):
            raise RuntimeError(f"Node '{node}' does not exist.")

        for attr in attributes:
            full_attr = f"{node}.{attr}"
            if cmds.objExists(full_attr):
                cmds.setAttr(
                    full_attr,
                    lock=True,
                    keyable=keyable,
                    channelBox=channel_box,
                )

    def unlock_attributes(
        self,
        node: str,
        attributes: Iterable[str],
        keyable: bool = True,
    ) -> None:
        """
        Unlock specified attributes on a node.

        Args:
            node: Node name.
            attributes: List of attribute names.
            keyable: Whether to set keyable to True.
        """
        if not cmds.objExists(node):
            raise RuntimeError(f"Node '{node}' does not exist.")

        for attr in attributes:
            full_attr = f"{node}.{attr}"
            if cmds.objExists(full_attr):
                cmds.setAttr(
                    full_attr,
                    lock=False,
                    keyable=keyable,
                )

    def lock_all_transform_attributes(self, node: str) -> None:
        """
        Lock all translate, rotate, scale, and visibility attributes.

        Args:
            node: Node name.
        """
        attrs = ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz", "v"]
        self.lock_attributes(node, attrs, keyable=False, channel_box=False)

    def unlock_all_transform_attributes(self, node: str) -> None:
        """
        Unlock all translate, rotate, scale, and visibility attributes.

        Args:
            node: Node name.
        """
        attrs = ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz", "v"]
        self.unlock_attributes(node, attrs, keyable=True)

    # ----------------------------------------------------------
    # Query and Set
    # ----------------------------------------------------------

    def attribute_exists(self, node: str, name: str) -> bool:
        """Check if an attribute exists on a node."""
        if not cmds.objExists(node):
            return False
        return cmds.attributeQuery(name, node=node, exists=True)

    def set_attribute(self, node: str, name: str, value: Any) -> None:
        """
        Set an attribute value.

        Args:
            node: Node name.
            name: Attribute name.
            value: New value.
        """
        full_attr = f"{node}.{name}"
        if not cmds.objExists(full_attr):
            raise RuntimeError(f"Attribute '{full_attr}' does not exist.")

        # Determine type to set accordingly.
        if isinstance(value, bool):
            cmds.setAttr(full_attr, int(value))
        elif isinstance(value, str):
            cmds.setAttr(full_attr, value, type="string")
        else:
            cmds.setAttr(full_attr, value)

    def get_attribute(self, node: str, name: str) -> Any:
        """
        Get an attribute value.

        Args:
            node: Node name.
            name: Attribute name.

        Returns:
            The attribute value.
        """
        full_attr = f"{node}.{name}"
        if not cmds.objExists(full_attr):
            raise RuntimeError(f"Attribute '{full_attr}' does not exist.")

        return cmds.getAttr(full_attr)

    def get_all_attributes(
        self,
        node: str,
        custom_only: bool = True,
    ) -> List[str]:
        """
        Get a list of attribute names on a node.

        Args:
            node: Node name.
            custom_only: If True, only return user-defined (custom) attributes.

        Returns:
            List of attribute names.
        """
        if not cmds.objExists(node):
            return []

        if custom_only:
            return cmds.listAttr(node, userDefined=True) or []
        else:
            return cmds.listAttr(node) or []

    # ----------------------------------------------------------
    # Bulk Operations
    # ----------------------------------------------------------

    def add_attributes_from_dict(
        self,
        node: str,
        attr_dict: dict,
    ) -> None:
        """
        Add multiple attributes from a dictionary.

        The dictionary can have keys:
            - "float": list of (name, default, min, max)
            - "int": list of (name, default, min, max)
            - "bool": list of (name, default)
            - "enum": list of (name, values, default_index)
            - "string": list of (name, default)

        Args:
            node: Node name.
            attr_dict: Dictionary of attribute definitions.
        """
        for attr_type, items in attr_dict.items():
            if attr_type == "float":
                for item in items:
                    name, default, min_val, max_val = item
                    self.add_float(node, name, default, min_val, max_val)
            elif attr_type == "int":
                for item in items:
                    name, default, min_val, max_val = item
                    self.add_int(node, name, default, min_val, max_val)
            elif attr_type == "bool":
                for item in items:
                    name, default = item
                    self.add_bool(node, name, default)
            elif attr_type == "enum":
                for item in items:
                    name, values, default_index = item
                    self.add_enum(node, name, values, default_index)
            elif attr_type == "string":
                for item in items:
                    name, default = item
                    self.add_string(node, name, default)
            else:
                raise ValueError(f"Unsupported attribute type: {attr_type}")

    def copy_attributes(
        self,
        source_node: str,
        target_node: str,
        attribute_names: Optional[List[str]] = None,
    ) -> None:
        """
        Copy attributes from one node to another.

        Args:
            source_node: Source node.
            target_node: Target node.
            attribute_names: List of attribute names to copy. If None, copies all.
        """
        if not cmds.objExists(source_node):
            raise RuntimeError(f"Source node '{source_node}' does not exist.")
        if not cmds.objExists(target_node):
            raise RuntimeError(f"Target node '{target_node}' does not exist.")

        if attribute_names is None:
            attribute_names = self.get_all_attributes(source_node)

        for attr in attribute_names:
            if self.attribute_exists(source_node, attr):
                value = self.get_attribute(source_node, attr)
                # Add the attribute if it doesn't exist on target
                if not self.attribute_exists(target_node, attr):
                    # Determine type from source (we'll add as float for simplicity)
                    # This is a simplistic approach; for production you'd check types.
                    self.add_float(target_node, attr, default=0.0)
                self.set_attribute(target_node, attr, value)


# ----------------------------------------------------------
# Singleton
# ----------------------------------------------------------

attribute_manager = AttributeManager()