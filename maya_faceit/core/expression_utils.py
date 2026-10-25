# expression_utils.py
# Maya Faceit Plugin - Expression Utilities
# Converted from Blender to Maya Python 3.11

"""
Expression utilities for Faceit Maya plugin.
Handles expression management, frame operations, and expression data.
"""

import maya.cmds as cmds
from typing import List, Dict, Optional, Tuple


# ============================================================
# Expression Data Management
# ============================================================

def get_expression_data() -> Dict:
    """
    Get all expression data from the scene.
    
    Returns:
        Dictionary containing expression data
    """
    if not cmds.objExists("faceit_core_data"):
        return {}
    
    data = {
        'names': cmds.getAttr("faceit_core_data.expression_names") or "",
        'frames': cmds.getAttr("faceit_core_data.expression_frames") or "",
        'sides': cmds.getAttr("faceit_core_data.expression_sides") or "",
        'procedural': cmds.getAttr("faceit_core_data.expression_procedural") or "",
        'current_index': cmds.getAttr("faceit_core_data.current_index") or 0,
    }
    
    # Parse strings to lists
    result = {}
    for key, value in data.items():
        if key in ['names', 'sides', 'procedural']:
            result[key] = value.split(',') if value else []
        elif key == 'frames':
            result[key] = [int(x) for x in value.split(',')] if value else []
        else:
            result[key] = value
    
    return result


def save_expression_data(data: Dict) -> bool:
    """
    Save expression data to the scene.
    
    Args:
        data: Dictionary containing expression data
        
    Returns:
        True if successful
    """
    if not cmds.objExists("faceit_core_data"):
        # Create core data node
        cmds.createNode("transform", name="faceit_core_data")
        
        # Add attributes
        cmds.addAttr("faceit_core_data", ln="version", dt="string")
        cmds.addAttr("faceit_core_data", ln="expression_names", dt="string")
        cmds.addAttr("faceit_core_data", ln="expression_frames", dt="string")
        cmds.addAttr("faceit_core_data", ln="expression_sides", dt="string")
        cmds.addAttr("faceit_core_data", ln="expression_procedural", dt="string")
        cmds.addAttr("faceit_core_data", ln="current_index", attributeType="long", min=0, defaultValue=0)
    
    try:
        names_str = ','.join(data.get('names', []))
        frames_str = ','.join(str(x) for x in data.get('frames', []))
        sides_str = ','.join(data.get('sides', []))
        procedural_str = ','.join(data.get('procedural', []))
        
        cmds.setAttr("faceit_core_data.expression_names", names_str, type="string")
        cmds.setAttr("faceit_core_data.expression_frames", frames_str, type="string")
        cmds.setAttr("faceit_core_data.expression_sides", sides_str, type="string")
        cmds.setAttr("faceit_core_data.expression_procedural", procedural_str, type="string")
        
        if 'current_index' in data:
            cmds.setAttr("faceit_core_data.current_index", data['current_index'])
        
        return True
    except Exception as e:
        cmds.warning(f"Failed to save expression data: {str(e)}")
        return False


def get_expression_by_name(expression_name: str) -> Optional[Dict]:
    """
    Get expression data by name.
    
    Args:
        expression_name: Name of the expression
        
    Returns:
        Expression data or None
    """
    data = get_expression_data()
    names = data.get('names', [])
    
    for i, name in enumerate(names):
        if name == expression_name:
            return {
                'name': name,
                'frame': data['frames'][i] if i < len(data['frames']) else None,
                'side': data['sides'][i] if i < len(data['sides']) else 'N',
                'procedural': data['procedural'][i] if i < len(data['procedural']) else 'NONE',
                'index': i
            }
    
    return None


def get_expression_by_frame(frame: int) -> Optional[Dict]:
    """
    Get expression data by frame.
    
    Args:
        frame: Frame number
        
    Returns:
        Expression data or None
    """
    data = get_expression_data()
    frames = data.get('frames', [])
    names = data.get('names', [])
    
    for i, f in enumerate(frames):
        if f == frame and i < len(names):
            return {
                'name': names[i],
                'frame': f,
                'side': data['sides'][i] if i < len(data['sides']) else 'N',
                'procedural': data['procedural'][i] if i < len(data['procedural']) else 'NONE',
                'index': i
            }
    
    return None


def get_current_expression() -> Optional[Dict]:
    """
    Get the currently selected expression.
    
    Returns:
        Current expression data or None
    """
    data = get_expression_data()
    index = data.get('current_index', 0)
    names = data.get('names', [])
    
    if index < len(names):
        return {
            'name': names[index],
            'frame': data['frames'][index] if index < len(data['frames']) else None,
            'side': data['sides'][index] if index < len(data['sides']) else 'N',
            'procedural': data['procedural'][index] if index < len(data['procedural']) else 'NONE',
            'index': index
        }
    
    return None


# ============================================================
# Expression Frame Operations
# ============================================================

def go_to_expression_frame(expression_name: str) -> bool:
    """
    Go to the frame of an expression.
    
    Args:
        expression_name: Name of the expression
        
    Returns:
        True if successful
    """
    expr = get_expression_by_name(expression_name)
    if expr and expr['frame'] is not None:
        cmds.currentTime(expr['frame'])
        return True
    
    return False


def go_to_current_expression_frame() -> bool:
    """
    Go to the frame of the current expression.
    
    Returns:
        True if successful
    """
    expr = get_current_expression()
    if expr and expr['frame'] is not None:
        cmds.currentTime(expr['frame'])
        return True
    
    return False


def get_expression_frames() -> List[int]:
    """
    Get all expression frames.
    
    Returns:
        List of frame numbers
    """
    data = get_expression_data()
    return data.get('frames', [])


def get_expression_names() -> List[str]:
    """
    Get all expression names.
    
    Returns:
        List of expression names
    """
    data = get_expression_data()
    return data.get('names', [])


def get_next_expression() -> Optional[Dict]:
    """
    Get the next expression.
    
    Returns:
        Next expression data or None
    """
    data = get_expression_data()
    index = data.get('current_index', 0)
    names = data.get('names', [])
    
    next_index = index + 1
    if next_index < len(names):
        return {
            'name': names[next_index],
            'frame': data['frames'][next_index] if next_index < len(data['frames']) else None,
            'side': data['sides'][next_index] if next_index < len(data['sides']) else 'N',
            'procedural': data['procedural'][next_index] if next_index < len(data['procedural']) else 'NONE',
            'index': next_index
        }
    
    return None


def get_previous_expression() -> Optional[Dict]:
    """
    Get the previous expression.
    
    Returns:
        Previous expression data or None
    """
    data = get_expression_data()
    index = data.get('current_index', 0)
    names = data.get('names', [])
    
    prev_index = index - 1
    if prev_index >= 0:
        return {
            'name': names[prev_index],
            'frame': data['frames'][prev_index] if prev_index < len(data['frames']) else None,
            'side': data['sides'][prev_index] if prev_index < len(data['sides']) else 'N',
            'procedural': data['procedural'][prev_index] if prev_index < len(data['procedural']) else 'NONE',
            'index': prev_index
        }
    
    return None


# ============================================================
# Expression Management
# ============================================================

def add_expression(
    name: str,
    side: str = 'N',
    procedural: str = 'NONE',
    frame: int = None
) -> bool:
    """
    Add a new expression.
    
    Args:
        name: Expression name
        side: 'L', 'R', or 'N'
        procedural: Procedural type
        frame: Frame number (auto-generated if None)
        
    Returns:
        True if successful
    """
    data = get_expression_data()
    names = data.get('names', [])
    frames = data.get('frames', [])
    sides = data.get('sides', [])
    procedural_list = data.get('procedural', [])
    
    # Check for duplicates
    if name in names:
        # Add suffix
        counter = 1
        while f"{name}.{counter:03d}" in names:
            counter += 1
        name = f"{name}.{counter:03d}"
    
    # Generate frame
    if frame is None:
        frame = (len(names) + 1) * 10
    
    # Add data
    names.append(name)
    frames.append(frame)
    sides.append(side)
    procedural_list.append(procedural)
    
    data['names'] = names
    data['frames'] = frames
    data['sides'] = sides
    data['procedural'] = procedural_list
    data['current_index'] = len(names) - 1
    
    return save_expression_data(data)


def remove_expression(expression_name: str) -> bool:
    """
    Remove an expression.
    
    Args:
        expression_name: Name of the expression to remove
        
    Returns:
        True if successful
    """
    data = get_expression_data()
    names = data.get('names', [])
    
    if expression_name not in names:
        return False
    
    index = names.index(expression_name)
    
    # Remove from lists
    names.pop(index)
    data['frames'].pop(index) if index < len(data['frames']) else None
    data['sides'].pop(index) if index < len(data['sides']) else None
    data['procedural'].pop(index) if index < len(data['procedural']) else None
    
    # Update current index
    if data['current_index'] >= len(names):
        data['current_index'] = len(names) - 1
    
    return save_expression_data(data)


def clear_all_expressions() -> bool:
    """
    Clear all expressions.
    
    Returns:
        True if successful
    """
    data = {
        'names': [],
        'frames': [],
        'sides': [],
        'procedural': [],
        'current_index': 0
    }
    
    return save_expression_data(data)


# ============================================================
# Expression Side Utilities
# ============================================================

def get_expression_side(expression_name: str) -> str:
    """
    Get the side of an expression.
    
    Args:
        expression_name: Name of the expression
        
    Returns:
        'L', 'R', or 'N'
    """
    expr = get_expression_by_name(expression_name)
    if expr:
        return expr.get('side', 'N')
    return 'N'


def is_left_expression(expression_name: str) -> bool:
    """
    Check if an expression is left-sided.
    
    Args:
        expression_name: Name of the expression
        
    Returns:
        True if left-sided
    """
    side = get_expression_side(expression_name)
    return side == 'L'


def is_right_expression(expression_name: str) -> bool:
    """
    Check if an expression is right-sided.
    
    Args:
        expression_name: Name of the expression
        
    Returns:
        True if right-sided
    """
    side = get_expression_side(expression_name)
    return side == 'R'


def is_neutral_expression(expression_name: str) -> bool:
    """
    Check if an expression is neutral (both sides).
    
    Args:
        expression_name: Name of the expression
        
    Returns:
        True if neutral
    """
    side = get_expression_side(expression_name)
    return side == 'N'


def get_mirror_expression_name(expression_name: str) -> str:
    """
    Get the mirror expression name.
    
    Args:
        expression_name: Name of the expression
        
    Returns:
        Mirror expression name or empty string
    """
    side = get_expression_side(expression_name)
    
    if side == 'L':
        # Replace left indicators with right
        if '_L' in expression_name:
            return expression_name.replace('_L', '_R')
        elif '_l' in expression_name:
            return expression_name.replace('_l', '_r')
        elif 'left' in expression_name.lower():
            return expression_name.replace('left', 'right')
        elif 'Left' in expression_name:
            return expression_name.replace('Left', 'Right')
    
    elif side == 'R':
        # Replace right indicators with left
        if '_R' in expression_name:
            return expression_name.replace('_R', '_L')
        elif '_r' in expression_name:
            return expression_name.replace('_r', '_l')
        elif 'right' in expression_name.lower():
            return expression_name.replace('right', 'left')
        elif 'Right' in expression_name:
            return expression_name.replace('Right', 'Left')
    
    return ''