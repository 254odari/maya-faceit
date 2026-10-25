# shape_key_utils.py
# Maya Faceit Plugin - Shape Key Utilities
# Converted from Blender to Maya Python 3.11

"""
Shape key utilities for Faceit Maya plugin.
Handles blend shape management, creation, and data operations.
"""

import maya.cmds as cmds
import maya.api.OpenMaya as om2
from maya.api.OpenMaya import MPoint, MVector, MFnMesh
import numpy as np
import re
from typing import List, Dict, Optional, Tuple, Any, Set

from . import faceit_utils as futils
from . import fc_dr_utils


# ============================================================
# Shape Key Detection Functions
# ============================================================

def has_shape_keys(obj: str) -> bool:
    """
    Check if an object has shape keys (blend shapes).
    
    Args:
        obj: Object name
        
    Returns:
        True if object has blend shapes
    """
    if not cmds.objExists(obj):
        return False
    
    history = cmds.listHistory(obj, pruneDagObjects=True, interestLevel=2) or []
    
    for node in history:
        if cmds.nodeType(node) == 'blendShape':
            return True
    
    return False


def get_blend_shape_node(obj: str) -> Optional[str]:
    """
    Get the blend shape node on an object.
    
    Args:
        obj: Object name
        
    Returns:
        Blend shape node name or None
    """
    if not cmds.objExists(obj):
        return None
    
    history = cmds.listHistory(obj, pruneDagObjects=True, interestLevel=2) or []
    
    for node in history:
        if cmds.nodeType(node) == 'blendShape':
            return node
    
    return None


def get_blend_shape_targets(obj: str) -> List[str]:
    """
    Get all blend shape target names on an object.
    
    Args:
        obj: Object name
        
    Returns:
        List of target names
    """
    blend_node = get_blend_shape_node(obj)
    if not blend_node:
        return []
    
    targets = cmds.listAttr(f"{blend_node}.weight", multi=True) or []
    # Filter out weight attributes (they start with 'weight[')
    return [t for t in targets if not t.startswith('weight[')]


def get_shape_key_names_from_objects(objects: List[str] = None) -> List[str]:
    """
    Get all shape key names from a list of objects.
    
    Args:
        objects: List of object names (uses get_faceit_objects_list if None)
        
    Returns:
        List of unique shape key names
    """
    if objects is None:
        objects = futils.get_faceit_objects_list()
    
    shape_key_names = []
    
    for obj in objects:
        if not cmds.objExists(obj):
            continue
        
        targets = get_blend_shape_targets(obj)
        shape_key_names.extend(targets)
    
    return list(set(shape_key_names))


def get_shape_key_names_from_action(action: str) -> List[str]:
    """
    Get shape key names from an action.
    
    Args:
        action: Action name
        
    Returns:
        List of shape key names
    """
    if not cmds.objExists(action):
        return []
    
    shape_key_names = []
    curves = cmds.listAnimCurves(action) or []
    
    for curve in curves:
        data_path = cmds.getAttr(f"{curve}.attributeName") or ""
        
        if 'blendShape' in data_path or 'weight' in data_path:
            # Extract shape key name from data path
            # Format: blendShape.weight[target_name]
            match = re.search(r'weight\[(.*?)\]', data_path)
            if match:
                shape_key_names.append(match.group(1))
    
    return shape_key_names


# ============================================================
# Shape Key Value Functions
# ============================================================

def get_shape_key_value(obj: str, target_name: str) -> float:
    """
    Get the value of a blend shape target.
    
    Args:
        obj: Object name
        target_name: Target name
        
    Returns:
        Current weight value
    """
    blend_node = get_blend_shape_node(obj)
    if not blend_node:
        return 0.0
    
    if cmds.attributeQuery(target_name, node=blend_node, exists=True):
        return cmds.getAttr(f"{blend_node}.{target_name}")
    
    return 0.0


def set_shape_key_value(obj: str, target_name: str, value: float) -> bool:
    """
    Set the value of a blend shape target.
    
    Args:
        obj: Object name
        target_name: Target name
        value: Weight value (0.0 to 1.0)
        
    Returns:
        True if successful
    """
    blend_node = get_blend_shape_node(obj)
    if not blend_node:
        return False
    
    if cmds.attributeQuery(target_name, node=blend_node, exists=True):
        cmds.setAttr(f"{blend_node}.{target_name}", value)
        return True
    
    return False


def set_rest_position_shape_keys(
    objects: List[str] = None,
    expressions_filter: List[str] = None
) -> None:
    """
    Set all shape keys to their default (0.0) values.
    
    Args:
        objects: List of object names (uses get_faceit_objects_list if None)
        expressions_filter: List of expression names to reset (None for all)
    """
    if objects is None:
        objects = futils.get_faceit_objects_list()
    
    for obj in objects:
        if not cmds.objExists(obj):
            continue
        
        blend_node = get_blend_shape_node(obj)
        if not blend_node:
            continue
        
        targets = cmds.listAttr(f"{blend_node}.weight", multi=True) or []
        
        for target in targets:
            if target.startswith('weight['):
                continue
            
            if expressions_filter:
                if target not in expressions_filter:
                    continue
            
            cmds.setAttr(f"{blend_node}.{target}", 0.0)


# ============================================================
# Shape Key Creation Functions
# ============================================================

def create_shape_key_from_mesh(
    obj: str,
    target_mesh: str,
    target_name: str
) -> Optional[str]:
    """
    Create a blend shape target from another mesh.
    
    Args:
        obj: Object name
        target_mesh: Target mesh name
        target_name: Target name
        
    Returns:
        Created blend shape node name or None
    """
    if not cmds.objExists(obj) or not cmds.objExists(target_mesh):
        return None
    
    # Get or create blend shape node
    blend_node = get_blend_shape_node(obj)
    if not blend_node:
        blend_node = cmds.blendShape(obj, name=f"{obj}_faceit_blendShape")[0]
    
    # Add target
    cmds.blendShape(
        blend_node,
        edit=True,
        target=(obj, 0, target_mesh, 1.0)
    )
    
    # Rename target
    weight_attrs = cmds.listAttr(f"{blend_node}.weight", multi=True) or []
    weight_attrs = [a for a in weight_attrs if a.startswith('weight[')]
    
    if weight_attrs:
        last_weight = weight_attrs[-1]
        cmds.aliasAttr(target_name, f"{blend_node}.{last_weight}")
    
    return blend_node


def create_shape_key_from_delta(
    obj: str,
    delta_vertices: np.ndarray,
    target_name: str
) -> Optional[str]:
    """
    Create a blend shape target from vertex deltas.
    
    Args:
        obj: Object name
        delta_vertices: Numpy array of vertex deltas
        target_name: Target name
        
    Returns:
        Created blend shape node name or None
    """
    if not cmds.objExists(obj):
        return None
    
    # Create a temporary mesh with the delta applied
    temp_mesh = _create_temp_mesh_with_delta(obj, delta_vertices)
    
    if not temp_mesh:
        return None
    
    # Create blend shape from temp mesh
    blend_node = create_shape_key_from_mesh(obj, temp_mesh, target_name)
    
    # Clean up
    cmds.delete(temp_mesh)
    
    return blend_node


def _create_temp_mesh_with_delta(obj: str, delta_vertices: np.ndarray) -> Optional[str]:
    """
    Create a temporary mesh with delta applied.
    
    Args:
        obj: Object name
        delta_vertices: Numpy array of vertex deltas
        
    Returns:
        Temporary mesh name or None
    """
    # Duplicate mesh
    temp_mesh = cmds.duplicate(obj, name=f"{obj}_temp")[0]
    
    # Get vertex positions
    vertices = cmds.ls(f"{temp_mesh}.vtx[*]", flatten=True)
    
    for i, vtx in enumerate(vertices):
        if i < len(delta_vertices):
            pos = cmds.xform(vtx, query=True, objectSpace=True, translation=True)
            if pos:
                new_pos = [
                    pos[0] + delta_vertices[i][0],
                    pos[1] + delta_vertices[i][1],
                    pos[2] + delta_vertices[i][2]
                ]
                cmds.xform(vtx, objectSpace=True, translation=new_pos)
    
    return temp_mesh


# ============================================================
# Shape Key Data Functions
# ============================================================

def get_mesh_data(obj: str, evaluated: bool = True) -> np.ndarray:
    """
    Get mesh vertex data.
    
    Args:
        obj: Object name
        evaluated: Whether to use evaluated mesh
        
    Returns:
        Numpy array of vertex positions
    """
    if not cmds.objExists(obj):
        return np.array([])
    
    vertex_count = cmds.polyEvaluate(obj, vertex=True)
    positions = np.zeros((vertex_count, 3), dtype=np.float32)
    
    for i in range(vertex_count):
        if evaluated:
            pos = cmds.xform(f"{obj}.vtx[{i}]", query=True, worldSpace=True, translation=True)
        else:
            pos = cmds.xform(f"{obj}.vtx[{i}]", query=True, objectSpace=True, translation=True)
        
        if pos:
            positions[i] = pos
    
    return positions


def apply_matrix_to_all_mesh_data(
    mesh_data: np.ndarray,
    matrix: List[List[float]]
) -> np.ndarray:
    """
    Apply a matrix to all mesh data.
    
    Args:
        mesh_data: Numpy array of vertex positions
        matrix: 4x4 transformation matrix
        
    Returns:
        Transformed vertex positions
    """
    # Convert to homogeneous coordinates
    ones = np.ones((mesh_data.shape[0], 1))
    homogeneous = np.hstack([mesh_data, ones])
    
    # Apply matrix
    transformed = homogeneous @ np.array(matrix).T
    
    # Return 3D coordinates
    return transformed[:, :3] / transformed[:, 3:]


def store_shape_keys(obj: str) -> Dict:
    """
    Store all shape key data.
    
    Args:
        obj: Object name
        
    Returns:
        Dictionary of shape key data
    """
    sk_dict = {}
    
    if not has_shape_keys(obj):
        return sk_dict
    
    blend_node = get_blend_shape_node(obj)
    if not blend_node:
        return sk_dict
    
    vertex_count = cmds.polyEvaluate(obj, vertex=True)
    targets = get_blend_shape_targets(obj)
    
    for i, target in enumerate(targets):
        # Get target weight
        weight = get_shape_key_value(obj, target)
        
        # Get target data (we need to set weight to 1.0 and capture mesh)
        original_weight = weight
        cmds.setAttr(f"{blend_node}.{target}", 1.0)
        
        # Get mesh data at this shape
        shape_data = get_mesh_data(obj, evaluated=False)
        
        # Restore weight
        cmds.setAttr(f"{blend_node}.{target}", original_weight)
        
        # Store data
        sk_dict[target] = {
            'data': shape_data,
            'value': original_weight,
            'index': i,
        }
    
    return sk_dict


def apply_stored_shape_keys(
    obj: str,
    sk_dict: Dict,
    new_order_list: List[str] = None,
    apply_drivers: bool = True
) -> None:
    """
    Apply stored shape key data to an object.
    
    Args:
        obj: Object name
        sk_dict: Shape key data dictionary
        new_order_list: List of shape key names in desired order
        apply_drivers: Whether to apply drivers
    """
    if not sk_dict:
        return
    
    # Get or create blend shape node
    blend_node = get_blend_shape_node(obj)
    if not blend_node:
        blend_node = cmds.blendShape(obj, name=f"{obj}_faceit_blendShape")[0]
    
    # Get existing targets
    existing_targets = get_blend_shape_targets(obj)
    
    # Process in new order if specified
    reordered_shapes = []
    
    if new_order_list:
        for target_name in new_order_list:
            if target_name in sk_dict:
                reordered_shapes.append(target_name)
                _apply_shape_key_from_data(obj, target_name, sk_dict[target_name])
    
    # Process remaining shapes
    for target_name, sk_data in sk_dict.items():
        if target_name not in reordered_shapes:
            _apply_shape_key_from_data(obj, target_name, sk_data)


def _apply_shape_key_from_data(
    obj: str,
    target_name: str,
    sk_data: Dict
) -> None:
    """
    Apply a single shape key from data.
    
    Args:
        obj: Object name
        target_name: Target name
        sk_data: Shape key data dictionary
    """
    blend_node = get_blend_shape_node(obj)
    if not blend_node:
        return
    
    # Check if target already exists
    if cmds.attributeQuery(target_name, node=blend_node, exists=True):
        # Update existing target
        # Maya doesn't support direct updating of blend shape targets
        # We need to recreate it
        cmds.removeMultiInstance(f"{blend_node}.weight[{target_name}]")
    
    # Create temporary mesh with shape data
    temp_mesh = _create_mesh_from_data(obj, sk_data['data'])
    if not temp_mesh:
        return
    
    # Add as blend shape target
    cmds.blendShape(
        blend_node,
        edit=True,
        target=(obj, 0, temp_mesh, 1.0)
    )
    
    # Rename target
    weight_attrs = cmds.listAttr(f"{blend_node}.weight", multi=True) or []
    weight_attrs = [a for a in weight_attrs if a.startswith('weight[')]
    
    if weight_attrs:
        last_weight = weight_attrs[-1]
        cmds.aliasAttr(target_name, f"{blend_node}.{last_weight}")
    
    # Set value
    value = sk_data.get('value', 0.0)
    cmds.setAttr(f"{blend_node}.{target_name}", value)
    
    # Clean up
    cmds.delete(temp_mesh)


def _create_mesh_from_data(obj: str, data: np.ndarray) -> Optional[str]:
    """
    Create a temporary mesh from vertex data.
    
    Args:
        obj: Object name
        data: Numpy array of vertex positions
        
    Returns:
        Temporary mesh name or None
    """
    if data.size == 0:
        return None
    
    # Duplicate mesh
    temp_mesh = cmds.duplicate(obj, name=f"{obj}_temp_data")[0]
    
    # Set vertex positions
    vertices = cmds.ls(f"{temp_mesh}.vtx[*]", flatten=True)
    
    for i, vtx in enumerate(vertices):
        if i < len(data):
            cmds.xform(vtx, objectSpace=True, translation=list(data[i]))
    
    return temp_mesh


# ============================================================
# Shape Key Removal Functions
# ============================================================

def remove_all_sk_apply_basis(obj: str, apply_basis: bool = True) -> None:
    """
    Remove all shape keys and optionally apply basis.
    
    Args:
        obj: Object name
        apply_basis: Whether to apply basis shape
    """
    if not cmds.objExists(obj):
        return
    
    blend_node = get_blend_shape_node(obj)
    if not blend_node:
        return
    
    targets = get_blend_shape_targets(obj)
    
    for target in targets:
        cmds.removeMultiInstance(f"{blend_node}.weight[{target}]")
    
    # If applying basis, delete the blend shape node
    if apply_basis:
        cmds.delete(blend_node)


# ============================================================
# Shape Key Enum Functions
# ============================================================

def get_shape_keys_from_faceit_objects_enum() -> List[Tuple[str, str, str]]:
    """
    Get shape keys from Faceit objects as enum items.
    
    Returns:
        List of (value, label, description) tuples
    """
    shapes = []
    faceit_objects = futils.get_faceit_objects_list()
    
    if faceit_objects:
        shape_key_names = get_shape_key_names_from_objects(faceit_objects)
        
        for i, name in enumerate(shape_key_names):
            shapes.append((name, name, name, i))
    else:
        shapes.append(("None", "None", "None"))
    
    return shapes


def get_enum_shape_key_actions() -> List[Tuple[str, str, str]]:
    """
    Get all shape key actions as enum items.
    
    Returns:
        List of (value, label, description) tuples
    """
    actions = []
    
    for a in cmds.ls(type='animCurve'):
        action_name = cmds.getAttr(f"{a}.name") or a
        actions.append((action_name, action_name, action_name))
    
    if not actions:
        actions.append(("None", "None", "None"))
    
    return actions


def get_all_shape_key_actions() -> List[str]:
    """
    Get all shape key actions.
    
    Returns:
        List of action names
    """
    actions = []
    
    for a in cmds.ls(type='animCurve'):
        action_name = cmds.getAttr(f"{a}.name") or a
        actions.append(action_name)
    
    return actions


# ============================================================
# Shape Key Slider Functions
# ============================================================

def set_slider_max(
    shape_key_name: str,
    value: float,
    highest_value: bool = True
) -> None:
    """
    Set the slider maximum value for a shape key.
    
    Args:
        shape_key_name: Shape key name
        value: Maximum value
        highest_value: Whether to only set if higher than current
    """
    # In Maya, we can store this in a custom attribute
    if not cmds.objExists("faceit_shape_data"):
        return
    
    if not cmds.attributeQuery("slider_max", node="faceit_shape_data", exists=True):
        cmds.addAttr("faceit_shape_data", ln="slider_max", dt="string")
    
    # Get existing data
    data_str = cmds.getAttr("faceit_shape_data.slider_max") or "{}"
    try:
        import json
        data = json.loads(data_str)
    except:
        data = {}
    
    current_max = data.get(shape_key_name, 1.0)
    
    if highest_value:
        if value < current_max:
            return
    
    data[shape_key_name] = value
    
    cmds.setAttr("faceit_shape_data.slider_max", json.dumps(data), type="string")


def set_slider_min(
    shape_key_name: str,
    value: float,
    lowest_value: bool = True
) -> None:
    """
    Set the slider minimum value for a shape key.
    
    Args:
        shape_key_name: Shape key name
        value: Minimum value
        lowest_value: Whether to only set if lower than current
    """
    if not cmds.objExists("faceit_shape_data"):
        return
    
    if not cmds.attributeQuery("slider_min", node="faceit_shape_data", exists=True):
        cmds.addAttr("faceit_shape_data", ln="slider_min", dt="string")
    
    # Get existing data
    data_str = cmds.getAttr("faceit_shape_data.slider_min") or "{}"
    try:
        import json
        data = json.loads(data_str)
    except:
        data = {}
    
    current_min = data.get(shape_key_name, 0.0)
    
    if lowest_value:
        if value > current_min:
            return
    
    data[shape_key_name] = value
    
    cmds.setAttr("faceit_shape_data.slider_min", json.dumps(data), type="string")


# ============================================================
# Shape Key Animation Functions
# ============================================================

def keyframe_shape_key(
    obj: str,
    target_name: str,
    frame: int,
    value: float
) -> bool:
    """
    Keyframe a shape key value.
    
    Args:
        obj: Object name
        target_name: Target name
        frame: Frame number
        value: Weight value
        
    Returns:
        True if successful
    """
    blend_node = get_blend_shape_node(obj)
    if not blend_node:
        return False
    
    if not cmds.attributeQuery(target_name, node=blend_node, exists=True):
        return False
    
    # Set value
    cmds.setAttr(f"{blend_node}.{target_name}", value)
    
    # Keyframe
    cmds.setKeyframe(blend_node, attribute=target_name, t=frame)
    
    return True


def get_shape_key_animation(obj: str, target_name: str) -> Dict[int, float]:
    """
    Get animation data for a shape key.
    
    Args:
        obj: Object name
        target_name: Target name
        
    Returns:
        Dictionary mapping frame to value
    """
    blend_node = get_blend_shape_node(obj)
    if not blend_node:
        return {}
    
    if not cmds.attributeQuery(target_name, node=blend_node, exists=True):
        return {}
    
    # Get animation curves
    curves = cmds.listAnimCurves(blend_node, attribute=target_name) or []
    
    if not curves:
        return {}
    
    animation_data = {}
    curve = curves[0]
    
    keyframes = cmds.keyframe(curve, query=True, timeChange=True) or []
    values = cmds.keyframe(curve, query=True, valueChange=True) or []
    
    for t, v in zip(keyframes, values):
        animation_data[int(t)] = v
    
    return animation_data