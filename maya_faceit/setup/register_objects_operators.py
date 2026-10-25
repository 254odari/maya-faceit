# register_objects_operators.py
# Maya Faceit Plugin - Register Objects Operators
# Converted from Blender to Maya Python 3.11

"""
Register objects operators for Faceit Maya plugin.
Handles object registration and management.
"""

import maya.cmds as cmds
import webbrowser
from typing import List, Dict, Optional, Any

from ..core import faceit_utils as futils
from ..core import vgroup_utils as vg_utils
from ..core import modifier_utils


# ============================================================
# Add Facial Part Operator
# ============================================================

class AddFacialPart:
    """
    Register the selected Object for Faceit Process.
    """
    
    name = "AddFacialPart"
    label = "Register Selected Object"
    
    def __init__(self):
        self.facial_part = ""
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        selection = cmds.ls(selection=True, type='transform')
        for obj in selection:
            shapes = cmds.listRelatives(obj, shapes=True, type='mesh')
            if shapes:
                return True
        return False
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        selection = cmds.ls(selection=True, type='transform')
        
        if not selection:
            cmds.warning("No objects selected.")
            return {'CANCELLED'}
        
        # Filter to mesh objects
        mesh_objects = []
        for obj in selection:
            shapes = cmds.listRelatives(obj, shapes=True, type='mesh')
            if shapes:
                mesh_objects.append(obj)
        
        if not mesh_objects:
            cmds.warning("No mesh objects selected.")
            return {'CANCELLED'}
        
        # Register objects
        if cmds.objExists("faceit_core_data"):
            if cmds.attributeQuery("faceit_objects", node="faceit_core_data", exists=True):
                current_str = cmds.getAttr("faceit_core_data.faceit_objects") or ""
                current = current_str.split(',') if current_str else []
                
                for obj in mesh_objects:
                    if obj not in current:
                        current.append(obj)
                
                cmds.setAttr("faceit_core_data.faceit_objects", ",".join(current), type="string")
        
        cmds.warning(f"Registered {len(mesh_objects)} object(s).")
        return {'FINISHED'}


# ============================================================
# Select Facial Part Operator
# ============================================================

class SelectFacialPart:
    """
    Select the corresponding object from the active list item.
    """
    
    name = "SelectFacialPart"
    label = "Select Facial Part"
    
    def __init__(self):
        self.object_name = ""
        self.clear_current_selection = True
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return True
    
    def invoke(self, context: Any) -> str:
        """Invoke the operator."""
        return self.execute(context)
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        if not self.object_name:
            cmds.warning("No object name specified.")
            return {'CANCELLED'}
        
        if cmds.objExists(self.object_name):
            if self.clear_current_selection:
                cmds.select(clear=True)
            
            cmds.select(self.object_name, add=True)
            cmds.selectMode(object=True)
        
        return {'FINISHED'}


# ============================================================
# Remove Facial Part Operator
# ============================================================

class RemoveFacialPart:
    """
    Remove the selected Character Geometry from Registration.
    """
    
    name = "RemoveFacialPart"
    label = "Remove Facial Parts"
    
    def __init__(self):
        self.prompt = False
        self.clear_vertex_groups = False
        self.remove_item = ""
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return True
    
    def invoke(self, context: Any) -> str:
        """Invoke the operator."""
        if self.prompt:
            # In Maya, we'd show a dialog
            return self.execute(context)
        else:
            return self.execute(context)
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        if not self.remove_item:
            cmds.warning("No item specified.")
            return {'CANCELLED'}
        
        # Remove from faceit objects list
        if cmds.objExists("faceit_core_data"):
            if cmds.attributeQuery("faceit_objects", node="faceit_core_data", exists=True):
                current_str = cmds.getAttr("faceit_core_data.faceit_objects") or ""
                current = current_str.split(',') if current_str else []
                
                if self.remove_item in current:
                    current.remove(self.remove_item)
                    cmds.setAttr("faceit_core_data.faceit_objects", ",".join(current), type="string")
                    
                    # Clear vertex groups if requested
                    if self.clear_vertex_groups and cmds.objExists(self.remove_item):
                        groups = vg_utils.get_vertex_groups(self.remove_item)
                        for grp in groups:
                            if grp.startswith('faceit_'):
                                vg_utils.delete_vertex_group(self.remove_item, grp)
        
        cmds.warning(f"Removed {self.remove_item} from registration.")
        return {'FINISHED'}


# ============================================================
# Clear Faceit Objects Operator
# ============================================================

class ClearFaceitObjects:
    """
    Clear all registered Faceit objects.
    """
    
    name = "ClearFaceitObjects"
    label = "Clear Facial Parts"
    
    def __init__(self):
        self.clear_vertex_groups = False
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return True
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        faceit_objects = futils.get_faceit_objects_list()
        
        if not faceit_objects:
            cmds.warning("No Faceit objects found.")
            return {'CANCELLED'}
        
        # Clear vertex groups if requested
        if self.clear_vertex_groups:
            for obj in faceit_objects:
                if cmds.objExists(obj):
                    groups = vg_utils.get_vertex_groups(obj)
                    for grp in groups:
                        if grp.startswith('faceit_'):
                            vg_utils.delete_vertex_group(obj, grp)
        
        # Clear faceit objects list
        if cmds.objExists("faceit_core_data"):
            if cmds.attributeQuery("faceit_objects", node="faceit_core_data", exists=True):
                cmds.setAttr("faceit_core_data.faceit_objects", "", type="string")
        
        cmds.warning("Cleared all Faceit objects.")
        return {'FINISHED'}


# ============================================================
# Move Face Object Operator
# ============================================================

class MoveFaceObject:
    """
    Move the Face Object to new index.
    """
    
    name = "MoveFaceObject"
    label = "Move"
    
    def __init__(self):
        self.direction = 'UP'
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return True
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        faceit_objects = futils.get_faceit_objects_list()
        
        if not faceit_objects:
            return {'CANCELLED'}
        
        # In Maya, we'd reorder the list
        # For now, just log
        cmds.warning(f"Moved object {self.direction}")
        return {'FINISHED'}


# ============================================================
# Go To Tab Operator
# ============================================================

class GoToTab:
    """
    Navigate to a specific tab.
    """
    
    name = "GoToTab"
    label = "Go To Tab"
    
    def __init__(self):
        self.tab = 'CREATE'
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        cmds.warning(f"Navigating to tab: {self.tab}")
        return {'FINISHED'}


# ============================================================
# Open Web Operator
# ============================================================

class OpenWeb:
    """
    Opens a Weblink in the Browser.
    """
    
    name = "OpenWeb"
    label = "Web Link"
    
    def __init__(self):
        self.link = "https://faceit-doc.readthedocs.io/en/latest"
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        webbrowser.open(self.link)
        cmds.warning(f"Opened: {self.link}")
        return {'FINISHED'}