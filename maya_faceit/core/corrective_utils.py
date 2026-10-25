# corrective_utils.py
# Maya Faceit Plugin - Corrective Shape Utilities
# Converted from Blender to Maya Python 3.11

"""
Corrective shape utilities for Faceit Maya plugin.
Handles corrective shape key creation, management, and evaluation.
"""

import maya.cmds as cmds
import maya.api.OpenMaya as om2
from typing import List, Dict, Optional, Tuple
import numpy as np


# ============================================================
# Corrective Shape Key Management
# ============================================================

CORRECTIVE_SK_PREFIX = "faceit_cc_"


def create_corrective_shape_key(
    mesh: str,
    expression_name: str,
    base_frame: int,
    corrected_frame: int
) -> Optional[str]:
    """
    Create a corrective shape key from a corrected pose.
    
    Args:
        mesh: Mesh object name
        expression_name: Name of the expression
        base_frame: Frame with base expression
        corrected_frame: Frame with corrected pose
        
    Returns:
        Name of the created corrective shape key
    """
    if not cmds.objExists(mesh):
        return None
    
    # Get vertex positions at base frame
    cmds.currentTime(base_frame)
    base_positions = _get_vertex_positions(mesh)
    
    # Get vertex positions at corrected frame
    cmds.currentTime(corrected_frame)
    corrected_positions = _get_vertex_positions(mesh)
    
    # Calculate delta
    delta_positions = corrected_positions - base_positions
    
    # Create shape key name
    sk_name = f"{CORRECTIVE_SK_PREFIX}{expression_name}"
    
    # Check if shape key already exists
    if cmds.objExists(f"{mesh}.{sk_name}"):
        cmds.delete(f"{mesh}.{sk_name}")
    
    # Create shape key
    # In Maya, we need to create a blend shape target
    # First, duplicate the mesh at base frame
    cmds.currentTime(base_frame)
    dup_mesh = cmds.duplicate(mesh, name=f"{mesh}_temp")[0]
    cmds.delete(dup_mesh, constructionHistory=True)
    
    # Apply delta to duplicate
    _apply_delta_to_mesh(dup_mesh, delta_positions)
    
    # Create blend shape from duplicate
    blend_node = cmds.blendShape(mesh, dup_mesh, name=f"{mesh}_corr_blendShape")[0]
    cmds.aliasAttr(sk_name, f"{blend_node}.weight[0]")
    cmds.setAttr(f"{blend_node}.{sk_name}", 0)
    
    # Clean up
    cmds.delete(dup_mesh)
    
    # Store corrective data
    _store_corrective_data(mesh, expression_name, sk_name, base_frame, corrected_frame)
    
    return sk_name


def _get_vertex_positions(mesh: str) -> np.ndarray:
    """
    Get vertex positions of a mesh.
    
    Args:
        mesh: Mesh object name
        
    Returns:
        Numpy array of vertex positions
    """
    if not cmds.objExists(mesh):
        return np.array([])
    
    vertices = cmds.ls(f"{mesh}.vtx[*]", flatten=True)
    positions = []
    
    for vtx in vertices:
        pos = cmds.xform(vtx, query=True, worldSpace=True, translation=True)
        if pos:
            positions.append(pos)
    
    return np.array(positions)


def _apply_delta_to_mesh(mesh: str, delta: np.ndarray):
    """
    Apply delta to mesh vertices.
    
    Args:
        mesh: Mesh object name
        delta: Numpy array of delta positions
    """
    if not cmds.objExists(mesh):
        return
    
    vertices = cmds.ls(f"{mesh}.vtx[*]", flatten=True)
    
    for i, vtx in enumerate(vertices):
        if i < len(delta):
            current_pos = cmds.xform(vtx, query=True, worldSpace=True, translation=True)
            if current_pos:
                new_pos = [
                    current_pos[0] + delta[i][0],
                    current_pos[1] + delta[i][1],
                    current_pos[2] + delta[i][2]
                ]
                cmds.xform(vtx, worldSpace=True, translation=new_pos)


def _store_corrective_data(
    mesh: str,
    expression_name: str,
    sk_name: str,
    base_frame: int,
    corrected_frame: int
):
    """
    Store corrective shape data.
    
    Args:
        mesh: Mesh object name
        expression_name: Expression name
        sk_name: Shape key name
        base_frame: Base frame
        corrected_frame: Corrected frame
    """
    if not cmds.objExists("faceit_core_data"):
        return
    
    # Get existing corrective data
    data_str = cmds.getAttr("faceit_core_data.corrective_data") or "{}"
    try:
        import json
        data = json.loads(data_str)
    except:
        data = {}
    
    # Add corrective data
    if mesh not in data:
        data[mesh] = {}
    
    data[mesh][expression_name] = {
        'sk_name': sk_name,
        'base_frame': base_frame,
        'corrected_frame': corrected_frame
    }
    
    # Save data
    cmds.setAttr("faceit_core_data.corrective_data", json.dumps(data), type="string")


# ============================================================
# Corrective Shape Key Evaluation
# ============================================================

def evaluate_corrective_shape_key(
    mesh: str,
    expression_name: str,
    weight: float = 1.0
) -> bool:
    """
    Evaluate a corrective shape key.
    
    Args:
        mesh: Mesh object name
        expression_name: Expression name
        weight: Weight value
        
    Returns:
        True if successful
    """
    sk_name = f"{CORRECTIVE_SK_PREFIX}{expression_name}"
    
    # Find blend shape node
    history = cmds.listHistory(mesh, pruneDagObjects=True, interestLevel=2) or []
    for node in history:
        if cmds.nodeType(node) == 'blendShape':
            if cmds.attributeQuery(sk_name, node=node, exists=True):
                cmds.setAttr(f"{node}.{sk_name}", weight)
                return True
    
    return False


def get_corrective_shape_keys(mesh: str) -> List[str]:
    """
    Get all corrective shape keys on a mesh.
    
    Args:
        mesh: Mesh object name
        
    Returns:
        List of corrective shape key names
    """
    if not cmds.objExists(mesh):
        return []
    
    corrective_keys = []
    
    history = cmds.listHistory(mesh, pruneDagObjects=True, interestLevel=2) or []
    for node in history:
        if cmds.nodeType(node) == 'blendShape':
            targets = cmds.listAttr(f"{node}.weight", multi=True) or []
            for target in targets:
                if target.startswith(CORRECTIVE_SK_PREFIX):
                    corrective_keys.append(target)
    
    return corrective_keys


def remove_corrective_shape_key(mesh: str, expression_name: str) -> bool:
    """
    Remove a corrective shape key.
    
    Args:
        mesh: Mesh object name
        expression_name: Expression name
        
    Returns:
        True if successful
    """
    sk_name = f"{CORRECTIVE_SK_PREFIX}{expression_name}"
    
    history = cmds.listHistory(mesh, pruneDagObjects=True, interestLevel=2) or []
    for node in history:
        if cmds.nodeType(node) == 'blendShape':
            if cmds.attributeQuery(sk_name, node=node, exists=True):
                # Remove the target
                cmds.removeMultiInstance(f"{node}.weight[{sk_name}]")
                return True
    
    return False


def clear_all_corrective_shape_keys(mesh: str) -> bool:
    """
    Clear all corrective shape keys from a mesh.
    
    Args:
        mesh: Mesh object name
        
    Returns:
        True if successful
    """
    if not cmds.objExists(mesh):
        return False
    
    history = cmds.listHistory(mesh, pruneDagObjects=True, interestLevel=2) or []
    for node in history:
        if cmds.nodeType(node) == 'blendShape':
            targets = cmds.listAttr(f"{node}.weight", multi=True) or []
            for target in targets:
                if target.startswith(CORRECTIVE_SK_PREFIX):
                    cmds.removeMultiInstance(f"{node}.weight[{target}]")
    
    return True


# ============================================================
# Corrective Shape Key Baking
# ============================================================

def bake_corrective_shape_key_to_mesh(mesh: str, expression_name: str) -> bool:
    """
    Bake a corrective shape key to the mesh.
    
    Args:
        mesh: Mesh object name
        expression_name: Expression name
        
    Returns:
        True if successful
    """
    sk_name = f"{CORRECTIVE_SK_PREFIX}{expression_name}"
    
    # Find blend shape node
    history = cmds.listHistory(mesh, pruneDagObjects=True, interestLevel=2) or []
    blend_node = None
    
    for node in history:
        if cmds.nodeType(node) == 'blendShape':
            if cmds.attributeQuery(sk_name, node=node, exists=True):
                blend_node = node
                break
    
    if not blend_node:
        return False
    
    # Get current weight
    weight = cmds.getAttr(f"{blend_node}.{sk_name}")
    
    # Set weight to 1.0 to apply correction
    cmds.setAttr(f"{blend_node}.{sk_name}", 1.0)
    
    # Duplicate mesh
    dup_mesh = cmds.duplicate(mesh, name=f"{mesh}_baked")[0]
    cmds.delete(dup_mesh, constructionHistory=True)
    
    # Create new blend shape from baked mesh
    new_blend = cmds.blendShape(mesh, dup_mesh, name=f"{mesh}_baked_blendShape")[0]
    cmds.aliasAttr(sk_name, f"{new_blend}.weight[0]")
    cmds.setAttr(f"{new_blend}.{sk_name}", 0)
    
    # Restore original weight
    cmds.setAttr(f"{blend_node}.{sk_name}", weight)
    
    # Clean up
    cmds.delete(dup_mesh)
    cmds.delete(blend_node)
    
    return True


# ============================================================
# Corrective Shape Key Mirroring
# ============================================================

def mirror_corrective_shape_key(
    mesh: str,
    source_expression: str,
    target_expression: str,
    axis: str = 'X'
) -> bool:
    """
    Mirror a corrective shape key.
    
    Args:
        mesh: Mesh object name
        source_expression: Source expression name
        target_expression: Target expression name
        axis: Mirror axis ('X', 'Y', or 'Z')
        
    Returns:
        True if successful
    """
    source_sk = f"{CORRECTIVE_SK_PREFIX}{source_expression}"
    target_sk = f"{CORRECTIVE_SK_PREFIX}{target_expression}"
    
    # Find source blend shape
    history = cmds.listHistory(mesh, pruneDagObjects=True, interestLevel=2) or []
    source_blend = None
    
    for node in history:
        if cmds.nodeType(node) == 'blendShape':
            if cmds.attributeQuery(source_sk, node=node, exists=True):
                source_blend = node
                break
    
    if not source_blend:
        return False
    
    # Get source weight
    source_weight = cmds.getAttr(f"{source_blend}.{source_sk}")
    
    # Set source weight to 1.0
    cmds.setAttr(f"{source_blend}.{source_sk}", 1.0)
    
    # Duplicate mesh
    dup_mesh = cmds.duplicate(mesh, name=f"{mesh}_mirror")[0]
    cmds.delete(dup_mesh, constructionHistory=True)
    
    # Mirror duplicate across axis
    _mirror_mesh(dup_mesh, axis)
    
    # Create mirrored blend shape
    new_blend = cmds.blendShape(mesh, dup_mesh, name=f"{mesh}_mirror_blendShape")[0]
    cmds.aliasAttr(target_sk, f"{new_blend}.weight[0]")
    cmds.setAttr(f"{new_blend}.{target_sk}", 0)
    
    # Restore source weight
    cmds.setAttr(f"{source_blend}.{source_sk}", source_weight)
    
    # Clean up
    cmds.delete(dup_mesh)
    
    return True


def _mirror_mesh(mesh: str, axis: str = 'X'):
    """
    Mirror a mesh across an axis.
    
    Args:
        mesh: Mesh object name
        axis: Mirror axis ('X', 'Y', or 'Z')
    """
    if not cmds.objExists(mesh):
        return
    
    vertices = cmds.ls(f"{mesh}.vtx[*]", flatten=True)
    
    axis_index = {'X': 0, 'Y': 1, 'Z': 2}[axis]
    
    for vtx in vertices:
        pos = cmds.xform(vtx, query=True, worldSpace=True, translation=True)
        if pos:
            pos[axis_index] = -pos[axis_index]
            cmds.xform(vtx, worldSpace=True, translation=pos)
    
    # Flip normals
    cmds.polyNormal(mesh, normalMode=0, userNormalMode=0, ch=1)


# ============================================================
# Corrective Shape Key Utilities
# ============================================================

def get_corrective_data(mesh: str) -> Dict:
    """
    Get corrective data for a mesh.
    
    Args:
        mesh: Mesh object name
        
    Returns:
        Dictionary of corrective data
    """
    if not cmds.objExists("faceit_core_data"):
        return {}
    
    data_str = cmds.getAttr("faceit_core_data.corrective_data") or "{}"
    try:
        import json
        data = json.loads(data_str)
        return data.get(mesh, {})
    except:
        return {}


def is_corrective_shape_key(sk_name: str) -> bool:
    """
    Check if a name is a corrective shape key.
    
    Args:
        sk_name: Shape key name
        
    Returns:
        True if it's a corrective shape key
    """
    return sk_name.startswith(CORRECTIVE_SK_PREFIX)


def get_expression_from_corrective_sk(sk_name: str) -> str:
    """
    Get the expression name from a corrective shape key name.
    
    Args:
        sk_name: Shape key name
        
    Returns:
        Expression name
    """
    if sk_name.startswith(CORRECTIVE_SK_PREFIX):
        return sk_name[len(CORRECTIVE_SK_PREFIX):]
    return ""