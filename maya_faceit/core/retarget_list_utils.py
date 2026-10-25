# retarget_list_utils.py
# Maya Faceit Plugin - Retarget List Utilities
# Converted from Blender to Maya Python 3.11

"""
Retarget list utilities for Faceit Maya plugin.
Handles target shape management, retargeting operations, and shape mapping.
"""

import maya.cmds as cmds
from typing import List, Dict, Optional, Tuple, Any, Set
import re

from .faceit_data import FACE_REGIONS_BASE
from .faceit_utils import get_faceit_objects_list


# ============================================================
# Index and Path Utilities
# ============================================================

def get_index_from_path(path: str) -> int:
    """
    Returns the index from a path string (integer in []).
    
    Args:
        path: Path string containing [index]
        
    Returns:
        Index value or -1 if not found
    """
    if not path:
        return -1
    
    # Find index in brackets
    start = path.find('[')
    end = path.find(']')
    
    if start != -1 and end != -1 and start < end:
        try:
            return int(path[start + 1:end])
        except ValueError:
            return -1
    
    return -1


def get_index_of_parent_collection_item(item_path: str) -> int:
    """
    Returns the index of the parent item.
    
    Args:
        item_path: Path of the item
        
    Returns:
        Parent index or -1
    """
    if not item_path:
        return -1
    
    # Get parent path
    parts = item_path.split('.')
    if len(parts) >= 2:
        parent_path = '.'.join(parts[:-1])
        return get_index_from_path(parent_path)
    
    return -1


def get_index_of_collection_item(item_path: str) -> int:
    """
    Returns the index of the item in the corresponding collection.
    
    Args:
        item_path: Path of the item
        
    Returns:
        Item index or -1
    """
    return get_index_from_path(item_path)


# ============================================================
# Target Shape Utilities
# ============================================================

def get_all_set_target_shapes(
    retarget_list: List[Dict],
    region: str = None
) -> List[str]:
    """
    Return a list of all target shapes registered to all source shapes.
    
    Args:
        retarget_list: The collection property (list of dicts)
        region: Optional region filter
        
    Returns:
        List of target shape names
    """
    all_target_shapes = []
    
    for item in retarget_list:
        if region:
            if item.get('region', '').lower() != region.lower():
                continue
        
        target_shapes = item.get('target_shapes', [])
        for target_item in target_shapes:
            if isinstance(target_item, dict):
                all_target_shapes.append(target_item.get('name', ''))
            else:
                all_target_shapes.append(target_item)
    
    return all_target_shapes


def get_all_set_target_shapes_regions(retarget_list: List[Dict]) -> Dict[str, List[str]]:
    """
    Return a dict of all target shapes and their respective regions.
    
    Args:
        retarget_list: The collection property (list of dicts)
        
    Returns:
        Dictionary mapping regions to lists of target shapes
    """
    shape_region_dict = {
        'eyes': [],
        'brows': [],
        'cheeks': [],
        'nose': [],
        'mouth': [],
        'tongue': [],
        'other': [],
    }
    
    for item in retarget_list:
        target_shapes = item.get('target_shapes', [])
        if not target_shapes:
            continue
        
        region = item.get('region', 'other').lower()
        if region not in shape_region_dict:
            shape_region_dict[region] = []
        
        for target_item in target_shapes:
            if isinstance(target_item, dict):
                name = target_item.get('name', '')
            else:
                name = target_item
            
            if name and name not in shape_region_dict[region]:
                shape_region_dict[region].append(name)
    
    return shape_region_dict


def get_target_shapes_dict(
    retarget_list: List[Dict],
    force_empty_strings: bool = False
) -> Dict[str, List[str]]:
    """
    Returns a dict of source shape name and target shapes.
    
    Args:
        retarget_list: List of retarget items
        force_empty_strings: Whether to include empty target shapes
        
    Returns:
        Dictionary mapping source shapes to target shape lists
    """
    target_shapes_dict = {}
    
    for item in retarget_list:
        source_shape = item.get('name', '')
        target_shapes = item.get('target_shapes', [])
        
        target_shapes_list = []
        for target_item in target_shapes:
            if isinstance(target_item, dict):
                name = target_item.get('name', '')
            else:
                name = target_item
            
            if name:
                target_shapes_list.append(name)
        
        if target_shapes_list:
            target_shapes_dict[source_shape] = target_shapes_list
        elif force_empty_strings:
            target_shapes_dict[source_shape] = ['']
    
    return target_shapes_dict


def is_target_shape_double(
    shape_name: str,
    retarget_list: List[Dict]
) -> bool:
    """
    Check if the target shape has been registered to any source shape.
    
    Args:
        shape_name: Name of the target shape
        retarget_list: List of retarget items
        
    Returns:
        True if shape is already registered
    """
    all_target_shapes = get_all_set_target_shapes(retarget_list)
    return shape_name in all_target_shapes


def eval_target_shapes(retarget_list: List[Dict]) -> bool:
    """
    Check if any target shapes are populated in the specified list.
    
    Args:
        retarget_list: List of retarget items
        
    Returns:
        True if any target shapes exist
    """
    if not retarget_list:
        return False
    
    for item in retarget_list:
        target_shapes = item.get('target_shapes', [])
        if target_shapes:
            return True
    
    return False


def set_base_regions_from_dict(retarget_list: List[Dict]) -> None:
    """
    Set regions for shapes based on the FACE_REGIONS_BASE dictionary.
    
    Args:
        retarget_list: List of retarget items
    """
    for region, shapes in FACE_REGIONS_BASE.items():
        for shape_name in shapes:
            # Find item with this name
            for item in retarget_list:
                if item.get('name', '') == shape_name:
                    item['region'] = region
                    break
                # Also check if item name contains the shape name
                elif shape_name in item.get('name', ''):
                    item['region'] = region
                    break


# ============================================================
# Shape Key Utilities
# ============================================================

def get_all_available_shapes_names() -> List[str]:
    """
    Return a list of all available Faceit related shape names.
    
    Returns:
        List of shape names
    """
    all_expression_names = []
    
    # Get from scene data
    if cmds.objExists("faceit_core_data"):
        names_str = cmds.getAttr("faceit_core_data.expression_names") or ""
        names = names_str.split(',') if names_str else []
        all_expression_names.extend(names)
    
    # Get from retarget lists
    # This would need to access the retarget lists from the scene
    # For now, we'll return the expression names
    
    return all_expression_names


def get_target_shape_keys(
    item: Dict,
    objects: List[str]
) -> List[str]:
    """
    Get target shape keys for an item.
    
    Args:
        item: Retarget item dictionary
        objects: List of mesh object names
        
    Returns:
        List of shape key names
    """
    target_shape_keys = []
    target_shapes = item.get('target_shapes', [])
    
    for obj in objects:
        if not cmds.objExists(obj):
            continue
        
        # Check if object has blend shapes
        history = cmds.listHistory(obj, pruneDagObjects=True, interestLevel=2) or []
        blend_node = None
        
        for node in history:
            if cmds.nodeType(node) == 'blendShape':
                blend_node = node
                break
        
        if not blend_node:
            continue
        
        # Get shape keys
        for target_item in target_shapes:
            if isinstance(target_item, dict):
                name = target_item.get('name', '')
            else:
                name = target_item
            
            if name:
                # Check if shape key exists
                if cmds.attributeQuery(name, node=blend_node, exists=True):
                    target_shape_keys.append(name)
    
    return target_shape_keys


def get_invalid_target_shapes(item: Dict) -> List[str]:
    """
    Check if the target shapes for this item exist.
    
    Args:
        item: Retarget item dictionary
        
    Returns:
        List of invalid target shape names
    """
    invalid_shapes = []
    target_shapes = item.get('target_shapes', [])
    
    # Get all available shape keys from Faceit objects
    faceit_objects = get_faceit_objects_list()
    available_shapes = []
    
    for obj in faceit_objects:
        if not cmds.objExists(obj):
            continue
        
        history = cmds.listHistory(obj, pruneDagObjects=True, interestLevel=2) or []
        for node in history:
            if cmds.nodeType(node) == 'blendShape':
                targets = cmds.listAttr(f"{node}.weight", multi=True) or []
                for target in targets:
                    if target.startswith('weight'):
                        continue
                    available_shapes.append(target)
    
    for target_item in target_shapes:
        if isinstance(target_item, dict):
            name = target_item.get('name', '')
        else:
            name = target_item
        
        if name and name not in available_shapes:
            invalid_shapes.append(name)
    
    return invalid_shapes


def are_target_shapes_valid(item: Dict) -> bool:
    """
    Check if the target shapes for this item exist.
    
    Args:
        item: Retarget item dictionary
        
    Returns:
        True if all target shapes are valid
    """
    if not item.get('target_shapes', []):
        return False
    
    invalid = get_invalid_target_shapes(item)
    return len(invalid) == 0


def target_shape_key_in_registered_objects(target_shape: str) -> bool:
    """
    Check if a target shape exists in registered objects.
    
    Args:
        target_shape: Name of the target shape
        
    Returns:
        True if shape exists
    """
    faceit_objects = get_faceit_objects_list()
    
    for obj in faceit_objects:
        if not cmds.objExists(obj):
            continue
        
        history = cmds.listHistory(obj, pruneDagObjects=True, interestLevel=2) or []
        for node in history:
            if cmds.nodeType(node) == 'blendShape':
                if cmds.attributeQuery(target_shape, node=node, exists=True):
                    return True
    
    return False


# ============================================================
# Retarget List Management Utilities
# ============================================================

def create_retarget_item(
    retarget_list: List[Dict],
    name: str,
    region: str = 'other',
    target_shapes: List[str] = None
) -> Dict:
    """
    Create a new retarget item.
    
    Args:
        retarget_list: List to add to
        name: Source shape name
        region: Face region
        target_shapes: List of target shape names
        
    Returns:
        Created item dictionary
    """
    item = {
        'name': name,
        'region': region,
        'target_shapes': [],
        'amplify': 1.0,
        'use_animation': True
    }
    
    if target_shapes:
        for ts in target_shapes:
            item['target_shapes'].append({'name': ts})
    
    retarget_list.append(item)
    return item


def remove_retarget_item(
    retarget_list: List[Dict],
    name: str
) -> bool:
    """
    Remove a retarget item by name.
    
    Args:
        retarget_list: List of retarget items
        name: Name of item to remove
        
    Returns:
        True if removed successfully
    """
    for i, item in enumerate(retarget_list):
        if item.get('name', '') == name:
            retarget_list.pop(i)
            return True
    
    return False


def clear_retarget_list(retarget_list: List[Dict]) -> None:
    """
    Clear all items from a retarget list.
    
    Args:
        retarget_list: List of retarget items
    """
    retarget_list.clear()


def find_retarget_item(
    retarget_list: List[Dict],
    name: str
) -> Optional[Dict]:
    """
    Find a retarget item by name.
    
    Args:
        retarget_list: List of retarget items
        name: Name to find
        
    Returns:
        Item dictionary or None
    """
    for item in retarget_list:
        if item.get('name', '') == name:
            return item
    
    return None


def get_retarget_item_index(
    retarget_list: List[Dict],
    name: str
) -> int:
    """
    Get the index of a retarget item by name.
    
    Args:
        retarget_list: List of retarget items
        name: Name to find
        
    Returns:
        Index or -1 if not found
    """
    for i, item in enumerate(retarget_list):
        if item.get('name', '') == name:
            return i
    
    return -1


# ============================================================
# Target Shape Management Utilities
# ============================================================

def add_target_shape_to_item(
    item: Dict,
    shape_name: str
) -> bool:
    """
    Add a target shape to a retarget item.
    
    Args:
        item: Retarget item dictionary
        shape_name: Target shape name
        
    Returns:
        True if added successfully
    """
    if 'target_shapes' not in item:
        item['target_shapes'] = []
    
    # Check if already exists
    existing = [t.get('name', '') for t in item['target_shapes']]
    if shape_name in existing:
        return False
    
    item['target_shapes'].append({'name': shape_name})
    return True


def remove_target_shape_from_item(
    item: Dict,
    shape_name: str
) -> bool:
    """
    Remove a target shape from a retarget item.
    
    Args:
        item: Retarget item dictionary
        shape_name: Target shape name
        
    Returns:
        True if removed successfully
    """
    if 'target_shapes' not in item:
        return False
    
    for i, ts in enumerate(item['target_shapes']):
        if ts.get('name', '') == shape_name:
            item['target_shapes'].pop(i)
            return True
    
    return False


def clear_target_shapes_from_item(item: Dict) -> None:
    """
    Clear all target shapes from a retarget item.
    
    Args:
        item: Retarget item dictionary
    """
    if 'target_shapes' in item:
        item['target_shapes'].clear()


def get_target_shapes_for_source(
    retarget_list: List[Dict],
    source_name: str
) -> List[str]:
    """
    Get all target shapes for a source shape.
    
    Args:
        retarget_list: List of retarget items
        source_name: Source shape name
        
    Returns:
        List of target shape names
    """
    item = find_retarget_item(retarget_list, source_name)
    if not item:
        return []
    
    return [t.get('name', '') for t in item.get('target_shapes', [])]


# ============================================================
# Utility Functions for UI Lists
# ============================================================

def get_filtered_retarget_items(
    retarget_list: List[Dict],
    filter_name: str = '',
    region_filter: str = None,
    active_regions: Dict[str, bool] = None
) -> List[Dict]:
    """
    Get filtered retarget items.
    
    Args:
        retarget_list: List of retarget items
        filter_name: Name filter string
        region_filter: Region to filter by
        active_regions: Dictionary of active regions
        
    Returns:
        Filtered list of items
    """
    result = []
    
    for item in retarget_list:
        name = item.get('name', '')
        
        # Name filter
        if filter_name:
            if filter_name.lower() not in name.lower():
                continue
        
        # Region filter
        if region_filter:
            if item.get('region', 'other') != region_filter:
                continue
        
        # Active regions filter
        if active_regions:
            region = item.get('region', 'other').lower()
            if not active_regions.get(region, True):
                continue
        
        result.append(item)
    
    return result


def sort_retarget_items(
    retarget_list: List[Dict],
    key: str = 'name',
    reverse: bool = False
) -> List[Dict]:
    """
    Sort retarget items by a key.
    
    Args:
        retarget_list: List of retarget items
        key: Sort key ('name', 'region')
        reverse: Reverse sort order
        
    Returns:
        Sorted list
    """
    return sorted(retarget_list, key=lambda x: x.get(key, ''), reverse=reverse)


# ============================================================
# Expression Name Detection Utilities
# ============================================================

def get_expression_name_double_entries(
    expression_name: str,
    expression_list: List[str]
) -> str:
    """
    Add trailing number to double entries.
    Return the name with .001, .002, ... suffix if multiple entries already exist.
    
    Args:
        expression_name: The base expression name
        expression_list: List of existing expression names
        
    Returns:
        Unique expression name with suffix if needed
    """
    expression_name_final = expression_name
    
    if expression_name_final in expression_list:
        max_integer_found = 0
        
        for item_name in expression_list:
            if expression_name_final in item_name:
                # Check for numeric suffix
                if len(item_name) >= 3 and item_name[-3:].isdigit():
                    if item_name[:-4] == expression_name_final:
                        digits = int(item_name[-3:])
                        max_integer_found = max(max_integer_found, digits)
        
        if max_integer_found > 0:
            new_digits = '.' + str(max_integer_found + 1).zfill(3)
        else:
            new_digits = '.001'
        
        expression_name_final += new_digits
    
    return expression_name_final


# ============================================================
# Side Detection Utilities
# ============================================================

def get_side(expression_name: str) -> str:
    """
    Return the side (L/N/R) for the given expression name.
    
    Args:
        expression_name: Name of the expression
        
    Returns:
        'L', 'R', or 'N'
    """
    # Check for side indicators in the name
    left_patterns = ['_L', '_l', '.L', '.l', 'left', 'Left', 'LEFT']
    right_patterns = ['_R', '_r', '.R', '.r', 'right', 'Right', 'RIGHT']
    
    for pattern in left_patterns:
        if pattern in expression_name:
            return 'L'
    
    for pattern in right_patterns:
        if pattern in expression_name:
            return 'R'
    
    return 'N'


def poll_side_in_expression_name(side: str, expression_name: str) -> bool:
    """
    Check if the correct side is in the expression name.
    
    Args:
        side: 'L' or 'R'
        expression_name: Name of the expression
        
    Returns:
        True if side is found in name
    """
    if side == 'L':
        patterns = ['_L', '_l', '.L', '.l', 'left', 'Left', 'LEFT']
        return any(p in expression_name for p in patterns)
    elif side == 'R':
        patterns = ['_R', '_r', '.R', '.r', 'right', 'Right', 'RIGHT']
        return any(p in expression_name for p in patterns)
    
    return False


def get_mirror_name(side: str, expression_name: str) -> str:
    """
    Get the mirror name for an expression.
    
    Args:
        side: 'L' or 'R'
        expression_name: Name of the expression
        
    Returns:
        Mirrored expression name
    """
    if side == 'L':
        # Replace left indicators with right
        replacements = [
            ('_L', '_R'), ('_l', '_r'),
            ('.L', '.R'), ('.l', '.r'),
            ('left', 'right'), ('Left', 'Right'), ('LEFT', 'RIGHT')
        ]
    elif side == 'R':
        # Replace right indicators with left
        replacements = [
            ('_R', '_L'), ('_r', '_l'),
            ('.R', '.L'), ('.r', '.l'),
            ('right', 'left'), ('Right', 'Left'), ('RIGHT', 'LEFT')
        ]
    else:
        return ''
    
    for old, new in replacements:
        if old in expression_name:
            return expression_name.replace(old, new)
    
    return ''


# ============================================================
# Maya Scene Data Integration
# ============================================================

def load_retarget_data_from_scene() -> List[Dict]:
    """
    Load retarget data from Maya scene.
    
    Returns:
        List of retarget items
    """
    retarget_data = []
    
    if not cmds.objExists("faceit_retarget_data"):
        return retarget_data
    
    # Get data from attributes
    if cmds.attributeQuery("retarget_data", node="faceit_retarget_data", exists=True):
        data_str = cmds.getAttr("faceit_retarget_data.retarget_data") or "[]"
        try:
            import json
            retarget_data = json.loads(data_str)
        except:
            retarget_data = []
    
    return retarget_data


def save_retarget_data_to_scene(retarget_data: List[Dict]) -> bool:
    """
    Save retarget data to Maya scene.
    
    Args:
        retarget_data: List of retarget items
        
    Returns:
        True if successful
    """
    if not cmds.objExists("faceit_retarget_data"):
        cmds.createNode("transform", name="faceit_retarget_data")
        cmds.addAttr("faceit_retarget_data", ln="retarget_data", dt="string")
    
    try:
        import json
        data_str = json.dumps(retarget_data)
        cmds.setAttr("faceit_retarget_data.retarget_data", data_str, type="string")
        return True
    except Exception as e:
        cmds.warning(f"Failed to save retarget data: {str(e)}")
        return False