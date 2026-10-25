# rig_utils.py
# Maya Faceit Plugin - Rig Utilities
# Converted from Blender to Maya Python 3.11

"""
Rig utilities for Faceit Maya plugin.
Provides helper functions for rig generation and manipulation.
"""

import maya.cmds as cmds
import maya.api.OpenMaya as om2
from operator import attrgetter
from typing import List, Dict, Optional, Tuple, Any
import math

from ..core import faceit_utils as futils
from ..core import vgroup_utils as vg_utils


# ============================================================
# Vertex Group Utilities
# ============================================================

def get_evaluated_vertex_group_positions(obj: str, vgroup_name: str) -> Optional[List[Tuple[float, float, float]]]:
    """
    Get world location vectors for each vertex in a vertex group.
    
    Args:
        obj: Object name
        vgroup_name: Vertex group name
        
    Returns:
        List of world positions or None
    """
    if not cmds.objExists(obj):
        return None
    
    # Check if vertex group exists
    if vgroup_name not in vg_utils.get_vertex_groups(obj):
        return None
    
    # Get vertices in group
    vertices = vg_utils.get_verts_in_vgroup(obj, vgroup_name)
    
    if not vertices:
        return None
    
    # Get world positions
    positions = []
    for vtx in vertices:
        pos = cmds.xform(f"{obj}.vtx[{vtx}]", query=True, worldSpace=True, translation=True)
        if pos:
            positions.append((pos[0], pos[1], pos[2]))
    
    return positions


def get_bounds_from_locations(locations: List[Tuple[float, float, float]], axis: str) -> Optional[List[Tuple[float, float, float]]]:
    """
    Get the bounds (max, min) for the specified locations.
    
    Args:
        locations: List of Vector3 elements
        axis: Axis ('x', 'y', or 'z')
        
    Returns:
        List of [max, min] positions
    """
    if not locations:
        return None
    
    axis = axis.lower()
    if axis not in ('x', 'y', 'z'):
        return None
    
    axis_index = {'x': 0, 'y': 1, 'z': 2}[axis]
    
    max_pos = max(locations, key=lambda p: p[axis_index])
    min_pos = min(locations, key=lambda p: p[axis_index])
    
    return [max_pos, min_pos]


# ============================================================
# Constraint Utilities
# ============================================================

def reset_stretch(rig_obj: str = None, bone: str = None) -> None:
    """
    Reset stretch constraints.
    
    Args:
        rig_obj: Rig object name
        bone: Bone name
    """
    # Set frame to 1
    cmds.currentTime(1)
    
    def reset_bone_constraints(bone_name: str):
        if not cmds.objExists(bone_name):
            return
        
        constraints = cmds.listConnections(f"{bone_name}.constraints") or []
        for constraint in constraints:
            if cmds.objExists(constraint) and cmds.nodeType(constraint) == 'stretchConstraint':
                if cmds.attributeQuery("restLength", node=constraint, exists=True):
                    cmds.setAttr(f"{constraint}.restLength", 0)
    
    if bone:
        reset_bone_constraints(bone)
    elif rig_obj:
        bones = cmds.ls(f"{rig_obj}.bones", type='joint') or []
        for bone_name in bones:
            reset_bone_constraints(bone_name)


def get_bone_delta(bone1: str, bone2: str) -> List[float]:
    """
    Get object space vector between two pose bones.
    
    Args:
        bone1: First bone name
        bone2: Second bone name
        
    Returns:
        Delta vector [x, y, z]
    """
    if not cmds.objExists(bone1) or not cmds.objExists(bone2):
        return [0, 0, 0]
    
    pos1 = cmds.xform(bone1, query=True, objectSpace=True, translation=True)
    pos2 = cmds.xform(bone2, query=True, objectSpace=True, translation=True)
    
    if pos1 and pos2:
        return [pos1[0] - pos2[0], pos1[1] - pos2[1], pos1[2] - pos2[2]]
    
    return [0, 0, 0]


def set_lid_follow_constraints(rig: str, side: str = "L") -> None:
    """
    Set best follow location constraint influence on the lid bones.
    
    Args:
        rig: Rig object name
        side: Side ('L' or 'R')
    """
    if not cmds.objExists(rig):
        return
    
    # All bottom lid bones
    bot_inner_lid = f"lid.B.{side}.001"
    bot_mid_lid = f"lid.B.{side}.002"
    bot_outer_lid = f"lid.B.{side}.003"
    
    # All upper lid bones
    top_outer_lid = f"lid.T.{side}.001"
    top_mid_lid = f"lid.T.{side}.002"
    top_inner_lid = f"lid.T.{side}.003"
    
    # Check if bones exist
    if not all(cmds.objExists(b) for b in [bot_inner_lid, bot_mid_lid, bot_outer_lid,
                                            top_outer_lid, top_mid_lid, top_inner_lid]):
        return
    
    # Calculate delta vectors
    mid_delta = get_bone_delta(top_mid_lid, bot_mid_lid)
    outer_lid_delta = get_bone_delta(top_outer_lid, bot_outer_lid)
    inner_lid_delta = get_bone_delta(top_inner_lid, bot_inner_lid)
    
    # Calculate mid delta length
    mid_length = math.sqrt(mid_delta[0]**2 + mid_delta[1]**2 + mid_delta[2]**2)
    
    # Set outer lid influence
    if mid_length > 0:
        outer_lid_influence = math.sqrt(outer_lid_delta[0]**2 + outer_lid_delta[1]**2 + outer_lid_delta[2]**2) / mid_length
        inner_lid_influence = math.sqrt(inner_lid_delta[0]**2 + inner_lid_delta[1]**2 + inner_lid_delta[2]**2) / mid_length
    else:
        outer_lid_influence = 1.0
        inner_lid_influence = 1.0
    
    # Set constraint influences
    for bone_name, influence in [(top_outer_lid, outer_lid_influence),
                                  (bot_outer_lid, outer_lid_influence),
                                  (top_inner_lid, inner_lid_influence),
                                  (bot_inner_lid, inner_lid_influence)]:
        constraints = cmds.listConnections(f"{bone_name}.constraints") or []
        for constraint in constraints:
            if cmds.objExists(constraint):
                if cmds.attributeQuery("influence", node=constraint, exists=True):
                    cmds.setAttr(f"{constraint}.influence", influence)


def child_of_set_inverse(rig_obj: str = None, bone: str = None) -> None:
    """
    Set inverse for Child Of constraints.
    
    Args:
        rig_obj: Rig object name
        bone: Bone name
    """
    def set_inverse_on_bone(bone_name: str):
        if not cmds.objExists(bone_name):
            return
        
        constraints = cmds.listConnections(f"{bone_name}.constraints") or []
        for constraint in constraints:
            if cmds.objExists(constraint) and cmds.nodeType(constraint) == 'childOfConstraint':
                if cmds.attributeQuery("inverse", node=constraint, exists=True):
                    cmds.setAttr(f"{constraint}.inverse", 1)
    
    if bone:
        set_inverse_on_bone(bone)
    elif rig_obj:
        bones = cmds.ls(f"{rig_obj}.bones", type='joint') or []
        for bone_name in bones:
            set_inverse_on_bone(bone_name)


# ============================================================
# Bone Group Utilities
# ============================================================

def get_bone_groups_dict(rig: str) -> Dict[str, Dict]:
    """
    Get all bone groups from a rig.
    
    Args:
        rig: Rig object name
        
    Returns:
        Dictionary of bone groups
    """
    if not cmds.objExists(rig):
        return {}
    
    bone_groups_dict = {}
    
    # In Maya, bone groups are stored differently
    # We'll store as custom attributes on the rig
    if cmds.attributeQuery("faceit_bone_groups", node=rig, exists=True):
        import json
        data_str = cmds.getAttr(f"{rig}.faceit_bone_groups") or "{}"
        try:
            return json.loads(data_str)
        except:
            pass
    
    return {}


def set_bone_groups_from_dict(rig: str, bone_groups_dict: Dict[str, Dict]) -> None:
    """
    Set bone groups from a dictionary.
    
    Args:
        rig: Rig object name
        bone_groups_dict: Dictionary of bone groups
    """
    if not cmds.objExists(rig):
        return
    
    # Store as custom attribute
    if not cmds.attributeQuery("faceit_bone_groups", node=rig, exists=True):
        cmds.addAttr(rig, ln="faceit_bone_groups", dt="string")
    
    import json
    cmds.setAttr(f"{rig}.faceit_bone_groups", json.dumps(bone_groups_dict), type="string")