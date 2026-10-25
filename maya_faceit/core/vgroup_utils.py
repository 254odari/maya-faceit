# vgroup_utils.py
# Maya Faceit Plugin - Vertex Group Utilities
# Converted from Blender to Maya Python 3.11

"""
Vertex group utilities for Faceit Maya plugin.
Handles vertex group creation, management, and weight operations.
"""

import maya.cmds as cmds
import maya.api.OpenMaya as om2
from typing import List, Dict, Optional, Tuple, Any, Set

from . import faceit_utils as futils
from .modifier_utils import get_faceit_armature_modifier


# ============================================================
# Vertex Group Management Functions
# ============================================================

def get_vertex_groups(obj: str) -> List[str]:
    """
    Get all vertex group names on an object.
    
    Args:
        obj: Object name
        
    Returns:
        List of vertex group names
    """
    if not cmds.objExists(obj):
        return []
    
    return cmds.listAttr(f"{obj}.vertexGroups") or []


def get_vertex_group(obj: str, group_name: str) -> Optional[str]:
    """
    Get a vertex group by name.
    
    Args:
        obj: Object name
        group_name: Group name
        
    Returns:
        Vertex group name or None
    """
    if not cmds.objExists(obj):
        return None
    
    groups = get_vertex_groups(obj)
    
    if group_name in groups:
        return group_name
    
    return None


def create_vertex_group(obj: str, group_name: str) -> Optional[str]:
    """
    Create a vertex group on an object.
    
    Args:
        obj: Object name
        group_name: Group name
        
    Returns:
        Created group name or None
    """
    if not cmds.objExists(obj):
        return None
    
    # Check if group already exists
    if group_name in get_vertex_groups(obj):
        return group_name
    
    # Create vertex group
    cmds.vertexGroup(obj, add=group_name)
    
    return group_name


def delete_vertex_group(obj: str, group_name: str) -> bool:
    """
    Delete a vertex group from an object.
    
    Args:
        obj: Object name
        group_name: Group name
        
    Returns:
        True if successful
    """
    if not cmds.objExists(obj):
        return False
    
    if group_name not in get_vertex_groups(obj):
        return False
    
    cmds.vertexGroup(obj, remove=group_name)
    return True


def get_vertex_group_weight(obj: str, group_name: str, vertex_index: int) -> float:
    """
    Get the weight of a vertex in a vertex group.
    
    Args:
        obj: Object name
        group_name: Group name
        vertex_index: Vertex index
        
    Returns:
        Weight value
    """
    if not cmds.objExists(obj):
        return 0.0
    
    if group_name not in get_vertex_groups(obj):
        return 0.0
    
    # Check if vertex is in group
    if cmds.vertexInGroup(f"{obj}.vtx[{vertex_index}]", group_name):
        # Get weight
        return cmds.getAttr(f"{obj}.vtx[{vertex_index}].weight[{group_name}]")
    
    return 0.0


def set_vertex_group_weight(
    obj: str,
    group_name: str,
    vertex_index: int,
    weight: float
) -> bool:
    """
    Set the weight of a vertex in a vertex group.
    
    Args:
        obj: Object name
        group_name: Group name
        vertex_index: Vertex index
        weight: Weight value (0.0 to 1.0)
        
    Returns:
        True if successful
    """
    if not cmds.objExists(obj):
        return False
    
    # Ensure group exists
    if group_name not in get_vertex_groups(obj):
        create_vertex_group(obj, group_name)
    
    # Set weight
    cmds.setAttr(f"{obj}.vtx[{vertex_index}].weight[{group_name}]", weight)
    return True


# ============================================================
# Vertex Group Assignment Functions
# ============================================================

def assign_vertex_grp(
    obj: str,
    vertices: List[int],
    grp_name: str,
    overwrite: bool = False,
    mode: str = 'REPLACE'
) -> bool:
    """
    Assign vertices to a vertex group.
    
    Args:
        obj: Object name
        vertices: List of vertex indices
        grp_name: Group name
        overwrite: Whether to overwrite existing weights
        mode: Assignment mode ('REPLACE', 'ADD', 'SUBTRACT')
        
    Returns:
        True if successful
    """
    if not cmds.objExists(obj):
        return False
    
    # Ensure group exists
    if grp_name not in get_vertex_groups(obj):
        create_vertex_group(obj, grp_name)
    
    # Get current selection
    current_selection = cmds.ls(selection=True)
    
    # Select vertices
    cmds.select(clear=True)
    for vtx in vertices:
        cmds.select(f"{obj}.vtx[{vtx}]", add=True)
    
    # Assign to group
    if overwrite:
        cmds.sets(force=True, add=grp_name)
    else:
        if mode == 'REPLACE':
            cmds.sets(force=True, add=grp_name)
        elif mode == 'ADD':
            cmds.sets(add=grp_name)
        elif mode == 'SUBTRACT':
            cmds.sets(remove=grp_name)
    
    # Restore selection
    if current_selection:
        cmds.select(current_selection)
    
    return True


def remove_verts_from_grp(
    obj: str,
    vertex_group: str,
    vertices: List[int] = None
) -> bool:
    """
    Remove vertices from a vertex group.
    
    Args:
        obj: Object name
        vertex_group: Group name
        vertices: List of vertex indices (None for all)
        
    Returns:
        True if successful
    """
    if not cmds.objExists(obj):
        return False
    
    if vertex_group not in get_vertex_groups(obj):
        return False
    
    if vertices is None:
        # Remove all vertices
        vertex_count = cmds.polyEvaluate(obj, vertex=True)
        vertices = list(range(vertex_count))
    
    # Select vertices
    cmds.select(clear=True)
    for vtx in vertices:
        cmds.select(f"{obj}.vtx[{vtx}]", add=True)
    
    # Remove from group
    cmds.sets(remove=vertex_group)
    
    return True


# ============================================================
# Vertex Group Retrieval Functions
# ============================================================

def get_verts_in_vgroup(obj: str, grp_name: str) -> List[int]:
    """
    Get all vertices in a vertex group.
    
    Args:
        obj: Object name
        grp_name: Group name
        
    Returns:
        List of vertex indices
    """
    if not cmds.objExists(obj):
        return []
    
    if grp_name not in get_vertex_groups(obj):
        return []
    
    vertex_count = cmds.polyEvaluate(obj, vertex=True)
    result = []
    
    for i in range(vertex_count):
        if cmds.vertexInGroup(f"{obj}.vtx[{i}]", grp_name):
            result.append(i)
    
    return result


def get_vertex_groups_from_objects(objects: List[str] = None) -> List[str]:
    """
    Get all vertex groups from a list of objects.
    
    Args:
        objects: List of object names (uses get_faceit_objects_list if None)
        
    Returns:
        List of unique vertex group names
    """
    if objects is None:
        objects = futils.get_faceit_objects_list()
    
    vg_names = []
    
    for obj in objects:
        if not cmds.objExists(obj):
            continue
        
        groups = get_vertex_groups(obj)
        vg_names.extend(groups)
    
    return list(set(vg_names))


def get_objects_with_vertex_group(
    vgroup_name: str,
    objects: List[str] = None,
    get_all: bool = False
) -> List[str]:
    """
    Find objects with a specific vertex group.
    
    Args:
        vgroup_name: Group name
        objects: List of object names (uses get_faceit_objects_list if None)
        get_all: Whether to return all objects or just the first
        
    Returns:
        List of object names
    """
    if objects is None:
        objects = futils.get_faceit_objects_list()
    
    found_objects = []
    
    for obj in objects:
        if not cmds.objExists(obj):
            continue
        
        if vgroup_name in get_vertex_groups(obj):
            found_objects.append(obj)
            if not get_all:
                break
    
    return found_objects


# ============================================================
# Vertex Group Weight Operations
# ============================================================

def remove_all_weight(
    obj: str,
    vertices: List[int] = None,
    armature_obj: str = None
) -> bool:
    """
    Remove all weights from deform groups for specified vertices.
    
    Args:
        obj: Object name
        vertices: List of vertex indices (None for all)
        armature_obj: Armature object name
        
    Returns:
        True if successful
    """
    if not cmds.objExists(obj):
        return False
    
    # Get deform groups
    deform_groups = get_deform_bones_from_armature(armature_obj)
    
    if not deform_groups:
        return False
    
    if vertices is None:
        vertex_count = cmds.polyEvaluate(obj, vertex=True)
        vertices = list(range(vertex_count))
    
    for grp in deform_groups:
        if grp in get_vertex_groups(obj):
            for vtx in vertices:
                cmds.setAttr(f"{obj}.vtx[{vtx}].weight[{grp}]", 0.0)
    
    return True


def remove_zero_weights_from_verts(obj: str, threshold: float = 0.0) -> bool:
    """
    Remove weights below a threshold from vertices.
    
    Args:
        obj: Object name
        threshold: Weight threshold
        
    Returns:
        True if successful
    """
    if not cmds.objExists(obj):
        return False
    
    vertex_count = cmds.polyEvaluate(obj, vertex=True)
    groups = get_vertex_groups(obj)
    
    for vtx in range(vertex_count):
        for grp in groups:
            weight = get_vertex_group_weight(obj, grp, vtx)
            if weight <= threshold:
                cmds.setAttr(f"{obj}.vtx[{vtx}].weight[{grp}]", 0.0)
    
    return True


def remove_unused_vertex_groups(obj: str) -> bool:
    """
    Remove all vertex groups that have no vertices assigned.
    
    Args:
        obj: Object name
        
    Returns:
        True if successful
    """
    if not cmds.objExists(obj):
        return False
    
    groups = get_vertex_groups(obj)
    vertex_count = cmds.polyEvaluate(obj, vertex=True)
    
    for grp in groups:
        has_vertices = False
        for vtx in range(vertex_count):
            if cmds.vertexInGroup(f"{obj}.vtx[{vtx}]", grp):
                has_vertices = True
                break
        
        if not has_vertices:
            cmds.vertexGroup(obj, remove=grp)
    
    return True


def remove_unused_vertex_groups_thresh(obj: str, threshold: float = 0.0) -> bool:
    """
    Remove vertex groups with total weight below threshold.
    
    Args:
        obj: Object name
        threshold: Weight threshold
        
    Returns:
        True if successful
    """
    if not cmds.objExists(obj):
        return False
    
    groups = get_vertex_groups(obj)
    vertex_count = cmds.polyEvaluate(obj, vertex=True)
    
    for grp in groups:
        total_weight = 0.0
        for vtx in range(vertex_count):
            weight = get_vertex_group_weight(obj, grp, vtx)
            total_weight += weight
        
        if total_weight <= threshold:
            cmds.vertexGroup(obj, remove=grp)
    
    return True


# ============================================================
# Vertex Group Copy Functions
# ============================================================

def copy_vertex_groups(source_obj: str, target_obj: str) -> bool:
    """
    Copy vertex groups from source to target object.
    Both objects should have the same topology.
    
    Args:
        source_obj: Source object name
        target_obj: Target object name
        
    Returns:
        True if successful
    """
    if not cmds.objExists(source_obj) or not cmds.objExists(target_obj):
        return False
    
    # Get source groups
    source_groups = get_vertex_groups(source_obj)
    
    if not source_groups:
        return False
    
    # Get vertex counts
    source_count = cmds.polyEvaluate(source_obj, vertex=True)
    target_count = cmds.polyEvaluate(target_obj, vertex=True)
    
    if source_count != target_count:
        print(f"Vertex count mismatch: {source_obj} has {source_count}, {target_obj} has {target_count}")
        return False
    
    for grp in source_groups:
        # Create group on target if it doesn't exist
        if grp not in get_vertex_groups(target_obj):
            create_vertex_group(target_obj, grp)
        
        # Copy weights
        for vtx in range(source_count):
            weight = get_vertex_group_weight(source_obj, grp, vtx)
            set_vertex_group_weight(target_obj, grp, vtx, weight)
    
    return True


def store_vertex_group(obj: str, vertex_group: str) -> List[Tuple[int, float]]:
    """
    Store vertex group data as list of (vertex_index, weight) tuples.
    
    Args:
        obj: Object name
        vertex_group: Group name
        
    Returns:
        List of (vertex_index, weight) tuples
    """
    if not cmds.objExists(obj):
        return []
    
    if vertex_group not in get_vertex_groups(obj):
        return []
    
    vertex_count = cmds.polyEvaluate(obj, vertex=True)
    data = []
    
    for vtx in range(vertex_count):
        if cmds.vertexInGroup(f"{obj}.vtx[{vtx}]", vertex_group):
            weight = get_vertex_group_weight(obj, vertex_group, vtx)
            if weight > 0.0:
                data.append((vtx, weight))
    
    return data


def apply_vertex_group(obj: str, vertex_group: str, data: List[Tuple[int, float]]) -> bool:
    """
    Apply vertex group data to an object.
    
    Args:
        obj: Object name
        vertex_group: Group name
        data: List of (vertex_index, weight) tuples
        
    Returns:
        True if successful
    """
    if not cmds.objExists(obj):
        return False
    
    # Ensure group exists
    if vertex_group not in get_vertex_groups(obj):
        create_vertex_group(obj, vertex_group)
    
    for vtx, weight in data:
        if vtx < cmds.polyEvaluate(obj, vertex=True):
            set_vertex_group_weight(obj, vertex_group, vtx, weight)
    
    return True


# ============================================================
# Deform Bone Functions
# ============================================================

def get_deform_bones_from_armature(armature_obj: str = None, use_all: bool = False) -> List[str]:
    """
    Get all deform bones from an armature.
    
    Args:
        armature_obj: Armature object name
        use_all: Whether to return all bones
        
    Returns:
        List of bone names
    """
    if not cmds.objExists(armature_obj):
        return []
    
    deform_groups = []
    
    # Get all joints under the armature
    joints = cmds.ls(f"{armature_obj}.bones", type='joint') or []
    
    for joint in joints:
        if use_all:
            deform_groups.append(joint)
        else:
            # Check if joint has deform attribute
            if cmds.attributeQuery("deform", node=joint, exists=True):
                if cmds.getAttr(f"{joint}.deform"):
                    deform_groups.append(joint)
    
    return deform_groups


# ============================================================
# Faceit Vertex Group Functions
# ============================================================

def remove_faceit_vertex_grps(obj: str) -> List[str]:
    """
    Remove all Faceit vertex groups from an object.
    
    Args:
        obj: Object name
        
    Returns:
        List of removed group names
    """
    if not cmds.objExists(obj):
        return []
    
    groups = get_vertex_groups(obj)
    removed = []
    
    for grp in groups:
        if 'faceit' in grp.lower():
            cmds.vertexGroup(obj, remove=grp)
            removed.append(grp)
    
    return removed


def remove_deform_vertex_grps(
    obj: str,
    armature: str = None,
    remove_all: bool = False
) -> bool:
    """
    Remove deform vertex groups from an object.
    
    Args:
        obj: Object name
        armature: Armature object name
        remove_all: Whether to remove all non-Faceit groups
        
    Returns:
        True if successful
    """
    if not cmds.objExists(obj):
        return False
    
    deform_groups = []
    
    if armature:
        deform_groups = get_deform_bones_from_armature(armature)
    
    groups = get_vertex_groups(obj)
    
    for grp in groups:
        if 'faceit' not in grp.lower():
            if grp in deform_groups or remove_all:
                cmds.vertexGroup(obj, remove=grp)
    
    return True


def get_faceit_vertex_grps(
    obj: str,
    groups_filter: List[str] = None
) -> List[str]:
    """
    Get Faceit vertex groups on an object.
    
    Args:
        obj: Object name
        groups_filter: List of group names to filter by
        
    Returns:
        List of group names
    """
    if not cmds.objExists(obj):
        return []
    
    groups = get_vertex_groups(obj)
    faceit_groups = []
    
    for grp in groups:
        if groups_filter:
            if grp in groups_filter:
                faceit_groups.append(grp)
        else:
            if 'faceit' in grp.lower():
                faceit_groups.append(grp)
    
    return faceit_groups


def has_verts_without_grps(obj: str) -> bool:
    """
    Check if there are vertices without any group assignment.
    
    Args:
        obj: Object name
        
    Returns:
        True if vertices without groups exist
    """
    if not cmds.objExists(obj):
        return False
    
    vertex_count = cmds.polyEvaluate(obj, vertex=True)
    
    for vtx in range(vertex_count):
        # Check if vertex has any group
        if not cmds.vertexInGroup(f"{obj}.vtx[{vtx}]", "any"):
            return True
    
    return False


# ============================================================
# Vertex Group Inversion Functions
# ============================================================

def invert_vertex_group_weights(obj: str, vgrp: str) -> Optional[str]:
    """
    Create a new vertex group with inverted weights.
    
    Args:
        obj: Object name
        vgrp: Source vertex group name
        
    Returns:
        New group name or None
    """
    if not cmds.objExists(obj):
        return None
    
    if vgrp not in get_vertex_groups(obj):
        return None
    
    new_group_name = f"{vgrp}_invert"
    
    # Create new group
    create_vertex_group(obj, new_group_name)
    
    vertex_count = cmds.polyEvaluate(obj, vertex=True)
    
    for vtx in range(vertex_count):
        weight = get_vertex_group_weight(obj, vgrp, vtx)
        inv_weight = 1.0 - weight
        
        set_vertex_group_weight(obj, new_group_name, vtx, inv_weight)
    
    return new_group_name


# ============================================================
# Vertex Group Utilities for Maya
# ============================================================

def vertex_group_sanity_check(obj: str) -> bool:
    """
    Check if vertex group data is valid.
    
    Args:
        obj: Object name
        
    Returns:
        True if valid
    """
    if not cmds.objExists(obj):
        return False
    
    try:
        groups = get_vertex_groups(obj)
        vertex_count = cmds.polyEvaluate(obj, vertex=True)
        
        for vtx in range(vertex_count):
            for grp in groups:
                # Try to get weight
                try:
                    get_vertex_group_weight(obj, grp, vtx)
                except:
                    return False
        
        return True
    except:
        return False


def remove_vgroups_from_verts(
    obj: str,
    vertices: List[int] = None,
    filter_keep: List[str] = None
) -> bool:
    """
    Remove vertex groups from specific vertices.
    
    Args:
        obj: Object name
        vertices: List of vertex indices (None for all)
        filter_keep: List of group names to keep
        
    Returns:
        True if successful
    """
    if not cmds.objExists(obj):
        return False
    
    if vertices is None:
        vertex_count = cmds.polyEvaluate(obj, vertex=True)
        vertices = list(range(vertex_count))
    
    groups = get_vertex_groups(obj)
    
    for grp in groups:
        if filter_keep and grp in filter_keep:
            continue
        
        for vtx in vertices:
            set_vertex_group_weight(obj, grp, vtx, 0.0)
    
    return True


# ============================================================
# Scene Data Integration for Vertex Groups
# ============================================================

def save_vertex_group_data(obj: str) -> Dict:
    """
    Save all vertex group data for an object.
    
    Args:
        obj: Object name
        
    Returns:
        Dictionary of vertex group data
    """
    if not cmds.objExists(obj):
        return {}
    
    groups = get_vertex_groups(obj)
    data = {}
    
    for grp in groups:
        data[grp] = store_vertex_group(obj, grp)
    
    return data


def restore_vertex_group_data(obj: str, data: Dict) -> bool:
    """
    Restore vertex group data to an object.
    
    Args:
        obj: Object name
        data: Dictionary of vertex group data
        
    Returns:
        True if successful
    """
    if not cmds.objExists(obj):
        return False
    
    for grp, group_data in data.items():
        apply_vertex_group(obj, grp, group_data)
    
    return True