# corrective_shape_keys_utils.py
# Maya Faceit Plugin - Corrective Shape Keys Utilities
# Converted from Blender to Maya Python 3.11

"""
Corrective shape keys utilities for Faceit Maya plugin.
Handles corrective shape key creation and management.
"""

import maya.cmds as cmds # type: ignore
import maya.api.OpenMaya as om2 # type: ignore
from typing import List, Dict, Optional, Any

from ..core import faceit_utils as futils
from ..core import shape_key_utils as sk_utils


# ============================================================
# Constants
# ============================================================

CORRECTIVE_SK_ACTION_NAME = 'faceit_corrective_shape_keys'


# ============================================================
# Corrective Shape Key Management
# ============================================================

def reevaluate_corrective_shape_keys(expression_list: List[Dict] = None, objects: List[str] = None) -> None:
    """
    Re-evaluate the keyframes and properties in correspondence to the found corrective shape keys.
    
    Args:
        expression_list: List of expression items
        objects: List of object names
    """
    if expression_list is None:
        expression_list = _get_expression_list()
    
    if objects is None:
        objects = futils.get_faceit_objects_list()
    
    for obj in objects:
        if not cmds.objExists(obj):
            continue
        
        if not sk_utils.has_shape_keys(obj):
            continue
        
        blend_node = sk_utils.get_blend_shape_node(obj)
        if not blend_node:
            continue
        
        found_corrective_shapes = False
        
        for exp_item in expression_list:
            exp_name = exp_item.get('name', '')
            corr_sk_name = f'faceit_cc_{exp_name}'
            
            if cmds.attributeQuery(corr_sk_name, node=blend_node, exists=True):
                # Set weight to 1 (mute = False in Blender means active)
                cmds.setAttr(f"{blend_node}.{corr_sk_name}", 1)
                exp_item['corr_shape_key'] = True
                keyframe_corrective_sk_action(exp_item)
                found_corrective_shapes = True
        
        if found_corrective_shapes:
            action = get_corrective_sk_action()
            if not cmds.attributeQuery("currentAction", node=blend_node, exists=True):
                cmds.addAttr(blend_node, ln="currentAction", dt="string")
            cmds.setAttr(f"{blend_node}.currentAction", action, type="string")


def mute_corrective_shape_keys(expression_list: List[Dict] = None, objects: List[str] = None) -> None:
    """
    Mute all corrective shape keys.
    
    Args:
        expression_list: List of expression items
        objects: List of object names
    """
    if expression_list is None:
        expression_list = _get_expression_list()
    
    if objects is None:
        objects = futils.get_faceit_objects_list()
    
    for obj in objects:
        if not cmds.objExists(obj):
            continue
        
        if not sk_utils.has_shape_keys(obj):
            continue
        
        blend_node = sk_utils.get_blend_shape_node(obj)
        if not blend_node:
            continue
        
        found_corrective_shapes = False
        
        for exp_item in expression_list:
            exp_name = exp_item.get('name', '')
            corr_sk_name = f'faceit_cc_{exp_name}'
            
            if cmds.attributeQuery(corr_sk_name, node=blend_node, exists=True):
                # Set weight to 0 (mute)
                cmds.setAttr(f"{blend_node}.{corr_sk_name}", 0)
                found_corrective_shapes = True
        
        if found_corrective_shapes:
            action = get_corrective_sk_action()
            if cmds.attributeQuery("currentAction", node=blend_node, exists=True):
                current = cmds.getAttr(f"{blend_node}.currentAction") or ""
                if current == action:
                    cmds.setAttr(f"{blend_node}.currentAction", "", type="string")


def get_corrective_sk_action(clear_invalid_fcurves: bool = True, create: bool = True) -> Optional[str]:
    """
    Get the corrective shape key action.
    
    Args:
        clear_invalid_fcurves: If True, remove all fcurves that are not corrective shape keys
        create: Create the action if it doesn't exist
        
    Returns:
        Action name or None
    """
    action = None
    
    if cmds.objExists(CORRECTIVE_SK_ACTION_NAME):
        action = CORRECTIVE_SK_ACTION_NAME
        
        if clear_invalid_fcurves:
            # Purge old data-paths not valid
            curves = cmds.listAnimCurves(action) or []
            for curve in curves:
                attr = cmds.getAttr(f"{curve}.attributeName") or ""
                if not attr.startswith('key_blocks["faceit_cc_') or not cmds.objExists(curve):
                    cmds.delete(curve)
    elif create:
        # Create new action
        action = cmds.createNode("animCurveUA", name=CORRECTIVE_SK_ACTION_NAME)
        cmds.setAttr(f"{action}.useFakeUser", 1)
    
    return action


def assign_corrective_sk_action(obj: str) -> None:
    """
    Assign the corrective shape key action to an object.
    
    Args:
        obj: Object name
    """
    if not cmds.objExists(obj):
        return
    
    if not sk_utils.has_shape_keys(obj):
        return
    
    blend_node = sk_utils.get_blend_shape_node(obj)
    if not blend_node:
        return
    
    action = get_corrective_sk_action()
    
    if action:
        if not cmds.attributeQuery("currentAction", node=blend_node, exists=True):
            cmds.addAttr(blend_node, ln="currentAction", dt="string")
        cmds.setAttr(f"{blend_node}.currentAction", action, type="string")


def keyframe_corrective_sk_action(expression_item: Dict) -> None:
    """
    Add keyframes for the corrective shape key corresponding to the expression item.
    
    Args:
        expression_item: Expression item dictionary
    """
    action = get_corrective_sk_action()
    
    if not action:
        return
    
    exp_name = expression_item.get('name', '')
    frame = expression_item.get('frame', 0)
    data_path = f'key_blocks["faceit_cc_{exp_name}"].value'
    
    # Remove existing curve
    curves = cmds.listAnimCurves(action) or []
    for curve in curves:
        attr = cmds.getAttr(f"{curve}.attributeName") or ""
        if attr == data_path:
            cmds.delete(curve)
            break
    
    # Create new curve
    curve = cmds.createNode("animCurveUA", name=f"{action}_{data_path.replace('.', '_')}")
    cmds.connectAttr(f"{curve}.output", f"{action}.{data_path}")
    
    # Add keyframes
    cmds.setKeyframe(curve, t=frame - 9, v=0)
    cmds.setKeyframe(curve, t=frame, v=1)
    cmds.setKeyframe(curve, t=frame + 1, v=0)


def clear_all_corrective_shape_keys(objects: List[str], expression_list: List[Dict] = None) -> None:
    """
    Clear all corrective shape keys from objects.
    
    Args:
        objects: List of object names
        expression_list: List of expression items
    """
    for obj in objects:
        if not cmds.objExists(obj):
            continue
        
        if not sk_utils.has_shape_keys(obj):
            continue
        
        blend_node = sk_utils.get_blend_shape_node(obj)
        if not blend_node:
            continue
        
        targets = sk_utils.get_blend_shape_targets(obj)
        for target in targets:
            if target.startswith('faceit_cc_'):
                cmds.removeMultiInstance(f"{blend_node}.weight[{target}]")
        
        # Check if blend shape node is empty
        targets = sk_utils.get_blend_shape_targets(obj)
        if not targets:
            cmds.delete(blend_node)
    
    if expression_list:
        for exp_item in expression_list:
            exp_item['corr_shape_key'] = False
    
    action = get_corrective_sk_action(clear_invalid_fcurves=False, create=False)
    if action and cmds.objExists(action):
        cmds.delete(action)


def remove_corrective_shape_key(expression_list: List[Dict], objects: List[str], expression_name: str = '') -> bool:
    """
    Remove a corrective shape key for a given expression from all objects.
    
    Args:
        expression_list: List of expression items
        objects: List of object names
        expression_name: Expression name
        
    Returns:
        True if successful
    """
    if not expression_name:
        return False
    
    expression_item = None
    for item in expression_list:
        if item.get('name') == expression_name:
            expression_item = item
            break
    
    if not expression_item:
        print(f"Couldn't find the expression {expression_name}")
        return False
    
    corr_sk_name = f'faceit_cc_{expression_name}'
    sk_found = False
    
    for obj in objects:
        if not cmds.objExists(obj):
            continue
        
        if not sk_utils.has_shape_keys(obj):
            continue
        
        blend_node = sk_utils.get_blend_shape_node(obj)
        if not blend_node:
            continue
        
        if cmds.attributeQuery(corr_sk_name, node=blend_node, exists=True):
            sk_found = True
            cmds.removeMultiInstance(f"{blend_node}.weight[{corr_sk_name}]")
            
            # Check if blend shape node is empty
            targets = sk_utils.get_blend_shape_targets(obj)
            if not targets:
                cmds.delete(blend_node)
    
    if not sk_found:
        return False
    
    # Check if corrective shape key is still found on any other Faceit object
    corrective_sk_cleared = True
    faceit_objects = futils.get_faceit_objects_list()
    
    for obj in faceit_objects:
        if not cmds.objExists(obj):
            continue
        
        if not sk_utils.has_shape_keys(obj):
            continue
        
        blend_node = sk_utils.get_blend_shape_node(obj)
        if not blend_node:
            continue
        
        if cmds.attributeQuery(corr_sk_name, node=blend_node, exists=True):
            corrective_sk_cleared = False
            break
    
    if corrective_sk_cleared:
        expression_item['corr_shape_key'] = False
        action = get_corrective_sk_action(clear_invalid_fcurves=False, create=False)
        if action and cmds.objExists(action):
            # Remove the fcurve
            data_path = f'key_blocks["faceit_cc_{expression_name}"].value'
            curves = cmds.listAnimCurves(action) or []
            for curve in curves:
                attr = cmds.getAttr(f"{curve}.attributeName") or ""
                if attr == data_path:
                    cmds.delete(curve)
                    break
    
    return True


def get_objects_with_corrective_shape_key_for_expression(expression_name: str = '') -> List[str]:
    """
    Get list of objects that hold a corrective shape key for the given expression.
    
    Args:
        expression_name: Expression name
        
    Returns:
        List of object names
    """
    found_sk_objects = []
    objects = futils.get_faceit_objects_list()
    
    corr_sk_name = f'faceit_cc_{expression_name}'
    
    for obj in objects:
        if not cmds.objExists(obj):
            continue
        
        if not sk_utils.has_shape_keys(obj):
            continue
        
        blend_node = sk_utils.get_blend_shape_node(obj)
        if not blend_node:
            continue
        
        if cmds.attributeQuery(corr_sk_name, node=blend_node, exists=True):
            found_sk_objects.append(obj)
    
    return found_sk_objects


# ============================================================
# Helper Functions
# ============================================================

def _get_expression_list() -> List[Dict]:
    """
    Get the expression list from scene data.
    
    Returns:
        List of expression items
    """
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery("expression_list", node="faceit_core_data", exists=True):
            data_str = cmds.getAttr("faceit_core_data.expression_list") or "[]"
            try:
                import json
                return json.loads(data_str)
            except:
                pass
    return []