# landmarks_operators.py
# Maya Faceit Plugin - Landmarks Operators
# Converted from Blender to Maya Python 3.11

"""
Landmarks operators for Faceit Maya plugin.
Handles landmark creation, editing, and management.
"""

import maya.cmds as cmds # type: ignore
import maya.api.OpenMaya as om2 # type: ignore
import math
from typing import List, Dict, Optional, Tuple, Any

from ..core import faceit_data as fdata
from ..core import faceit_utils as futils
from ..core import mesh_utils
from ..core import shape_key_utils as sk_utils
from ..core import vgroup_utils as vg_utils
from ..core import pose_utils as rig_utils
from . import landmarks_data as lm_data
from . import landmarks_utils


# ============================================================
# Facial Landmarks Operator
# ============================================================

class FacialLandmarks:
    """
    Place the facial landmarks.
    1. Match Chin Position
    2. Match Eye Height
    3. Match Jaw Width
    """
    
    name = "FacialLandmarks"
    label = "facial_landmarks"
    
    def __init__(self):
        self.mouse_x = 0
        self.mouse_y = 0
        self.initial_mouse_scale = 0
        self.init_scale = False
        self.init_rotation = False
        self.init_loc = True
        self.initial_dimensions = (0, 0, 0)
        self.is_asymmetric_landmarks = False
        self.area_width = 0
        self.area_height = 0
        self.area_x = 0
        self.area_y = 0
        self.mouse_offset_x = 0
        self.mouse_offset_y = 0
        self.rotation_offset = 0
        self.pivot_point_2D = (0, 0)
        self.landmarks_scale = (1, 1, 1)
        self.face_dimensions = (1, 1, 1)
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        faceit_objects = futils.get_faceit_objects_list()
        return len(faceit_objects) > 0
    
    def invoke(self, context: Any, event: Any) -> str:
        """Invoke the operator."""
        self.mouse_x = event.mouse_x if hasattr(event, 'mouse_x') else 0
        self.mouse_y = event.mouse_y if hasattr(event, 'mouse_y') else 0
        self.is_asymmetric_landmarks = False  # In Maya, we'd get this from settings
        
        # Get area info
        self.area_width = 800  # Default
        self.area_height = 600
        self.area_x = 0
        self.area_y = 0
        
        self.execute(context)
        
        # In Maya, we'd start a modal operation
        return {'RUNNING_MODAL'}
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        # Unlock view
        landmarks_utils.unlock_3d_view()
        
        # Switch to object mode
        cmds.selectMode(object=True)
        
        # Get main Faceit object
        main_obj = futils.get_main_faceit_object()
        
        if main_obj is None:
            cmds.warning("Please assign the Main Vertex Group to the Face Mesh! (Setup Tab)")
            return {'CANCELLED'}
        
        # Show main object
        cmds.setAttr(f"{main_obj}.visibility", 1)
        
        # Create landmarks mesh
        lm_obj = self._create_landmarks_mesh()
        
        if lm_obj is None:
            cmds.warning("Could not create landmarks mesh")
            return {'CANCELLED'}
        
        # Position landmarks
        self._position_landmarks(lm_obj, main_obj)
        
        # Set initial state
        if cmds.attributeQuery("state", node=lm_obj, exists=True):
            cmds.setAttr(f"{lm_obj}.state", 0)
        
        cmds.warning("Align the Landmarks with your characters chin!")
        
        return {'FINISHED'}
    
    def _create_landmarks_mesh(self) -> Optional[str]:
        """Create the landmarks mesh."""
        # In Maya, we'd create a polygon mesh with predefined vertices
        # For now, create a simple plane
        lm_obj = cmds.polyCreateFacet(
            name="facial_landmarks",
            point=[[-1, 0, 0], [1, 0, 0], [1, 0, 2], [-1, 0, 2]]
        )[0]
        
        return lm_obj
    
    def _position_landmarks(self, lm_obj: str, main_obj: str) -> None:
        """Position the landmarks relative to the main object."""
        if not cmds.objExists(main_obj):
            return
        
        # Get main object bounding box
        bbox = cmds.xform(main_obj, query=True, worldSpace=True, boundingBox=True)
        
        if bbox:
            # Position at bottom of main object
            lm_pos = [0, bbox[1], 0]  # Bottom Y
            cmds.xform(lm_obj, worldSpace=True, translation=lm_pos)
    
    def modal(self, context: Any, event: Any) -> str:
        """Modal operator handler."""
        # In Maya, we'd handle modal operations differently
        return {'FINISHED'}


# ============================================================
# Reset Facial Landmarks Operator
# ============================================================

class ResetFacial:
    """Discard Landmarks and start over."""
    
    name = "ResetFacial"
    label = "Reset Landmarks"
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return cmds.objExists('facial_landmarks')
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        # Delete landmarks
        if cmds.objExists('facial_landmarks'):
            cmds.delete('facial_landmarks')
        
        # Remove locators
        self._remove_locators()
        
        # Unlock view
        landmarks_utils.unlock_3d_view()
        
        return {'FINISHED'}
    
    def _remove_locators(self) -> None:
        """Remove locator empties."""
        locator_names = lm_data.LOCATOR_NAMES
        
        for locator in locator_names:
            if cmds.objExists(locator):
                cmds.delete(locator)


# ============================================================
# Project Landmarks Operator
# ============================================================

class ProjectLandmarks:
    """Project the Landmarks onto the Main Object."""
    
    name = "ProjectLandmarks"
    label = "Project Landmarks"
    
    def __init__(self):
        self.mouse_x = 0
        self.mouse_y = 0
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return cmds.objExists('facial_landmarks')
    
    def invoke(self, context: Any, event: Any) -> str:
        """Invoke the operator."""
        self.mouse_x = event.mouse_x if hasattr(event, 'mouse_x') else 0
        self.mouse_y = event.mouse_y if hasattr(event, 'mouse_y') else 0
        return self.execute(context)
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        # Unlock view
        landmarks_utils.unlock_3d_view()
        
        lm_obj = 'facial_landmarks'
        
        if not cmds.objExists(lm_obj):
            cmds.warning("No landmarks mesh found")
            return {'CANCELLED'}
        
        # Get main object
        surface_obj = futils.get_main_faceit_object()
        
        if not surface_obj:
            cmds.warning("Please assign the main group to the face mesh (Setup tab)")
            return {'CANCELLED'}
        
        # Position landmarks in front of face
        bbox = cmds.xform(surface_obj, query=True, worldSpace=True, boundingBox=True)
        if bbox:
            lm_pos = [0, bbox[1], 0]
            cmds.xform(lm_obj, worldSpace=True, translation=lm_pos)
        
        # Project landmarks onto surface
        self._project_vertices(lm_obj, surface_obj)
        
        # Set state
        if cmds.attributeQuery("state", node=lm_obj, exists=True):
            cmds.setAttr(f"{lm_obj}.state", 4)
        
        cmds.warning("Fine-tune the landmarks in Edit mode until they match the face.")
        
        return {'FINISHED'}
    
    def _project_vertices(self, lm_obj: str, surface_obj: str) -> None:
        """Project landmarks vertices onto the surface."""
        if not cmds.objExists(lm_obj) or not cmds.objExists(surface_obj):
            return
        
        # Get vertices
        vertex_count = cmds.polyEvaluate(lm_obj, vertex=True)
        
        # For each vertex, project onto surface
        for i in range(vertex_count):
            vtx_pos = cmds.xform(f"{lm_obj}.vtx[{i}]", query=True, worldSpace=True, translation=True)
            
            if vtx_pos:
                # Find closest point on surface
                closest = mesh_utils.closest_point_on_mesh(tuple(vtx_pos), surface_obj)
                
                if closest:
                    cmds.xform(f"{lm_obj}.vtx[{i}]", worldSpace=True, translation=list(closest))


# ============================================================
# Revert Projection Operator
# ============================================================

class RevertProjection:
    """Revert landmark projection and edit in front view."""
    
    name = "RevertProjection"
    label = "Revert Projection (Edit Front)"
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return True
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        lm_obj = 'facial_landmarks'
        
        if not cmds.objExists(lm_obj):
            cmds.warning("No landmarks mesh found")
            return {'CANCELLED'}
        
        # Show landmarks
        cmds.setAttr(f"{lm_obj}.visibility", 1)
        
        # Switch to object mode
        cmds.selectMode(object=True)
        cmds.select(lm_obj)
        
        # Reset Y positions to 0
        vertex_count = cmds.polyEvaluate(lm_obj, vertex=True)
        for i in range(vertex_count):
            pos = cmds.xform(f"{lm_obj}.vtx[{i}]", query=True, objectSpace=True, translation=True)
            if pos:
                cmds.xform(f"{lm_obj}.vtx[{i}]", objectSpace=True, translation=[pos[0], 0, pos[2]])
        
        # Position at bottom of main object
        main_obj = futils.get_main_faceit_object()
        if main_obj:
            bbox = cmds.xform(main_obj, query=True, worldSpace=True, boundingBox=True)
            if bbox:
                lm_pos = [0, bbox[1], 0]
                cmds.xform(lm_obj, worldSpace=True, translation=lm_pos)
        
        # Update state
        if cmds.attributeQuery("state", node=lm_obj, exists=True):
            current_state = cmds.getAttr(f"{lm_obj}.state") or 0
            cmds.setAttr(f"{lm_obj}.state", current_state - 1)
        
        # Set front view
        landmarks_utils.set_front_view()
        
        return {'FINISHED'}


# ============================================================
# Lock 3D View Front Operator
# ============================================================

class Lock3DViewFront:
    """Lock the 3D view rotation and enable Front view."""
    
    name = "Lock3DViewFront"
    label = "Set Front View"
    
    def __init__(self):
        self.mouse_x = 0
        self.mouse_y = 0
        self.lock_value = False
        self.set_edit_mode = True
        self.find_area_by_mouse_position = False
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return True
    
    def invoke(self, context: Any, event: Any) -> str:
        """Invoke the operator."""
        self.mouse_x = event.mouse_x if hasattr(event, 'mouse_x') else 0
        self.mouse_y = event.mouse_y if hasattr(event, 'mouse_y') else 0
        return self.execute(context)
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        lm_obj = 'facial_landmarks'
        
        if self.set_edit_mode and cmds.objExists(lm_obj):
            cmds.select(lm_obj)
            cmds.selectMode(object=True)
        
        # Set front view
        landmarks_utils.set_front_view()
        
        if self.set_edit_mode and cmds.objExists(lm_obj):
            cmds.selectMode(component=True)
        
        return {'FINISHED'}


# ============================================================
# Unlock 3D View Operator
# ============================================================

class Unlock3DView:
    """Unlock the 3D view rotation."""
    
    name = "Unlock3DView"
    label = "Unlock 3D View"
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return True
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        landmarks_utils.unlock_3d_view()
        return {'FINISHED'}


# ============================================================
# Reset Snap Settings Operator
# ============================================================

class ResetSnapSettings:
    """Set the correct Snap to Face Settings automatically."""
    
    name = "ResetSnapSettings"
    label = "Reset Snap Settings"
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        # In Maya, set snap settings
        cmds.selectMode(object=True)
        cmds.snapMode('face')
        
        return {'FINISHED'}


# ============================================================
# Mirror Selected Verts Operator
# ============================================================

class MirrorSelectedVerts:
    """Mirror selected Landmarks Vertices."""
    
    name = "MirrorSelectedVerts"
    label = "Mirror Selected Vertices"
    
    def __init__(self):
        self.mirror_dir = 'L_R'
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        selection = cmds.ls(selection=True, flatten=True)
        if selection:
            # Check if selected items are vertices of facial_landmarks
            for item in selection:
                if 'facial_landmarks.vtx' in item:
                    return True
        return False
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        lm_obj = 'facial_landmarks'
        
        if not cmds.objExists(lm_obj):
            cmds.warning("No landmarks mesh found")
            return {'CANCELLED'}
        
        # Get selected vertices
        selected = cmds.ls(selection=True, flatten=True)
        selected_indices = []
        
        for item in selected:
            if 'facial_landmarks.vtx' in item:
                idx = int(item.split('[')[1].split(']')[0])
                selected_indices.append(idx)
        
        if not selected_indices:
            cmds.warning("Select either Left or Right Side Vertices")
            return {'FINISHED'}
        
        # Mirror vertices
        mirror_dict = lm_data.LANDMARKS_MIRROR_VERTICES_DICT
        
        # Determine direction
        left_indices = list(mirror_dict.keys())
        right_indices = list(mirror_dict.values())
        
        if all(idx in left_indices for idx in selected_indices):
            self.mirror_dir = 'L_R'
        elif all(idx in right_indices for idx in selected_indices):
            self.mirror_dir = 'R_L'
        else:
            cmds.warning("Select either Left or Right Side Vertices")
            return {'FINISHED'}
        
        # Mirror vertices
        for left_idx, right_idx in mirror_dict.items():
            if self.mirror_dir == 'L_R':
                if left_idx not in selected_indices:
                    continue
                
                # Get left vertex position
                pos = cmds.xform(f"{lm_obj}.vtx[{left_idx}]", query=True, worldSpace=True, translation=True)
                
                if pos:
                    # Mirror X
                    mirrored_pos = [-pos[0], pos[1], pos[2]]
                    cmds.xform(f"{lm_obj}.vtx[{right_idx}]", worldSpace=True, translation=mirrored_pos)
            else:
                if right_idx not in selected_indices:
                    continue
                
                # Get right vertex position
                pos = cmds.xform(f"{lm_obj}.vtx[{right_idx}]", query=True, worldSpace=True, translation=True)
                
                if pos:
                    # Mirror X
                    mirrored_pos = [-pos[0], pos[1], pos[2]]
                    cmds.xform(f"{lm_obj}.vtx[{left_idx}]", worldSpace=True, translation=mirrored_pos)
        
        return {'FINISHED'}


# ============================================================
# Reset To Landmarks Operator
# ============================================================

class ResetToLandmarks:
    """Go back to editing the landmarks."""
    
    name = "ResetToLandmarks"
    label = "Back to Landmarks"
    
    def __init__(self):
        self.keep_weights = False
        self.keep_expressions = False
        self.keep_corrective_shape_keys = True
        self.expressions_generated = False
        self.rig_bound = False
        self.corr_sk = False
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        rig = futils.get_faceit_armature()
        if rig:
            return cmds.getAttr(f"{rig}.visibility")
        return False
    
    def invoke(self, context: Any, event: Any) -> str:
        """Invoke the operator."""
        # Check if expressions exist
        if cmds.objExists("faceit_core_data"):
            if cmds.attributeQuery("expression_names", node="faceit_core_data", exists=True):
                names_str = cmds.getAttr("faceit_core_data.expression_names") or ""
                if names_str:
                    self.expressions_generated = True
        
        # Check if rig is bound
        rig = futils.get_faceit_armature()
        if rig:
            deform_groups = vg_utils.get_deform_bones_from_armature(rig)
            all_vgroups = vg_utils.get_vertex_groups_from_objects()
            if any(grp in deform_groups for grp in all_vgroups):
                self.rig_bound = True
        
        # Check for corrective shape keys
        self.corr_sk = any(
            sk_name.startswith('faceit_cc_') 
            for sk_name in sk_utils.get_shape_key_names_from_objects()
        )
        
        # Show dialog if needed
        if self.expressions_generated or self.rig_bound:
            # In Maya, we'd show a dialog
            return self.execute(context)
        else:
            return self.execute(context)
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        scene = context.scene if hasattr(context, 'scene') else None
        
        # Handle shape actions
        sh_action = None
        ow_action = None
        
        if cmds.objExists("faceit_shape_action"):
            sh_action = "faceit_shape_action"
        if cmds.objExists("overwrite_shape_action"):
            ow_action = "overwrite_shape_action"
        
        if self.keep_expressions:
            # Keep actions
            pass
        else:
            # Remove actions
            if sh_action:
                cmds.delete(sh_action)
            if ow_action:
                cmds.delete(ow_action)
            
            # Clear expression data
            if cmds.objExists("faceit_core_data"):
                if cmds.attributeQuery("expression_names", node="faceit_core_data", exists=True):
                    cmds.setAttr("faceit_core_data.expression_names", "", type="string")
                if cmds.attributeQuery("expression_frames", node="faceit_core_data", exists=True):
                    cmds.setAttr("faceit_core_data.expression_frames", "", type="string")
                if cmds.attributeQuery("expression_sides", node="faceit_core_data", exists=True):
                    cmds.setAttr("faceit_core_data.expression_sides", "", type="string")
        
        # Handle corrective shape keys
        if self.corr_sk:
            faceit_objects = futils.get_faceit_objects_list()
            
            for obj in faceit_objects:
                if sk_utils.has_shape_keys(obj):
                    blend_node = sk_utils.get_blend_shape_node(obj)
                    if blend_node:
                        targets = sk_utils.get_blend_shape_targets(obj)
                        for target in targets:
                            if target.startswith('faceit_cc_'):
                                if self.keep_corrective_shape_keys:
                                    # Mute corrective shapes
                                    # In Maya, we'd set the weight to 0
                                    pass
                                else:
                                    # Remove corrective shape
                                    cmds.removeMultiInstance(f"{blend_node}.weight[{target}]")
        
        # Unbind facial
        self._unbind_facial(remove_deform_groups=not self.keep_weights)
        
        # Remove rig
        rig = futils.get_faceit_armature()
        if rig:
            cmds.delete(rig)
        
        # Show landmarks
        lm_obj = 'facial_landmarks'
        if cmds.objExists(lm_obj):
            cmds.setAttr(f"{lm_obj}.visibility", 1)
        else:
            cmds.warning("Landmarks mesh does not exist anymore.")
            return {'CANCELLED'}
        
        # Edit landmarks
        self._edit_landmarks()
        
        # Purge orphans
        cmds.cleanupScene()
        
        return {'FINISHED'}
    
    def _unbind_facial(self, remove_deform_groups: bool = False) -> None:
        """Unbind facial rig."""
        faceit_objects = futils.get_faceit_objects_list()
        
        for obj in faceit_objects:
            # Remove skin cluster
            skin_cluster = None
            history = cmds.listHistory(obj, pruneDagObjects=True, interestLevel=2) or []
            for node in history:
                if cmds.nodeType(node) == 'skinCluster':
                    skin_cluster = node
                    break
            
            if skin_cluster:
                cmds.delete(skin_cluster)
    
    def _edit_landmarks(self) -> None:
        """Enter landmarks edit mode."""
        lm_obj = 'facial_landmarks'
        
        if cmds.objExists(lm_obj):
            cmds.select(lm_obj)
            cmds.selectMode(object=True)
            cmds.setAttr(f"{lm_obj}.visibility", 1)


# ============================================================
# Edit Landmarks Operator
# ============================================================

class EditLandmarks:
    """Edit the landmarks."""
    
    name = "EditLandmarks"
    label = "Edit Landmarks"
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return cmds.objExists('facial_landmarks')
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        lm_obj = 'facial_landmarks'
        
        if not cmds.objExists(lm_obj):
            cmds.warning("No landmarks mesh found")
            return {'CANCELLED'}
        
        # Show landmarks
        cmds.setAttr(f"{lm_obj}.visibility", 1)
        
        # Select landmarks
        cmds.select(lm_obj)
        cmds.selectMode(object=True)
        
        # Switch to vertex mode
        cmds.selectMode(component=True)
        cmds.selectType(vertex=True)
        
        return {'FINISHED'}


# ============================================================
# Finish Edit Landmarks Operator
# ============================================================

class FinishEditLandmarks:
    """Finish editing landmarks."""
    
    name = "FinishEditLandmarks"
    label = "Finish Edit Landmarks"
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        selection = cmds.ls(selection=True)
        return 'facial_landmarks' in selection
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        lm_obj = 'facial_landmarks'
        
        # Switch to object mode
        cmds.selectMode(object=True)
        cmds.select(lm_obj)
        
        return {'FINISHED'}