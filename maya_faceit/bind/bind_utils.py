# bind_utils.py
# Maya Faceit Plugin - Bind Utilities
# Converted from Blender to Maya Python 3.11

"""
Bind utilities for Faceit Maya plugin.
Handles weight transfer, object splitting, and geometry operations.
"""

import maya.cmds as cmds # type: ignore
import maya.api.OpenMaya as om2 # type: ignore
from typing import List, Optional, Tuple, Any

from ..core import faceit_utils as futils
from ..core import mesh_utils
from ..core import vgroup_utils as vg_utils


def remove_weights_from_non_facial_geometry(
    obj: str,
    face_hull: str,
    faceit_vertex_groups: List[str]
) -> None:
    """
    Remove all weights outside of the facial area on the main face object.
    
    Args:
        obj: Main facial object
        face_hull: Convex hull that encompasses the face
        faceit_vertex_groups: Faceit vertex groups to preserve
    """
    if not cmds.objExists(obj) or not cmds.objExists(face_hull):
        return
    
    # Get skin cluster
    skin_cluster = None
    history = cmds.listHistory(obj, pruneDagObjects=True, interestLevel=2) or []
    for node in history:
        if cmds.nodeType(node) == 'skinCluster':
            skin_cluster = node
            break
    
    if not skin_cluster:
        return
    
    # Get vertices in secondary groups
    vs_secondary = set()
    for vgroup in faceit_vertex_groups:
        if vgroup == 'faceit_eyelashes':
            continue
        vertices = vg_utils.get_verts_in_vgroup(obj, vgroup)
        vs_secondary.update(vertices)
    
    # Get vertex count
    vertex_count = cmds.polyEvaluate(obj, vertex=True)
    
    # Check each vertex
    vertices_to_keep = []
    
    for i in range(vertex_count):
        if i in vs_secondary:
            continue
        
        # Get vertex position in world space
        pos = cmds.xform(f"{obj}.vtx[{i}]", query=True, worldSpace=True, translation=True)
        
        if pos:
            # Check if point is inside face hull
            if mesh_utils.is_inside_dot(tuple(pos), face_hull):
                vertices_to_keep.append(i)
    
    # Find non-facial vertices
    non_facial = [i for i in range(vertex_count) if i not in vertices_to_keep and i not in vs_secondary]
    
    # Assign non-facial vertices to DEF-face
    if non_facial:
        vg_utils.assign_vertex_grp(obj, non_facial, 'DEF-face', overwrite=True)


def scale_bind_objects(
    factor: float,
    objects: List[str],
    reverse: bool = False
) -> None:
    """
    Scale objects for binding.
    
    Args:
        factor: Scale factor
        objects: List of objects to scale
        reverse: Whether to reverse the scale
    """
    scale_factor = factor if not reverse else 1.0 / factor
    
    for obj in objects:
        if cmds.objExists(obj):
            cmds.setAttr(f"{obj}.scaleX", cmds.getAttr(f"{obj}.scaleX") * scale_factor)
            cmds.setAttr(f"{obj}.scaleY", cmds.getAttr(f"{obj}.scaleY") * scale_factor)
            cmds.setAttr(f"{obj}.scaleZ", cmds.getAttr(f"{obj}.scaleZ") * scale_factor)


def data_transfer_vertex_groups(
    obj_from: str,
    obj_to: str,
    apply: bool = True,
    method: str = ''
) -> None:
    """
    Transfer vertex groups from one object to another.
    
    Args:
        obj_from: Source object
        obj_to: Target object
        apply: Whether to apply the transfer
        method: Transfer method ('NEAREST', 'TOPOLOGY')
    """
    if not cmds.objExists(obj_from) or not cmds.objExists(obj_to):
        return
    
    # Get vertex counts
    from_count = cmds.polyEvaluate(obj_from, vertex=True)
    to_count = cmds.polyEvaluate(obj_to, vertex=True)
    
    if from_count != to_count:
        cmds.warning(f"Vertex count mismatch: {obj_from} has {from_count}, {obj_to} has {to_count}")
        return
    
    # Get vertex groups from source
    groups = vg_utils.get_vertex_groups(obj_from)
    
    for grp in groups:
        # Create group on target if it doesn't exist
        if grp not in vg_utils.get_vertex_groups(obj_to):
            vg_utils.create_vertex_group(obj_to, grp)
        
        # Copy weights
        for i in range(to_count):
            weight = vg_utils.get_vertex_group_weight(obj_from, grp, i)
            vg_utils.set_vertex_group_weight(obj_to, grp, i, weight)


def split_by_faceit_groups(obj: str) -> List[str]:
    """
    Split the object into parts by assigned Faceit vertex groups.
    
    Args:
        obj: Object to split
        
    Returns:
        List of split object names
    """
    if not cmds.objExists(obj):
        return []
    
    split_objects = []
    groups = vg_utils.get_vertex_groups(obj)
    
    # Find Faceit groups
    faceit_groups = [g for g in groups if g.startswith('faceit_')]
    
    if not faceit_groups:
        return [obj]
    
    # Create separate objects for each group
    for grp in faceit_groups:
        vertices = vg_utils.get_verts_in_vgroup(obj, grp)
        
        if not vertices:
            continue
        
        # Duplicate object
        dup = cmds.duplicate(obj, name=f"{obj}_{grp}")[0]
        
        # Delete all vertices not in this group
        vertex_count = cmds.polyEvaluate(dup, vertex=True)
        vertices_to_delete = [i for i in range(vertex_count) if i not in vertices]
        
        if vertices_to_delete:
            # In Maya, we need to use a different approach
            # Select and delete vertices
            cmds.select(clear=True)
            for vtx in vertices_to_delete:
                cmds.select(f"{dup}.vtx[{vtx}]", add=True)
            cmds.delete()
        
        # Clean up vertex groups
        for g in vg_utils.get_vertex_groups(dup):
            if g != grp:
                vg_utils.delete_vertex_group(dup, g)
        
        split_objects.append(dup)
    
    # Delete original if it was split
    if len(split_objects) > 1:
        cmds.delete(obj)
    
    return split_objects if split_objects else [obj]


def split_object(obj: str) -> List[str]:
    """
    Split an object into loose parts.
    
    Args:
        obj: Object to split
        
    Returns:
        List of split object names
    """
    if not cmds.objExists(obj):
        return []
    
    # In Maya, we can use polySeparate
    cmds.select(obj)
    cmds.polySeparate(ch=1)
    
    # Get the resulting objects
    split_objects = cmds.ls(selection=True, type='transform')
    
    # Clean up each object
    for s_obj in split_objects:
        if cmds.objExists(s_obj):
            # Remove unused vertex groups
            vg_utils.remove_unused_vertex_groups(s_obj)
    
    return split_objects


def create_facial_hull(lm_obj: str) -> Optional[str]:
    """
    Create a facial hull from landmarks.
    
    Args:
        lm_obj: Landmarks object name
        
    Returns:
        Hull object name or None
    """
    if not cmds.objExists(lm_obj):
        return None
    
    # Duplicate landmarks
    hull = cmds.duplicate(lm_obj, name="face_hull")[0]
    
    # Apply mirror if needed
    history = cmds.listHistory(hull, pruneDagObjects=True, interestLevel=2) or []
    for node in history:
        if cmds.nodeType(node) == 'mirror':
            cmds.delete(node)
    
    # Make convex hull
    cmds.select(hull)
    cmds.polyConvexHull(ch=1)
    
    # Scale up slightly
    cmds.setAttr(f"{hull}.scaleX", 2)
    cmds.setAttr(f"{hull}.scaleY", 1.1)
    cmds.setAttr(f"{hull}.scaleZ", 1.2)
    
    return hull