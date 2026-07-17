"""
core/scene/dependency_graph.py

Dependency Graph utilities for Maya Faceit.
"""

from __future__ import annotations

from typing import Optional

import maya.cmds as cmds # type: ignore

from ..logger import log
from ...exceptions import ValidationError


class DependencyGraph:
    """High-level Maya DG helper."""

    @staticmethod
    def create_node(node_type: str, name: Optional[str] = None) -> str:
        node = cmds.createNode(node_type, name=name)
        log.debug(f"Created node: {node} ({node_type})")
        return node

    @staticmethod
    def delete(node: str) -> None:
        if cmds.objExists(node):
            cmds.delete(node)
            log.debug(f"Deleted node: {node}")

    @staticmethod
    def exists(node: str) -> bool:
        return cmds.objExists(node)

    @staticmethod
    def connect(source: str, destination: str, force: bool = True) -> None:
        if not cmds.objExists(source.split(".")[0]):
            raise ValidationError(source)
        if not cmds.objExists(destination.split(".")[0]):
            raise ValidationError(destination)
        if cmds.isConnected(source, destination):
            return
        cmds.connectAttr(source, destination, force=force)
        log.debug(f"Connected {source} -> {destination}")

    @staticmethod
    def disconnect(source: str, destination: str) -> None:
        if cmds.isConnected(source, destination):
            cmds.disconnectAttr(source, destination)
            log.debug(f"Disconnected {source} -> {destination}")

    @staticmethod
    def inputs(node: str):
        return cmds.listConnections(node, source=True, destination=False) or []

    @staticmethod
    def outputs(node: str):
        return cmds.listConnections(node, source=False, destination=True) or []

    @staticmethod
    def incoming(attribute: str):
        return cmds.listConnections(attribute, source=True, destination=False, plugs=True) or []

    @staticmethod
    def outgoing(attribute: str):
        return cmds.listConnections(attribute, source=False, destination=True, plugs=True) or []

    def multiply_divide(self, name=None): return self.create_node("multiplyDivide", name)
    def plus_minus_average(self, name=None): return self.create_node("plusMinusAverage", name)
    def clamp(self, name=None): return self.create_node("clamp", name)
    def condition(self, name=None): return self.create_node("condition", name)
    def blend_colors(self, name=None): return self.create_node("blendColors", name)
    def reverse(self, name=None): return self.create_node("reverse", name)
    def remap_value(self, name=None): return self.create_node("remapValue", name)
    def mult_matrix(self, name=None): return self.create_node("multMatrix", name)
    def decompose_matrix(self, name=None): return self.create_node("decomposeMatrix", name)
    def compose_matrix(self, name=None): return self.create_node("composeMatrix", name)
    def wt_add_matrix(self, name=None): return self.create_node("wtAddMatrix", name)


dependency_graph = DependencyGraph()