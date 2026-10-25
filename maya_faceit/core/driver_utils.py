# driver_utils.py
# Maya Faceit Plugin - Driver Utilities
# Converted from Blender to Maya Python 3.11

"""
Driver utilities for Faceit Maya plugin.
Handles driver creation, management, and expression evaluation.
"""

import maya.cmds as cmds
import maya.api.OpenMaya as om2
from typing import List, Dict, Optional, Tuple, Any


# ============================================================
# Driver Creation Functions
# ============================================================

def create_driver(
    target_attr: str,
    expression: str,
    variables: Dict[str, Dict] = None
) -> Optional[str]:
    """
    Create a driver on an attribute.
    
    Args:
        target_attr: Target attribute (e.g., 'bone.translateX')
        expression: Driver expression
        variables: Dictionary of variables (name -> {target, data_path})
        
    Returns:
        Created driver name or None
    """
    # Parse target object and attribute
    if '.' in target_attr:
        obj, attr = target_attr.split('.', 1)
    else:
        obj = target_attr
        attr = 'translateX'
    
    if not cmds.objExists(obj):
        return None
    
    # Add driver
    cmds.setKeyframe(obj, attribute=attr, t=0, v=0)
    
    # Get the animation curve
    curves = cmds.listAnimCurves(obj, attribute=attr) or []
    if not curves:
        return None
    
    curve = curves[0]
    
    # Add driver
    driver = cmds.createNode("driver", name=f"{obj}_{attr}_driver")
    cmds.connectAttr(f"{driver}.output", f"{curve}.driver")
    
    # Set expression
    if expression:
        cmds.setAttr(f"{driver}.expression", expression, type="string")
    
    # Add variables
    if variables:
        for var_name, var_data in variables.items():
            var = cmds.createNode("driverVariable", name=f"{driver}_{var_name}")
            cmds.connectAttr(f"{var}.output", f"{driver}.variables[0]")
            cmds.setAttr(f"{var}.name", var_name, type="string")
            
            if 'type' in var_data:
                cmds.setAttr(f"{var}.type", var_data['type'])
            
            if 'target' in var_data and 'data_path' in var_data:
                target = var_data['target']
                data_path = var_data['data_path']
                
                target_node = cmds.createNode("driverTarget", name=f"{var}_target")
                cmds.connectAttr(f"{target_node}.output", f"{var}.targets[0]")
                
                cmds.setAttr(f"{target_node}.dataPath", data_path, type="string")
                cmds.connectAttr(f"{target}.message", f"{target_node}.id")
    
    return driver


def create_expression_driver(
    target_obj: str,
    target_attr: str,
    expression: str,
    variables: Dict[str, Dict]
) -> Optional[str]:
    """
    Create a driver with an expression.
    
    Args:
        target_obj: Target object name
        target_attr: Target attribute name
        expression: Driver expression
        variables: Dictionary of variables
        
    Returns:
        Created driver name or None
    """
    target_attr_path = f"{target_obj}.{target_attr}"
    return create_driver(target_attr_path, expression, variables)


# ============================================================
# Driver Management Functions
# ============================================================

def get_driver_on_attribute(attr_path: str) -> Optional[str]:
    """
    Get the driver on an attribute.
    
    Args:
        attr_path: Attribute path (e.g., 'bone.translateX')
        
    Returns:
        Driver name or None
    """
    # Parse target object and attribute
    if '.' in attr_path:
        obj, attr = attr_path.split('.', 1)
    else:
        return None
    
    if not cmds.objExists(obj):
        return None
    
    # Get animation curves
    curves = cmds.listAnimCurves(obj, attribute=attr) or []
    
    for curve in curves:
        # Check if curve has a driver
        drivers = cmds.listConnections(f"{curve}.driver") or []
        if drivers:
            return drivers[0]
    
    return None


def remove_driver(attr_path: str) -> bool:
    """
    Remove a driver from an attribute.
    
    Args:
        attr_path: Attribute path (e.g., 'bone.translateX')
        
    Returns:
        True if successful
    """
    driver = get_driver_on_attribute(attr_path)
    
    if driver:
        cmds.delete(driver)
        return True
    
    return False


def get_driver_expression(driver: str) -> str:
    """
    Get the expression from a driver.
    
    Args:
        driver: Driver name
        
    Returns:
        Expression string
    """
    if not cmds.objExists(driver):
        return ""
    
    if cmds.attributeQuery("expression", node=driver, exists=True):
        return cmds.getAttr(f"{driver}.expression") or ""
    
    return ""


def set_driver_expression(driver: str, expression: str) -> bool:
    """
    Set the expression on a driver.
    
    Args:
        driver: Driver name
        expression: Driver expression
        
    Returns:
        True if successful
    """
    if not cmds.objExists(driver):
        return False
    
    if cmds.attributeQuery("expression", node=driver, exists=True):
        cmds.setAttr(f"{driver}.expression", expression, type="string")
        return True
    
    return False


def get_driver_variables(driver: str) -> Dict[str, Dict]:
    """
    Get variables from a driver.
    
    Args:
        driver: Driver name
        
    Returns:
        Dictionary of variables
    """
    if not cmds.objExists(driver):
        return {}
    
    variables = {}
    var_connections = cmds.listConnections(f"{driver}.variables") or []
    
    for var in var_connections:
        if not cmds.objExists(var):
            continue
        
        var_name = cmds.getAttr(f"{var}.name") if cmds.attributeQuery("name", node=var, exists=True) else ""
        
        if not var_name:
            continue
        
        var_data = {
            'type': cmds.getAttr(f"{var}.type") if cmds.attributeQuery("type", node=var, exists=True) else 0,
            'targets': []
        }
        
        # Get targets
        targets = cmds.listConnections(f"{var}.targets") or []
        
        for target in targets:
            if not cmds.objExists(target):
                continue
            
            target_data = {
                'data_path': cmds.getAttr(f"{target}.dataPath") if cmds.attributeQuery("dataPath", node=target, exists=True) else "",
            }
            
            # Get target ID
            id_connections = cmds.listConnections(f"{target}.id") or []
            if id_connections:
                target_data['target'] = id_connections[0]
            
            var_data['targets'].append(target_data)
        
        variables[var_name] = var_data
    
    return variables


# ============================================================
# Driver Utility Functions
# ============================================================

def add_driver_variable(
    driver: str,
    var_name: str,
    target: str,
    data_path: str,
    var_type: int = 0
) -> bool:
    """
    Add a variable to a driver.
    
    Args:
        driver: Driver name
        var_name: Variable name
        target: Target object
        data_path: Data path
        var_type: Variable type
        
    Returns:
        True if successful
    """
    if not cmds.objExists(driver):
        return False
    
    # Create variable
    var = cmds.createNode("driverVariable", name=f"{driver}_{var_name}")
    cmds.connectAttr(f"{var}.output", f"{driver}.variables[0]")
    
    cmds.setAttr(f"{var}.name", var_name, type="string")
    cmds.setAttr(f"{var}.type", var_type)
    
    # Create target
    target_node = cmds.createNode("driverTarget", name=f"{var}_target")
    cmds.connectAttr(f"{target_node}.output", f"{var}.targets[0]")
    
    cmds.setAttr(f"{target_node}.dataPath", data_path, type="string")
    cmds.connectAttr(f"{target}.message", f"{target_node}.id")
    
    return True


def remove_driver_variable(driver: str, var_name: str) -> bool:
    """
    Remove a variable from a driver.
    
    Args:
        driver: Driver name
        var_name: Variable name
        
    Returns:
        True if successful
    """
    if not cmds.objExists(driver):
        return False
    
    variables = get_driver_variables(driver)
    
    if var_name in variables:
        # Find and delete the variable node
        var_connections = cmds.listConnections(f"{driver}.variables") or []
        for var in var_connections:
            if cmds.getAttr(f"{var}.name") == var_name:
                cmds.delete(var)
                return True
    
    return False


def update_driver(driver: str) -> bool:
    """
    Force update a driver.
    
    Args:
        driver: Driver name
        
    Returns:
        True if successful
    """
    if not cmds.objExists(driver):
        return False
    
    # Force evaluation by setting a dummy value
    if cmds.attributeQuery("expression", node=driver, exists=True):
        current_expr = cmds.getAttr(f"{driver}.expression") or ""
        cmds.setAttr(f"{driver}.expression", current_expr, type="string")
    
    return True


# ============================================================
# Faceit-Specific Drivers
# ============================================================

def create_faceit_mouth_lock_driver(rig: str) -> bool:
    """
    Create the mouth lock driver for Faceit rig.
    
    Args:
        rig: Rig object name
        
    Returns:
        True if successful
    """
    if not cmds.objExists(rig):
        return False
    
    driver_data_paths = [
        'pose.bones["MCH-jaw_master"].constraints["Copy Transforms.001"].influence',
        'pose.bones["MCH-jaw_master.001"].constraints["Copy Transforms.001"].influence',
        'pose.bones["MCH-jaw_master.002"].constraints["Copy Transforms.001"].influence',
        'pose.bones["MCH-jaw_master.003"].constraints["Copy Transforms.001"].influence',
    ]
    
    # Create driver for each constraint influence
    for data_path in driver_data_paths:
        # Parse the constraint path
        parts = data_path.split('.')
        if len(parts) >= 2:
            constraint = parts[0]
            attr = '.'.join(parts[1:])
            
            if cmds.objExists(constraint):
                create_driver(
                    f"{constraint}.{attr}",
                    "mouth_lock",
                    {
                        'mouth_lock': {
                            'target': rig,
                            'data_path': 'jaw_master.mouth_lock'
                        }
                    }
                )
    
    return True


def create_faceit_eye_driver(rig: str) -> bool:
    """
    Create eye drivers for Faceit rig.
    
    Args:
        rig: Rig object name
        
    Returns:
        True if successful
    """
    if not cmds.objExists(rig):
        return False
    
    # Create eye look drivers
    eye_attrs = [
        ('eye.L', 'translateX', 'eye_look_x'),
        ('eye.L', 'translateY', 'eye_look_y'),
        ('eye.R', 'translateX', 'eye_look_x'),
        ('eye.R', 'translateY', 'eye_look_y'),
    ]
    
    for obj, attr, var_name in eye_attrs:
        if cmds.objExists(obj):
            create_driver(
                f"{obj}.{attr}",
                var_name,
                {
                    var_name: {
                        'target': rig,
                        'data_path': f'eyes.{var_name}'
                    }
                }
            )
    
    return True