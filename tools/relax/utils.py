# -*- coding: utf-8 -*-
"""
tools/relax/utils.py

Utilities for relaxation.
"""

import maya.cmds as cmds # type: ignore
from typing import Tuple, List, Optional


class RelaxUtils:
    """Helper functions for relaxation."""

    @staticmethod
    def get_selected_vertices() -> Tuple[str, List[int]]:
        """Get selected vertices as (mesh, list of indices)."""
        selection = cmds.ls(selection=True, flatten=True)
        verts = [v for v in selection if '.vtx' in v]
        if not verts:
            return "", []
        mesh = verts[0].split('.')[0]
        indices = []
        for v in verts:
            try:
                idx = int(v.split('[')[1].split(']')[0])
                indices.append(idx)
            except:
                pass
        return mesh, indices

    @staticmethod
    def get_vertex_count(mesh: str) -> int:
        if cmds.objExists(mesh):
            return cmds.polyEvaluate(mesh, vertex=True)
        return 0

    @staticmethod
    def get_mesh_from_selection() -> Optional[str]:
        selection = cmds.ls(selection=True, long=True)
        for obj in selection:
            if cmds.nodeType(obj) == 'mesh' or cmds.listRelatives(obj, shapes=True):
                shapes = cmds.listRelatives(obj, shapes=True) or []
                if shapes and cmds.nodeType(shapes[0]) == 'mesh':
                    return obj
        return None