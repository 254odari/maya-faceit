# landmark_utils.py
# Maya Faceit Plugin - Landmark Utilities
# Converted from Blender to Maya Python 3.11

"""
Landmark utilities for Faceit Maya plugin.
Handles facial landmark creation, management, and snapping.
"""

import maya.cmds as cmds
import maya.api.OpenMaya as om2
from typing import List, Dict, Optional, Tuple
import json
import os


# ============================================================
# Landmark Definitions
# ============================================================

# Standard ARKit landmark names
ARKIT_LANDMARKS = [
    "eye_l", "eye_r",
    "eye_brow_l", "eye_brow_r",
    "nose_tip", "nose_bridge",
    "mouth_l", "mouth_r",
    "mouth_top", "mouth_bottom",
    "chin", "forehead",
    "cheek_l", "cheek_r",
    "jaw_l", "jaw_r",
    "lip_upper_l", "lip_upper_r",
    "lip_lower_l", "lip_lower_r"
]

# Faceit landmark names
FACEIT_LANDMARKS = [
    "eye_left", "eye_right",
    "brow_left", "brow_right",
    "nose", "nose_bridge",
    "mouth_left", "mouth_right",
    "mouth_top", "mouth_bottom",
    "chin", "forehead_center",
    "cheek_left", "cheek_right",
    "jaw_left", "jaw_right",
    "lip_upper_left", "lip_upper_right",
    "lip_lower_left", "lip_lower_right"
]


# ============================================================
# Landmark Creation Functions
# ============================================================

def create_landmark(
    name: str,
    position: Tuple[float, float, float],
    parent: str = None
) -> str:
    """
    Create a landmark locator.
    
    Args:
        name: Landmark name
        position: (x, y, z) position
        parent: Parent transform (optional)
        
    Returns:
        Created locator name
    """
    # Create locator
    locator = cmds.spaceLocator(name=f"landmark_{name}")[0]
    
    # Set position
    cmds.xform(locator, worldSpace=True, translation=list(position))
    
    # Add custom attribute
    cmds.addAttr(locator, ln="faceit_landmark", dt="string")
    cmds.setAttr(f"{locator}.faceit_landmark", name, type="string")
    
    # Add to landmarks group
    if not cmds.objExists("facial_landmarks"):
        cmds.group(empty=True, name="facial_landmarks")
    
    cmds.parent(locator, "facial_landmarks")
    
    if parent:
        cmds.parent(locator, parent)
    
    return locator


def create_landmark_from_vertex(
    mesh: str,
    name: str,
    vertex_index: int
) -> Optional[str]:
    """
    Create a landmark from a mesh vertex.
    
    Args:
        mesh: Mesh object name
        name: Landmark name
        vertex_index: Vertex index
        
    Returns:
        Created locator name or None
    """
    if not cmds.objExists(mesh):
        return None
    
    # Get vertex position in world space
    vertex_pos = cmds.xform(f"{mesh}.vtx[{vertex_index}]", query=True, worldSpace=True, translation=True)
    
    if not vertex_pos:
        return None
    
    return create_landmark(name, tuple(vertex_pos))


def create_landmarks_from_vertices(
    mesh: str,
    landmark_vertex_map: Dict[str, int]
) -> List[str]:
    """
    Create multiple landmarks from mesh vertices.
    
    Args:
        mesh: Mesh object name
        landmark_vertex_map: Dictionary mapping landmark names to vertex indices
        
    Returns:
        List of created locator names
    """
    created = []
    
    for name, vertex_index in landmark_vertex_map.items():
        locator = create_landmark_from_vertex(mesh, name, vertex_index)
        if locator:
            created.append(locator)
    
    return created


# ============================================================
# Landmark Management Functions
# ============================================================

def get_landmarks() -> Dict[str, str]:
    """
    Get all Faceit landmarks.
    
    Returns:
        Dictionary mapping landmark names to locator names
    """
    landmarks = {}
    
    if not cmds.objExists("facial_landmarks"):
        return landmarks
    
    children = cmds.listRelatives("facial_landmarks", children=True) or []
    
    for child in children:
        if cmds.nodeType(child) == 'locator':
            if cmds.attributeQuery("faceit_landmark", node=child, exists=True):
                name = cmds.getAttr(f"{child}.faceit_landmark")
                if name:
                    landmarks[name] = child
    
    return landmarks


def get_landmark_position(landmark_name: str) -> Optional[Tuple[float, float, float]]:
    """
    Get the position of a landmark.
    
    Args:
        landmark_name: Landmark name
        
    Returns:
        (x, y, z) position or None
    """
    landmarks = get_landmarks()
    
    if landmark_name not in landmarks:
        return None
    
    locator = landmarks[landmark_name]
    pos = cmds.xform(locator, query=True, worldSpace=True, translation=True)
    
    if pos:
        return (pos[0], pos[1], pos[2])
    
    return None


def set_landmark_position(landmark_name: str, position: Tuple[float, float, float]) -> bool:
    """
    Set the position of a landmark.
    
    Args:
        landmark_name: Landmark name
        position: (x, y, z) position
        
    Returns:
        True if successful
    """
    landmarks = get_landmarks()
    
    if landmark_name not in landmarks:
        return False
    
    locator = landmarks[landmark_name]
    cmds.xform(locator, worldSpace=True, translation=list(position))
    
    return True


def delete_landmark(landmark_name: str) -> bool:
    """
    Delete a landmark.
    
    Args:
        landmark_name: Landmark name
        
    Returns:
        True if successful
    """
    landmarks = get_landmarks()
    
    if landmark_name not in landmarks:
        return False
    
    locator = landmarks[landmark_name]
    cmds.delete(locator)
    
    return True


def delete_all_landmarks() -> bool:
    """
    Delete all Faceit landmarks.
    
    Returns:
        True if successful
    """
    if cmds.objExists("facial_landmarks"):
        cmds.delete("facial_landmarks")
        return True
    
    return False


# ============================================================
# Landmark Snapping Functions
# ============================================================

def snap_landmark_to_mesh(
    landmark_name: str,
    mesh: str
) -> bool:
    """
    Snap a landmark to the nearest point on a mesh.
    
    Args:
        landmark_name: Landmark name
        mesh: Mesh object name
        
    Returns:
        True if successful
    """
    if not cmds.objExists(mesh):
        return False
    
    position = get_landmark_position(landmark_name)
    if position is None:
        return False
    
    # Find closest point on mesh
    closest_point = closest_point_on_mesh(position, mesh)
    if closest_point:
        return set_landmark_position(landmark_name, closest_point)
    
    return False


def snap_all_landmarks_to_mesh(mesh: str) -> int:
    """
    Snap all landmarks to the nearest points on a mesh.
    
    Args:
        mesh: Mesh object name
        
    Returns:
        Number of landmarks snapped
    """
    if not cmds.objExists(mesh):
        return 0
    
    landmarks = get_landmarks()
    snapped = 0
    
    for name in landmarks.keys():
        if snap_landmark_to_mesh(name, mesh):
            snapped += 1
    
    return snapped


def closest_point_on_mesh(
    point: Tuple[float, float, float],
    mesh: str
) -> Optional[Tuple[float, float, float]]:
    """
    Find the closest point on a mesh to a given point.
    
    Args:
        point: (x, y, z) point
        mesh: Mesh object name
        
    Returns:
        (x, y, z) closest point or None
    """
    if not cmds.objExists(mesh):
        return None
    
    # Use Maya's closest point on mesh
    # Convert to MPoint for API
    mpoint = om2.MPoint(point[0], point[1], point[2])
    
    # Get mesh data
    sel = om2.MSelectionList()
    sel.add(mesh)
    dag_path = sel.getDagPath(0)
    fn_mesh = om2.MFnMesh(dag_path)
    
    # Find closest point
    closest_point, _ = fn_mesh.getClosestPoint(mpoint, om2.MSpace.kWorld)
    
    if closest_point is not None:
        return (closest_point.x, closest_point.y, closest_point.z)
    
    return None


# ============================================================
# Landmark Export/Import Functions
# ============================================================

def export_landmarks(filepath: str) -> bool:
    """
    Export landmarks to a JSON file.
    
    Args:
        filepath: File path
        
    Returns:
        True if successful
    """
    landmarks = get_landmarks()
    
    if not landmarks:
        return False
    
    data = {}
    for name, locator in landmarks.items():
        pos = cmds.xform(locator, query=True, worldSpace=True, translation=True)
        if pos:
            data[name] = list(pos)
    
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        cmds.warning(f"Failed to export landmarks: {str(e)}")
        return False


def import_landmarks(filepath: str) -> bool:
    """
    Import landmarks from a JSON file.
    
    Args:
        filepath: File path
        
    Returns:
        True if successful
    """
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
    except Exception as e:
        cmds.warning(f"Failed to import landmarks: {str(e)}")
        return False
    
    for name, position in data.items():
        if name in get_landmarks():
            set_landmark_position(name, tuple(position))
        else:
            create_landmark(name, tuple(position))
    
    return True


# ============================================================
# Viewport Utilities
# ============================================================

def lock_3d_view_front():
    """
    Lock the 3D view to front view.
    """
    # Set view to front
    for panel in cmds.getPanel(scriptType='modelPanel'):
        if cmds.modelPanel(panel, query=True, modelEditor=True):
            cmds.modelEditor(panel, edit=True, view='front')


def unlock_3d_view():
    """
    Unlock the 3D view.
    """
    # Unlock view
    for panel in cmds.getPanel(scriptType='modelPanel'):
        if cmds.modelPanel(panel, query=True, modelEditor=True):
            cmds.modelEditor(panel, edit=True, lockView=False)