# -*- coding: utf-8 -*-
"""
maya_faceit.utils.api
~~~~~~~~~~~~~~~~~~~~~

Maya API utilities for safe and easy access to common Maya commands.
"""

import maya.cmds as cmds # type: ignore
import maya.api.OpenMaya as om2 # type: ignore
from typing import Optional, List, Tuple, Any, Union


class MayaAPI:
    """Safe Maya API wrapper with existence checks and error handling."""

    @staticmethod
    def exists(node: str) -> bool:
        """Check if a node exists."""
        return cmds.objExists(node)

    @staticmethod
    def get_type(node: str) -> Optional[str]:
        """Get the node type, or None if it doesn't exist."""
        if cmds.objExists(node):
            return cmds.nodeType(node)
        return None

    @staticmethod
    def get_long_name(node: str) -> Optional[str]:
        """Get the full path (long name) of a node."""
        if cmds.objExists(node):
            return cmds.ls(node, long=True)[0]
        return None

    @staticmethod
    def get_short_name(node: str) -> str:
        """Get the short name (without namespace or path)."""
        return node.split("|")[-1].split(":")[-1]

    @staticmethod
    def get_namespace(node: str) -> str:
        """Get the namespace of a node."""
        if ":" in node:
            return node.split(":")[0]
        return ""

    @staticmethod
    def get_dag_path(node: str) -> Optional[om2.MDagPath]:
        """Get an MDagPath for a node."""
        if not cmds.objExists(node):
            return None
        sel = om2.MSelectionList()
        sel.add(node)
        return sel.getDagPath(0)

    @staticmethod
    def get_mfn_mesh(node: str) -> Optional[om2.MFnMesh]:
        """Get an MFnMesh for a mesh node."""
        dag = MayaAPI.get_dag_path(node)
        if dag:
            if dag.hasFn(om2.MFn.kMesh):
                return om2.MFnMesh(dag)
        return None

    @staticmethod
    def get_mfn_transform(node: str) -> Optional[om2.MFnTransform]:
        """Get an MFnTransform for a transform node."""
        dag = MayaAPI.get_dag_path(node)
        if dag:
            if dag.hasFn(om2.MFn.kTransform):
                return om2.MFnTransform(dag)
        return None

    @staticmethod
    def is_mesh(node: str) -> bool:
        """Check if a node is a polygon mesh."""
        if not cmds.objExists(node):
            return False
        shapes = cmds.listRelatives(node, shapes=True) or []
        if shapes:
            return cmds.nodeType(shapes[0]) == "mesh"
        return False

    @staticmethod
    def is_joint(node: str) -> bool:
        """Check if a node is a joint."""
        return MayaAPI.get_type(node) == "joint"

    @staticmethod
    def is_controller(node: str) -> bool:
        """Check if a node is a controller (transform with NURBS shape)."""
        if not cmds.objExists(node):
            return False
        shapes = cmds.listRelatives(node, shapes=True) or []
        for s in shapes:
            if cmds.nodeType(s) in ["nurbsCurve", "nurbsSurface"]:
                return True
        return False

    @staticmethod
    def get_children(node: str, type_filter: Optional[str] = None) -> List[str]:
        """Get children of a node, optionally filtered by type."""
        children = cmds.listRelatives(node, children=True, fullPath=True) or []
        if type_filter:
            return [c for c in children if cmds.nodeType(c) == type_filter]
        return children

    @staticmethod
    def get_parent(node: str) -> Optional[str]:
        """Get the parent of a node."""
        parent = cmds.listRelatives(node, parent=True, fullPath=True)
        return parent[0] if parent else None

    @staticmethod
    def safe_delete(nodes: Union[str, List[str]], force: bool = False) -> int:
        """Safely delete nodes, skipping locked or referenced nodes."""
        if isinstance(nodes, str):
            nodes = [nodes]
        deleted = 0
        for n in nodes:
            if not cmds.objExists(n):
                continue
            if cmds.referenceQuery(n, isNodeReferenced=True):
                continue
            if cmds.lockNode(n, q=True, lock=True)[0]:
                continue
            try:
                cmds.delete(n)
                deleted += 1
            except:
                pass
        return deleted