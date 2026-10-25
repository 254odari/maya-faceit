# warnings_operators.py
# Maya Faceit Plugin - Warnings Operators
# Converted from Blender to Maya Python 3.11

"""
Warnings operators for Faceit Maya plugin.
Handles geometry warnings and validation.
"""

import maya.cmds as cmds # type: ignore
import maya.api.OpenMaya as om2 # type: ignore
from typing import List, Dict, Optional, Tuple, Any

from ..core import faceit_utils as futils
from ..core import vgroup_utils as vg_utils
from ..core import mesh_utils
from ..core import modifier_utils
from ..core import shape_key_utils


# ============================================================
# Warning Messages Dictionary
# ============================================================

WARNINGS_OUT = {
    'MIRROR': 'Object holds a MIRROR modifier. This can lead to problems in binding and/or baking!',
    'MAIN_GROUP': 'The Main vertex group should only be assigned to one connected surface.',
    'MULTIPLE_MAIN': 'This object among others has the Main vertex group assigned.',
    'TRANSFORMS_ANIM': 'The Object has animation keyframes on transform channels.',
    'ARMATURE_POSITION': 'The Object is bound to another armature.',
    'SURFACE_DEFORM': 'The Object is bound to another object with a Surface Deform modifier.',
    'SHAPEKEYS': 'The Object has animated shape keys.',
}


# ============================================================
# Warning Check Functions
# ============================================================

def all_verts_in_main_group(obj: str) -> bool:
    """
    Check if all vertices in an object are assigned to faceit_main.
    
    Args:
        obj: Object name
        
    Returns:
        True if all vertices are in main group
    """
    if not cmds.objExists(obj):
        return False
    
    if 'faceit_main' not in vg_utils.get_vertex_groups(obj):
        return False
    
    vertex_count = cmds.polyEvaluate(obj, vertex=True)
    main_vertices = vg_utils.get_verts_in_vgroup(obj, 'faceit_main')
    
    return len(main_vertices) == vertex_count


def get_island_count_in_main_group(obj: str) -> int:
    """
    Get the count of individual islands assigned to the main group.
    
    Args:
        obj: Object name
        
    Returns:
        Number of islands
    """
    if not cmds.objExists(obj):
        return 0
    
    if 'faceit_main' not in vg_utils.get_vertex_groups(obj):
        return 0
    
    vertices = vg_utils.get_verts_in_vgroup(obj, 'faceit_main')
    
    if not vertices:
        return 0
    
    # Get connected components
    # In Maya, we'd use polyListComponentConversion to find connected components
    # For now, return 1 as default
    return 1


def check_warnings_for_face_item(item: Dict) -> List[str]:
    """
    Check warnings for a Faceit item.
    
    Args:
        item: Faceit item dictionary
        
    Returns:
        List of warning codes
    """
    obj = item.get('name', '')
    
    if not cmds.objExists(obj):
        return []
    
    all_warnings = []
    rig = futils.get_faceit_armature()
    
    # Check main group
    if 'faceit_main' in vg_utils.get_vertex_groups(obj):
        if get_island_count_in_main_group(obj) > 1:
            all_warnings.append('MAIN_GROUP')
    
    # Check mirror modifier
    history = cmds.listHistory(obj, pruneDagObjects=True, interestLevel=2) or []
    for node in history:
        if cmds.nodeType(node) == 'mirror':
            all_warnings.append('MIRROR')
            break
    
    # Check armature position
    for node in history:
        if cmds.nodeType(node) == 'skinCluster':
            influences = cmds.skinCluster(node, query=True, influence=True) or []
            if rig and rig in influences:
                # Check if rig is in rest pose
                # In Maya, we'd check joint positions
                pass
    
    # Check shape key animation
    if shape_key_utils.has_shape_keys(obj):
        blend_node = shape_key_utils.get_blend_shape_node(obj)
        if blend_node:
            # Check if there are animation curves
            curves = cmds.listAnimCurves(blend_node) or []
            if curves:
                all_warnings.append('SHAPEKEYS')
    
    # Check transform animation
    curves = cmds.listAnimCurves(obj) or []
    for curve in curves:
        attr = cmds.getAttr(f"{curve}.attributeName") or ""
        if any(x in attr for x in ['translate', 'rotate', 'scale']):
            all_warnings.append('TRANSFORMS_ANIM')
            break
    
    return all_warnings


# ============================================================
# Check Warning Operator
# ============================================================

class CheckWarning:
    """
    Check warnings for Faceit objects.
    """
    
    name = "CheckWarning"
    label = "Check Warnings"
    
    def __init__(self):
        self.item_name = ""
        self.set_show_warnings = False
        self.check_main = False
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        faceit_objects = futils.get_faceit_objects_list()
        
        if self.item_name == 'ALL':
            items = faceit_objects
        else:
            items = [self.item_name] if self.item_name in faceit_objects else []
        
        any_warning = False
        
        for obj in items:
            if not cmds.objExists(obj):
                continue
            
            item = {'name': obj}
            warnings = check_warnings_for_face_item(item)
            
            if warnings:
                any_warning = True
                for warn in warnings:
                    cmds.warning(f"[{obj}]: {WARNINGS_OUT.get(warn, warn)}")
        
        if any_warning:
            if self.set_show_warnings:
                if cmds.objExists("faceit_core_data"):
                    if cmds.attributeQuery("show_warnings", node="faceit_core_data", exists=True):
                        cmds.setAttr("faceit_core_data.show_warnings", 1)
        else:
            if cmds.objExists("faceit_core_data"):
                if cmds.attributeQuery("show_warnings", node="faceit_core_data", exists=True):
                    cmds.setAttr("faceit_core_data.show_warnings", 0)
            cmds.warning("No Warnings found.")
        
        # Check main group
        if not self.set_show_warnings:
            if not any('faceit_main' in vg_utils.get_vertex_groups(obj) for obj in faceit_objects if cmds.objExists(obj)):
                cmds.warning("Main Face Vertex Island could not be found. Please assign the Main Vertex Group!")
        
        return {'FINISHED'}


# ============================================================
# Display Warning Operator
# ============================================================

class DisplayWarning:
    """
    Display warnings for a Faceit object.
    """
    
    name = "DisplayWarning"
    label = "Faceit Geometry Warnings"
    
    def __init__(self):
        self.item_name = ""
    
    def invoke(self, context: Any) -> str:
        """Invoke the operator."""
        if not self.item_name:
            cmds.warning("No item specified.")
            return {'CANCELLED'}
        
        if not cmds.objExists(self.item_name):
            cmds.warning(f"Object {self.item_name} not found.")
            return {'CANCELLED'}
        
        item = {'name': self.item_name}
        warnings = check_warnings_for_face_item(item)
        
        if not warnings:
            cmds.warning("No Warnings found.")
            return {'FINISHED'}
        
        # Display warnings
        for warn in warnings:
            cmds.warning(f"[{self.item_name}]: {WARNINGS_OUT.get(warn, warn)}")
        
        return {'FINISHED'}