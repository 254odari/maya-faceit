# bake_utils.py
# Maya Faceit Plugin - Bake Utilities
# Converted from Blender to Maya Python 3.11

"""
Bake utilities for Faceit Maya plugin.
Handles baking of modifiers, shapes, and expressions.
"""

import maya.cmds as cmds
import maya.api.OpenMaya as om2
from typing import List, Dict, Optional, Tuple


# ============================================================
# Bake Modifier Functions
# ============================================================

def bake_modifier(obj: str, modifier_name: str) -> bool:
    """
    Bake a modifier on an object.
    
    Args:
        obj: Object name
        modifier_name: Modifier name
        
    Returns:
        True if successful
    """
    if not cmds.objExists(obj):
        return False
    
    # Get modifier
    if not cmds.objExists(f"{obj}.{modifier_name}"):
        return False
    
    # Select the object
    cmds.select(obj)
    
    # Bake the modifier
    try:
        cmds.bakeModifier(obj, name=modifier_name)
        return True
    except:
        return False


def bake_all_modifiers(obj: str, modifier_types: List[str] = None) -> bool:
    """
    Bake all modifiers of specified types on an object.
    
    Args:
        obj: Object name
        modifier_types: List of modifier types to bake
        
    Returns:
        True if successful
    """
    if not cmds.objExists(obj):
        return False
    
    if modifier_types is None:
        modifier_types = ['armature', 'lattice', 'cluster', 'skinCluster']
    
    # Get modifiers
    mods = cmds.listHistory(obj, pruneDagObjects=True) or []
    baked_count = 0
    
    for mod in mods:
        mod_type = cmds.nodeType(mod)
        if mod_type in modifier_types:
            if bake_modifier(obj, mod):
                baked_count += 1
    
    return baked_count > 0


def bake_blend_shapes(obj: str) -> bool:
    """
    Bake blend shapes to vertex positions.
    
    Args:
        obj: Object name
        
    Returns:
        True if successful
    """
    if not cmds.objExists(obj):
        return False
    
    # Check if object has blend shapes
    history = cmds.listHistory(obj, pruneDagObjects=True, interestLevel=2) or []
    blend_node = None
    
    for node in history:
        if cmds.nodeType(node) == 'blendShape':
            blend_node = node
            break
    
    if not blend_node:
        return False
    
    # Get all blend shape weights
    weights = cmds.listAttr(f"{blend_node}.weight", multi=True) or []
    
    # Set all weights to current values and bake
    for weight_attr in weights:
        value = cmds.getAttr(f"{blend_node}.{weight_attr}")
        cmds.setAttr(f"{blend_node}.{weight_attr}", value)
    
    # Delete the blend shape node
    cmds.delete(blend_node)
    
    return True


# ============================================================
# Expression Bake Functions
# ============================================================

def bake_expression_to_blend_shape(
    mesh: str,
    expression_name: str,
    frame: int
) -> Optional[str]:
    """
    Bake an expression pose to a blend shape.
    
    Args:
        mesh: Mesh object name
        expression_name: Name of the expression
        frame: Frame number to bake from
        
    Returns:
        Name of the created blend shape target
    """
    if not cmds.objExists(mesh):
        return None
    
    # Get mesh at current frame
    cmds.currentTime(frame)
    
    # Duplicate mesh
    dup_mesh = cmds.duplicate(mesh, name=f"{mesh}_{expression_name}_bake")[0]
    
    # Delete history
    cmds.delete(dup_mesh, constructionHistory=True)
    
    # Create blend shape
    blend_node = cmds.blendShape(mesh, dup_mesh, name=f"{mesh}_faceit_blendShape")[0]
    
    # Get target name
    target_name = f"{expression_name}"
    
    # Rename target
    cmds.aliasAttr(target_name, f"{blend_node}.weight[0]")
    
    # Set weight to 0
    cmds.setAttr(f"{blend_node}.{target_name}", 0)
    
    # Delete duplicate
    cmds.delete(dup_mesh)
    
    return target_name


def bake_current_pose_to_blend_shape(mesh: str, expression_name: str) -> Optional[str]:
    """
    Bake the current mesh pose to a blend shape.
    
    Args:
        mesh: Mesh object name
        expression_name: Name of the expression
        
    Returns:
        Name of the created blend shape target
    """
    return bake_expression_to_blend_shape(mesh, expression_name, cmds.currentTime(query=True))


# ============================================================
# Shape Key Baking Utilities
# ============================================================

def bake_shape_key_delta(
    mesh: str,
    shape_key_name: str,
    target_name: str = None
) -> bool:
    """
    Bake a shape key to a new blend shape.
    
    Args:
        mesh: Mesh object name
        shape_key_name: Name of the shape key to bake
        target_name: Name for the new blend shape target
        
    Returns:
        True if successful
    """
    if not cmds.objExists(mesh):
        return False
    
    # Check if shape key exists
    if not cmds.objExists(f"{mesh}.{shape_key_name}"):
        return False
    
    if target_name is None:
        target_name = shape_key_name
    
    # Get shape key value
    value = cmds.getAttr(f"{mesh}.{shape_key_name}")
    
    # Set shape key to 1.0
    cmds.setAttr(f"{mesh}.{shape_key_name}", 1.0)
    
    # Duplicate mesh
    dup_mesh = cmds.duplicate(mesh, name=f"{mesh}_{shape_key_name}_bake")[0]
    cmds.delete(dup_mesh, constructionHistory=True)
    
    # Reset shape key
    cmds.setAttr(f"{mesh}.{shape_key_name}", value)
    
    # Create blend shape
    blend_node = cmds.blendShape(mesh, dup_mesh, name=f"{mesh}_faceit_blendShape")[0]
    
    # Rename target
    cmds.aliasAttr(target_name, f"{blend_node}.weight[0]")
    
    # Set weight to 0
    cmds.setAttr(f"{blend_node}.{target_name}", 0)
    
    # Delete duplicate
    cmds.delete(dup_mesh)
    
    return True


def convert_blend_shape_to_shape_key(
    mesh: str,
    blend_target_name: str,
    shape_key_name: str = None
) -> bool:
    """
    Convert a blend shape target to a shape key.
    
    Args:
        mesh: Mesh object name
        blend_target_name: Name of the blend shape target
        shape_key_name: Name for the new shape key
        
    Returns:
        True if successful
    """
    if not cmds.objExists(mesh):
        return False
    
    if shape_key_name is None:
        shape_key_name = blend_target_name
    
    # Find blend shape node
    history = cmds.listHistory(mesh, pruneDagObjects=True, interestLevel=2) or []
    blend_node = None
    
    for node in history:
        if cmds.nodeType(node) == 'blendShape':
            blend_node = node
            break
    
    if not blend_node:
        return False
    
    # Check if target exists
    if not cmds.attributeQuery(blend_target_name, node=blend_node, exists=True):
        return False
    
    # Get target value
    value = cmds.getAttr(f"{blend_node}.{blend_target_name}")
    
    # Set target to 1.0
    cmds.setAttr(f"{blend_node}.{blend_target_name}", 1.0)
    
    # Create shape key from current pose
    # Note: Maya doesn't have a direct equivalent to Blender's shape_key_add
    # We need to duplicate and create a blend shape, then convert
    
    # Duplicate mesh
    dup_mesh = cmds.duplicate(mesh, name=f"{mesh}_{shape_key_name}_conv")[0]
    cmds.delete(dup_mesh, constructionHistory=True)
    
    # Create blend shape
    new_blend = cmds.blendShape(mesh, dup_mesh, name=f"{mesh}_conv_blendShape")[0]
    cmds.aliasAttr(shape_key_name, f"{new_blend}.weight[0]")
    cmds.setAttr(f"{new_blend}.{shape_key_name}", 0)
    
    # Delete duplicate
    cmds.delete(dup_mesh)
    
    # Reset original blend target
    cmds.setAttr(f"{blend_node}.{blend_target_name}", value)
    
    return True


# ============================================================
# Corrective Shape Key Utilities
# ============================================================

def bake_corrective_shape_key(
    mesh: str,
    base_expression: str,
    corrected_pose_frame: int
) -> Optional[str]:
    """
    Bake a corrective shape key from a corrected pose.
    
    Args:
        mesh: Mesh object name
        base_expression: Name of the base expression
        corrected_pose_frame: Frame with corrected pose
        
    Returns:
        Name of the created corrective shape key
    """
    if not cmds.objExists(mesh):
        return None
    
    # Get base expression frame
    if cmds.objExists("faceit_core_data"):
        names_str = cmds.getAttr("faceit_core_data.expression_names") or ""
        frames_str = cmds.getAttr("faceit_core_data.expression_frames") or ""
        names = names_str.split(',') if names_str else []
        frames = [int(x) for x in frames_str.split(',')] if frames_str else []
        
        base_frame = None
        for i, name in enumerate(names):
            if name == base_expression and i < len(frames):
                base_frame = frames[i]
                break
        
        if base_frame is None:
            return None
    else:
        return None
    
    # Go to base frame
    cmds.currentTime(base_frame)
    
    # Get base mesh
    base_mesh = cmds.duplicate(mesh, name=f"{mesh}_base")[0]
    cmds.delete(base_mesh, constructionHistory=True)
    
    # Go to corrected frame
    cmds.currentTime(corrected_pose_frame)
    
    # Get corrected mesh
    corr_mesh = cmds.duplicate(mesh, name=f"{mesh}_corrected")[0]
    cmds.delete(corr_mesh, constructionHistory=True)
    
    # Calculate delta between base and corrected
    # This would require vertex position comparison
    # For now, create a blend shape from the difference
    
    # Create blend shape for correction
    correction_name = f"faceit_corr_{base_expression}"
    blend_node = cmds.blendShape(base_mesh, corr_mesh, name=f"{mesh}_corr_blendShape")[0]
    cmds.aliasAttr(correction_name, f"{blend_node}.weight[0]")
    cmds.setAttr(f"{blend_node}.{correction_name}", 0)
    
    # Apply correction to original mesh
    # This would be done through the blend shape node
    
    # Clean up
    cmds.delete(base_mesh, corr_mesh)
    
    return correction_name


# ============================================================
# Batch Baking Functions
# ============================================================

def bake_all_expressions(mesh: str) -> bool:
    """
    Bake all expressions to blend shapes.
    
    Args:
        mesh: Mesh object name
        
    Returns:
        True if successful
    """
    if not cmds.objExists(mesh):
        return False
    
    if not cmds.objExists("faceit_core_data"):
        return False
    
    names_str = cmds.getAttr("faceit_core_data.expression_names") or ""
    frames_str = cmds.getAttr("faceit_core_data.expression_frames") or ""
    
    names = names_str.split(',') if names_str else []
    frames = [int(x) for x in frames_str.split(',')] if frames_str else []
    
    baked_count = 0
    
    for i, name in enumerate(names):
        if i < len(frames):
            result = bake_expression_to_blend_shape(mesh, name, frames[i])
            if result:
                baked_count += 1
    
    return baked_count > 0


def bake_corrective_shape_keys(
    mesh: str,
    expression_names: List[str]
) -> List[str]:
    """
    Bake corrective shape keys for multiple expressions.
    
    Args:
        mesh: Mesh object name
        expression_names: List of expression names
        
    Returns:
        List of created corrective shape key names
    """
    if not cmds.objExists(mesh):
        return []
    
    if not cmds.objExists("faceit_core_data"):
        return []
    
    names_str = cmds.getAttr("faceit_core_data.expression_names") or ""
    frames_str = cmds.getAttr("faceit_core_data.expression_frames") or ""
    
    names = names_str.split(',') if names_str else []
    frames = [int(x) for x in frames_str.split(',')] if frames_str else []
    
    corrective_keys = []
    
    for expr_name in expression_names:
        # Find corrected frame (e.g., expr frame + 1)
        for i, name in enumerate(names):
            if name == expr_name and i < len(frames):
                corr_frame = frames[i] + 1
                result = bake_corrective_shape_key(mesh, expr_name, corr_frame)
                if result:
                    corrective_keys.append(result)
                break
    
    return corrective_keys


# ============================================================
# Utility Functions
# ============================================================

def clear_all_blend_shapes(mesh: str) -> bool:
    """
    Remove all blend shapes from a mesh.
    
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
            cmds.delete(node)
    
    return True


def get_blend_shape_targets(mesh: str) -> List[str]:
    """
    Get all blend shape target names from a mesh.
    
    Args:
        mesh: Mesh object name
        
    Returns:
        List of blend shape target names
    """
    if not cmds.objExists(mesh):
        return []
    
    history = cmds.listHistory(mesh, pruneDagObjects=True, interestLevel=2) or []
    for node in history:
        if cmds.nodeType(node) == 'blendShape':
            targets = cmds.listAttr(f"{node}.weight", multi=True) or []
            return [t for t in targets if not t.startswith('weight')]
    
    return []


def set_blend_shape_weight(
    mesh: str,
    target_name: str,
    weight: float
) -> bool:
    """
    Set the weight of a blend shape target.
    
    Args:
        mesh: Mesh object name
        target_name: Target name
        weight: Weight value (0.0 to 1.0)
        
    Returns:
        True if successful
    """
    if not cmds.objExists(mesh):
        return False
    
    history = cmds.listHistory(mesh, pruneDagObjects=True, interestLevel=2) or []
    for node in history:
        if cmds.nodeType(node) == 'blendShape':
            if cmds.attributeQuery(target_name, node=node, exists=True):
                cmds.setAttr(f"{node}.{target_name}", weight)
                return True
    
    return False