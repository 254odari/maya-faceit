# -*- coding: utf-8 -*-
"""
tools/attributes
~~~~~~~~~~~~~~~~

Attribute management toolkit for Maya FaceIT.

Provides functions for:
- Locking/unlocking, hiding/showing attributes (channels)
- Creating, editing, deleting custom attributes
- Creating proxy/driven attributes
- Controlling visibility of nodes and attributes
"""

from .channels import (
    lock_attributes,
    unlock_attributes,
    hide_attributes,
    show_attributes,
    set_keyable,
    set_channel_box_visibility,
    is_locked,
    is_hidden,
    is_keyable,
)
from .custom import (
    add_custom_attribute,
    delete_custom_attribute,
    set_custom_attribute,
    get_custom_attribute,
    list_custom_attributes,
    has_custom_attribute,
    add_enum_attribute,
    add_float_attribute,
    add_int_attribute,
    add_string_attribute,
    add_bool_attribute,
)
from .proxy import (
    create_proxy_attribute,
    connect_attribute,
    disconnect_attribute,
    get_source_connections,
    get_target_connections,
    is_driven,
    is_driver,
    get_driver,
    get_driven_attributes,
)
from .visibility import (
    show_node,
    hide_node,
    set_node_visibility,
    get_node_visibility,
    set_display_override,
    clear_display_override,
    set_display_layer_visibility,
)

__all__ = [
    # Channels
    "lock_attributes",
    "unlock_attributes",
    "hide_attributes",
    "show_attributes",
    "set_keyable",
    "set_channel_box_visibility",
    "is_locked",
    "is_hidden",
    "is_keyable",
    # Custom
    "add_custom_attribute",
    "delete_custom_attribute",
    "set_custom_attribute",
    "get_custom_attribute",
    "list_custom_attributes",
    "has_custom_attribute",
    "add_enum_attribute",
    "add_float_attribute",
    "add_int_attribute",
    "add_string_attribute",
    "add_bool_attribute",
    # Proxy
    "create_proxy_attribute",
    "connect_attribute",
    "disconnect_attribute",
    "get_source_connections",
    "get_target_connections",
    "is_driven",
    "is_driver",
    "get_driver",
    "get_driven_attributes",
    # Visibility
    "show_node",
    "hide_node",
    "set_node_visibility",
    "get_node_visibility",
    "set_display_override",
    "clear_display_override",
    "set_display_layer_visibility",
]