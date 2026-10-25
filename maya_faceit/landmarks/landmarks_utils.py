# landmarks_utils.py
# Maya Faceit Plugin - Landmarks Utilities
# Converted from Blender to Maya Python 3.11

"""
Landmarks utilities for Faceit Maya plugin.
Handles viewport management and landmark operations.
"""

import maya.cmds as cmds # type: ignore
import maya.api.OpenMaya as om2 # type: ignore
import math
from typing import List, Dict, Optional, Tuple, Any

from ..core.mesh_utils import get_object_center


def check_is_quad_view(area: str) -> bool:
    """
    Check if a view area is in quad view.
    
    Args:
        area: Area name or ID
        
    Returns:
        True if in quad view
    """
    # In Maya, check if view is in quad view
    # This is a placeholder
    return False


def check_if_area_is_active(area: str, x: float, y: float) -> bool:
    """
    Check if an area contains the given coordinates.
    
    Args:
        area: Area name or ID
        x: X coordinate
        y: Y coordinate
        
    Returns:
        True if coordinates are within the area
    """
    # In Maya, we'd check the area bounds
    # This is a placeholder
    return True


def set_front_view(region_3d: Any = None, lock_rotation: bool = True, view_selected: bool = True) -> None:
    """
    Set the view to front view.
    
    Args:
        region_3d: 3D region data
        lock_rotation: Whether to lock rotation
        view_selected: Whether to frame selected
    """
    # In Maya, set view to front
    if view_selected:
        cmds.viewFit()
    
    # Set to front view
    cmds.viewSet('front')
    
    # Lock rotation if requested
    if lock_rotation:
        # In Maya, we'd lock the view
        pass


def unlock_3d_view() -> None:
    """Unlock the 3D view rotation."""
    # In Maya, unlock the view
    pass


def get_center_of_landmarks(landmarks_mesh: str) -> Tuple[float, float, float]:
    """
    Get the center of the landmarks mesh.
    
    Args:
        landmarks_mesh: Landmarks mesh name
        
    Returns:
        Center position (x, y, z)
    """
    if not cmds.objExists(landmarks_mesh):
        return (0.0, 0.0, 0.0)
    
    return get_object_center(landmarks_mesh)


def get_landmark_vertex_positions(landmarks_mesh: str) -> List[Tuple[float, float, float]]:
    """
    Get all vertex positions of the landmarks mesh.
    
    Args:
        landmarks_mesh: Landmarks mesh name
        
    Returns:
        List of vertex positions
    """
    if not cmds.objExists(landmarks_mesh):
        return []
    
    vertex_count = cmds.polyEvaluate(landmarks_mesh, vertex=True)
    positions = []
    
    for i in range(vertex_count):
        pos = cmds.xform(f"{landmarks_mesh}.vtx[{i}]", query=True, worldSpace=True, translation=True)
        if pos:
            positions.append((pos[0], pos[1], pos[2]))
    
    return positions