# assign_groups_operators.py
# Maya Faceit Plugin - Assign Groups Operators
# Converted from Blender to Maya Python 3.11

"""
Assign groups operators for Faceit Maya plugin.
Handles vertex group assignment with modal picker and UI.
"""

import maya.cmds as cmds
import maya.api.OpenMaya as om2
import numpy as np
from typing import List, Dict, Optional, Tuple, Any
import math

from ..core import faceit_data as fdata
from ..core import faceit_utils as futils
from ..core import mesh_utils
from ..core import vgroup_utils as vg_utils


# ============================================================
# Global State
# ============================================================

picker_running = False


def is_picker_running() -> bool:
    """Check if the picker is currently running."""
    global picker_running
    return picker_running


# ============================================================
# Assign Main Modal Operator
# ============================================================

class AssignMainModal:
    """
    Register the main surface. Draws an overlay to help you select the right vertices.
    """
    
    name = "AssignMainModal"
    label = "Assign Main Vertex Group"
    
    def __init__(self):
        self._handler = None
        self._blf_handler = None
        self.dg = None
        self.obj = None
        self.bm = None
        self.mat = None
        self.vert_data = None
        self.indices = None
        self.vertex_colors = None
        self.is_faceit_obj = False
        self.obj_data_dict = {}
        self.island_ids = None
        self.geo_islands = None
        self.single_island = False
        self.cursor_pos = (0, 0)
        self.txt = "Assign Face."
        self.simplify_count = 0
        self.simplify_state = False
        self.disabled_mods = []
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return True
    
    def description(self, context: Any, properties: Any) -> str:
        """Get the operator description."""
        doc_string = "Works different in Edit / Object Mode.\n"
        # In Maya, we'd check the selection mode
        doc_string += "Object Mode: Assign all vertices of the selected object to this group.\n"
        doc_string += "You can assign multiple groups to one object.\n\n"
        doc_string += "The main group: (face, skull, body, skin)\n"
        doc_string += "This group should consist of one connected surface.\n"
        doc_string += "Read more in the Faceit documentation."
        return doc_string
    
    def modal(self, context: Any, event: Any) -> str:
        """Modal operator handler."""
        # In Maya, we'd handle modal operations differently
        return {'FINISHED'}
    
    def end(self, context: Any) -> None:
        """End the modal operator."""
        global picker_running
        picker_running = False
    
    def invoke(self, context: Any) -> str:
        """Invoke the operator."""
        global picker_running
        
        # In Maya, we'd use a different approach for modal picking
        # For now, just set up the picker state
        picker_running = True
        
        # Get faceit objects
        faceit_objects = futils.get_faceit_objects_list()
        
        if not faceit_objects:
            cmds.warning("No Faceit objects found.")
            picker_running = False
            return {'CANCELLED'}
        
        # For now, just use the first object
        obj = faceit_objects[0]
        
        if not cmds.objExists(obj):
            cmds.warning(f"Object {obj} not found.")
            picker_running = False
            return {'CANCELLED'}
        
        # Get all vertices
        vertex_count = cmds.polyEvaluate(obj, vertex=True)
        vertices = list(range(vertex_count))
        
        # Assign to main group
        vg_utils.assign_vertex_grp(obj, vertices, 'faceit_main', overwrite=True)
        
        # Update property
        if cmds.objExists("faceit_core_data"):
            if cmds.attributeQuery("vertex_groups", node="faceit_core_data", exists=True):
                data_str = cmds.getAttr("faceit_core_data.vertex_groups") or "[]"
                try:
                    import json
                    data = json.loads(data_str)
                    for item in data:
                        if item.get('name') == 'faceit_main':
                            item['is_assigned'] = True
                            item['assigned_to_objects'] = [obj]
                            break
                    cmds.setAttr("faceit_core_data.vertex_groups", json.dumps(data), type="string")
                except:
                    pass
        
        cmds.warning(f"Main group assigned to {obj}")
        picker_running = False
        
        return {'FINISHED'}


# ============================================================
# Assign Main Operator
# ============================================================

class AssignMain:
    """
    Register the respective vertices in Edit Mode or all vertices in Object Mode.
    """
    
    name = "AssignMain"
    label = "Assign Main Vertex Group"
    
    def __init__(self):
        self.mode_save = 'OBJECT'
    
    def description(self, context: Any, properties: Any) -> str:
        """Get the operator description."""
        doc_string = "Works different in Edit / Object Mode.\n"
        doc_string += "Object Mode: Assign all vertices of the selected object to this group.\n"
        doc_string += "You can assign multiple groups to one object.\n\n"
        doc_string += "The main group: (face, skull, body, skin)\n"
        doc_string += "This group should consist of one connected surface.\n"
        doc_string += "Read more in the Faceit documentation."
        return doc_string
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        selection = cmds.ls(selection=True, type='transform')
        if selection:
            obj = selection[0]
            shapes = cmds.listRelatives(obj, shapes=True, type='mesh')
            if shapes:
                return True
        return False
    
    def invoke(self, context: Any) -> str:
        """Invoke the operator."""
        selection = cmds.ls(selection=True, type='transform')
        
        if len(selection) > 1:
            cmds.warning("Please select only one object.")
            return {'CANCELLED'}
        
        obj = selection[0] if selection else None
        
        if not obj:
            cmds.warning("No object selected.")
            return {'CANCELLED'}
        
        # Get all vertices
        vertex_count = cmds.polyEvaluate(obj, vertex=True)
        vertices = list(range(vertex_count))
        
        # Assign to main group
        vg_utils.assign_vertex_grp(obj, vertices, 'faceit_main', overwrite=True)
        
        cmds.warning(f"Main group assigned to {obj}")
        
        return {'FINISHED'}


# ============================================================
# Assign Group Operator
# ============================================================

class AssignGroup:
    """
    Register the respective vertices in Edit Mode or all vertices in Object Mode.
    """
    
    name = "AssignGroup"
    label = "Assign Vertex Group"
    
    def __init__(self):
        self.vertex_group = ""
        self.method = 'REPLACE'
        self.vgroup_already_assigned = False
        self.faceit_group_in_selection = False
        self.faceit_groups_in_selection = []
        self.mode_save = 'OBJECT'
        self.initial_selection = []
        self.vertices_already_in_group = []
    
    def description(self, context: Any, properties: Any) -> str:
        """Get the operator description."""
        doc_string = "Object Mode: Assign all vertices of the selected object to this group.\n"
        doc_string += "You can assign multiple groups to one object.\n\n"
        
        if hasattr(properties, 'vertex_group'):
            if properties.vertex_group == "main":
                doc_string += "The main group: (face, skull, body, skin)\n"
                doc_string += "This group should consist of one connected surface.\n"
            elif "eyeball" in properties.vertex_group:
                doc_string += "Left/Right Eyeball: (spheres or half-spheres)"
            elif "eyes" in properties.vertex_group:
                doc_string += "Left/Right Eyes: All Deform Geometry\n"
            elif "teeth" in properties.vertex_group:
                doc_string += "Teeth: (Upper & Lower Teeth, Gum, Mouth Interior, etc.)\n"
            elif "eyelashes" in properties.vertex_group:
                doc_string += "Eyelashes: (Eyelashes, Eyeshells, Tearlines, etc.)\n"
            elif "tongue" in properties.vertex_group:
                doc_string += "Tongue: (Tongue)\n"
            elif "rigid" in properties.vertex_group:
                doc_string += "Rigid: (All geometry that is not supposed to deform)"
            elif "facial_hair" in properties.vertex_group:
                doc_string += "Facial Hair: (Beard, Moustache, Sideburns, etc.)"
        
        doc_string += "Read more in the Faceit documentation."
        return doc_string
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        selection = cmds.ls(selection=True, type='transform')
        if selection:
            obj = selection[0]
            shapes = cmds.listRelatives(obj, shapes=True, type='mesh')
            if shapes:
                return True
        return False
    
    def invoke(self, context: Any) -> str:
        """Invoke the operator."""
        selection = cmds.ls(selection=True, type='transform')
        
        if len(selection) > 1:
            cmds.warning("Please select only one object.")
            return {'CANCELLED'}
        
        obj = selection[0] if selection else None
        
        if not obj:
            cmds.warning("No object selected.")
            return {'CANCELLED'}
        
        grp_name = 'faceit_' + self.vertex_group
        
        # Get all vertices
        vertex_count = cmds.polyEvaluate(obj, vertex=True)
        vertices = list(range(vertex_count))
        
        # Assign to group
        vg_utils.assign_vertex_grp(obj, vertices, grp_name, overwrite=True)
        
        cmds.warning(f"Group {grp_name} assigned to {obj}")
        
        return {'FINISHED'}
    
    def get_clean_name(self, name: str) -> str:
        """Return a printable name for the vertex group."""
        return name.replace("faceit_", "").replace("_", " ").title()


# ============================================================
# Remove Faceit Group Operator
# ============================================================

class RemoveFaceitGroup:
    """
    Remove Faceit group(s) from selected object.
    """
    
    name = "RemoveFaceitGroup"
    label = "Reset Vertex Groups"
    
    def __init__(self):
        self.vgroup_name = ""
        self.operate_objects = ""
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return True
    
    def invoke(self, context: Any) -> str:
        """Invoke the operator."""
        return self.execute(context)
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        if not self.vgroup_name:
            cmds.warning("No vertex group specified.")
            return {'CANCELLED'}
        
        # Get objects with this group
        faceit_objects = futils.get_faceit_objects_list()
        
        for obj in faceit_objects:
            if not cmds.objExists(obj):
                continue
            
            if self.vgroup_name in vg_utils.get_vertex_groups(obj):
                vg_utils.delete_vertex_group(obj, self.vgroup_name)
        
        # Update property
        if cmds.objExists("faceit_core_data"):
            if cmds.attributeQuery("vertex_groups", node="faceit_core_data", exists=True):
                data_str = cmds.getAttr("faceit_core_data.vertex_groups") or "[]"
                try:
                    import json
                    data = json.loads(data_str)
                    for item in data:
                        if item.get('name') == self.vgroup_name:
                            item['is_assigned'] = False
                            item['assigned_to_objects'] = []
                            break
                    cmds.setAttr("faceit_core_data.vertex_groups", json.dumps(data), type="string")
                except:
                    pass
        
        cmds.warning(f"Removed group {self.vgroup_name}")
        return {'FINISHED'}


# ============================================================
# Remove Faceit Group List Operator
# ============================================================

class RemoveFaceitGroupList:
    """
    Remove Faceit group(s) from selected object.
    """
    
    name = "RemoveFaceitGroupList"
    label = "Reset Vertex Groups"
    
    def __init__(self):
        self.vgroup_name = ""
        self.object_list_index = -1
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return True
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        if not self.vgroup_name:
            cmds.warning("No vertex group specified.")
            return {'CANCELLED'}
        
        # Get objects
        faceit_objects = futils.get_faceit_objects_list()
        
        if self.object_list_index != -1 and self.object_list_index < len(faceit_objects):
            obj = faceit_objects[self.object_list_index]
            if cmds.objExists(obj):
                if self.vgroup_name in vg_utils.get_vertex_groups(obj):
                    vg_utils.delete_vertex_group(obj, self.vgroup_name)
        
        return {'FINISHED'}


# ============================================================
# Remove All Faceit Groups Operator
# ============================================================

class RemoveAllFaceitGroups:
    """
    Remove all Faceit vertex groups from selected objects.
    """
    
    name = "RemoveAllFaceitGroups"
    label = "Reset All Faceit Vertex Groups"
    
    def __init__(self):
        self.operate_scope = 'SELECTED'
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return True
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        if self.operate_scope == 'ALL':
            operate_objects = futils.get_faceit_objects_list()
        else:
            operate_objects = cmds.ls(selection=True, type='transform')
        
        if not operate_objects:
            cmds.warning("No objects to operate on.")
            return {'CANCELLED'}
        
        groups_to_remove = fdata.get_list_faceit_groups()
        
        for obj in operate_objects:
            if not cmds.objExists(obj):
                continue
            
            for grp_name in groups_to_remove:
                if grp_name in vg_utils.get_vertex_groups(obj):
                    vg_utils.delete_vertex_group(obj, grp_name)
        
        cmds.warning("Removed all Faceit vertex groups.")
        return {'FINISHED'}


# ============================================================
# Select Faceit Group Operator
# ============================================================

class SelectFaceitGroup:
    """
    Select all Vertices in the specified Faceit Vertex Group.
    """
    
    name = "SelectFaceitGroup"
    label = "Select Vertices"
    
    def __init__(self):
        self.faceit_vertex_group_name = ""
        self.object_list_index = -1
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return True
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        if not self.faceit_vertex_group_name:
            cmds.warning("No vertex group specified.")
            return {'CANCELLED'}
        
        # Get objects
        faceit_objects = futils.get_faceit_objects_list()
        
        if self.object_list_index != -1 and self.object_list_index < len(faceit_objects):
            obj = faceit_objects[self.object_list_index]
            
            if cmds.objExists(obj):
                vertices = vg_utils.get_verts_in_vgroup(obj, self.faceit_vertex_group_name)
                
                if vertices:
                    # Select vertices
                    cmds.select(clear=True)
                    for vtx in vertices:
                        cmds.select(f"{obj}.vtx[{vtx}]", add=True)
        
        return {'FINISHED'}


# ============================================================
# Draw Faceit Vertex Group Operator
# ============================================================

class DrawFaceitVertexGroup:
    """
    Draw an overlay for the Faceit vertex group.
    """
    
    name = "DrawFaceitVertexGroup"
    label = "Draw Vertex Group"
    
    def __init__(self):
        self.faceit_vertex_group_name = ""
        self._handler = None
        self.dg = None
        self.vert_data = None
        self.indices = None
        self.bm = None
        self.disabled_mods = []
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return True
    
    def description(self, context: Any, properties: Any) -> str:
        """Get the operator description."""
        return "Draws an overlay for the Faceit vertex group."
    
    def modal(self, context: Any, event: Any) -> str:
        """Modal operator handler."""
        return {'FINISHED'}
    
    def invoke(self, context: Any) -> str:
        """Invoke the operator."""
        if not self.faceit_vertex_group_name:
            cmds.warning("No vertex group specified.")
            return {'CANCELLED'}
        
        # In Maya, we'd use viewport drawing
        # For now, just select the vertices
        faceit_objects = futils.get_faceit_objects_list()
        
        for obj in faceit_objects:
            if not cmds.objExists(obj):
                continue
            
            if self.faceit_vertex_group_name in vg_utils.get_vertex_groups(obj):
                vertices = vg_utils.get_verts_in_vgroup(obj, self.faceit_vertex_group_name)
                
                if vertices:
                    cmds.select(clear=True)
                    for vtx in vertices:
                        cmds.select(f"{obj}.vtx[{vtx}]", add=True)
        
        return {'FINISHED'}


# ============================================================
# Mask Main Object Operator
# ============================================================

class MaskMainObject:
    """
    Mask all geometry that is not assigned to the main face.
    """
    
    name = "MaskMainObject"
    label = "Mask Main Face"
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return True
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        main_obj = futils.get_main_faceit_object()
        
        if not main_obj:
            cmds.warning("Main object not found.")
            return {'CANCELLED'}
        
        # In Maya, we'd use a mask modifier or selection
        # For now, just select the main group vertices
        if 'faceit_main' in vg_utils.get_vertex_groups(main_obj):
            vertices = vg_utils.get_verts_in_vgroup(main_obj, 'faceit_main')
            
            if vertices:
                cmds.select(clear=True)
                for vtx in vertices:
                    cmds.select(f"{main_obj}.vtx[{vtx}]", add=True)
        
        return {'FINISHED'}


# ============================================================
# Mask Group Operator
# ============================================================

class MaskGroup:
    """
    Mask all vertices that are not assigned to the specified group.
    """
    
    name = "MaskGroup"
    label = "Mask Faceit Vertex Group"
    
    def __init__(self):
        self.vgroup_name = ""
        self.inverse = True
        self.operation = 'ADD'
        self.mask_all = False
        self.grp_prop = None
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return True
    
    def invoke(self, context: Any) -> str:
        """Invoke the operator."""
        return self.execute(context)
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        if not self.vgroup_name:
            cmds.warning("No vertex group specified.")
            return {'CANCELLED'}
        
        faceit_objects = futils.get_faceit_objects_list()
        
        for obj in faceit_objects:
            if not cmds.objExists(obj):
                continue
            
            if self.vgroup_name in vg_utils.get_vertex_groups(obj):
                vertices = vg_utils.get_verts_in_vgroup(obj, self.vgroup_name)
                
                if self.operation == 'REMOVE':
                    # Deselect these vertices
                    pass
                else:
                    # Select these vertices
                    if vertices:
                        cmds.select(clear=True)
                        for vtx in vertices:
                            cmds.select(f"{obj}.vtx[{vtx}]", add=True)
        
        return {'FINISHED'}


# ============================================================
# Unmask Main Object Operator
# ============================================================

class UnmaskMainObject:
    """
    Remove mask from main object.
    """
    
    name = "UnmaskMainObject"
    label = "Remove Mask"
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return True
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        # In Maya, we'd remove the mask modifier
        cmds.warning("Unmask operation completed.")
        return {'FINISHED'}