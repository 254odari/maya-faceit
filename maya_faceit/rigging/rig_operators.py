# rig_operators.py
# Maya Faceit Plugin - Rig Operators
# Converted from Blender to Maya Python 3.11

"""
Rig operators for Faceit Maya plugin.
Handles rig generation and manipulation.
"""

import maya.cmds as cmds
import maya.api.OpenMaya as om2
import math
from typing import List, Dict, Optional, Any

from ..core import faceit_data as fdata
from ..core import faceit_utils as futils
from ..core import shape_key_utils as sk_utils
from ..core import vgroup_utils as vg_utils
from ..core import pose_utils
from ..ctrl_rig.control_rig_data import get_random_rig_id
from ..landmarks import landmarks_data as lm_data
from . import rig_data
from . import rig_utils

rig_create_warning = False


# ============================================================
# Generate Rig Operator
# ============================================================

class GenerateRig:
    """
    Generate the Rig that holds the shape key animation.
    """
    
    name = "GenerateRig"
    label = "Generate Rig"
    
    def __init__(self):
        self.use_existing_weights = False
        self.use_existing_expressions = False
        self.use_existing_corr_sk = False
        self.weights_restorable = False
        self.expressions_restorable = False
        self.corr_sk_restorable = False
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return True
    
    def invoke(self, context: Any) -> str:
        """Invoke the operator."""
        # Check if armature is missing
        self.weights_restorable = False
        self.expressions_restorable = False
        self.corr_sk_restorable = False
        
        # In Maya, we'd show a dialog
        return self.execute(context)
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        global rig_create_warning
        rig_create_warning = False
        
        # Get landmarks
        lm_obj = 'facial_landmarks'
        if not cmds.objExists(lm_obj):
            cmds.warning("You need to setup the Faceit Landmarks for your character.")
            return {'CANCELLED'}
        
        # Switch to object mode
        cmds.selectMode(object=True)
        
        # Generate eye locators if needed
        if not all(cmds.objExists(n) for n in ["eye_locator_L", "eye_locator_R"]):
            # Check if body rig has eye bones
            body_rig = None
            if cmds.objExists("faceit_core_data"):
                if cmds.attributeQuery("body_armature", node="faceit_core_data", exists=True):
                    body_rig = cmds.getAttr("faceit_core_data.body_armature") or ""
            
            if body_rig and cmds.objExists(body_rig):
                # Check for eye bones
                left_eye = None
                right_eye = None
                if cmds.attributeQuery("anime_ref_eyebone_l", node="faceit_core_data", exists=True):
                    left_eye = cmds.getAttr("faceit_core_data.anime_ref_eyebone_l") or ""
                if cmds.attributeQuery("anime_ref_eyebone_r", node="faceit_core_data", exists=True):
                    right_eye = cmds.getAttr("faceit_core_data.anime_ref_eyebone_r") or ""
                
                if left_eye and cmds.objExists(left_eye) and right_eye and cmds.objExists(right_eye):
                    # Generate locators
                    self._generate_locator_empties(context, eye_locators=True, teeth_locators=False, jaw_locator=False)
        
        # Unmask main
        self._unmask_main()
        
        # Hide locators
        for n in lm_data.LOCATOR_NAMES:
            if cmds.objExists(n):
                cmds.setAttr(f"{n}.visibility", 0)
        
        # Load rig file
        rig_filepath = fdata.get_rig_file()
        
        # In Maya, we'd import from a file
        # For now, create a simple rig
        rig = self._create_rig()
        
        if not rig:
            cmds.warning("Could not create rig.")
            return {'CANCELLED'}
        
        # Set rig ID
        cmds.addAttr(rig, ln="faceit_rig_id", dt="string")
        cmds.setAttr(f"{rig}.faceit_rig_id", str(get_random_rig_id()), type="string")
        
        # Match rig to landmarks
        self._match_rig_to_landmarks(rig, lm_obj)
        
        # Set up constraints
        self._setup_rig_constraints(rig)
        
        # Hide landmarks
        cmds.setAttr(f"{lm_obj}.visibility", 0)
        
        # Restore existing weights if requested
        if self.use_existing_weights:
            self._restore_existing_weights(rig)
        
        # Restore existing expressions if requested
        if self.use_existing_expressions:
            self._restore_existing_expressions(rig)
        
        if rig_create_warning:
            cmds.warning("Rig generated with warnings. Please see Console Output for details.")
        else:
            cmds.warning("Rig generated successfully!")
        
        return {'FINISHED'}
    
    def _create_rig(self) -> Optional[str]:
        """Create a simple rig."""
        # In Maya, we'd import from a file
        rig = cmds.joint(name="FaceitRig", position=[0, 0, 0])
        
        # Create basic bone structure
        # This would be expanded with the full Faceit rig
        return rig
    
    def _match_rig_to_landmarks(self, rig: str, lm_obj: str) -> None:
        """Match rig to landmarks."""
        if not cmds.objExists(rig) or not cmds.objExists(lm_obj):
            return
        
        # Get landmark positions
        vertex_count = cmds.polyEvaluate(lm_obj, vertex=True)
        
        # Get asymmetric setting
        asymmetric = False
        if cmds.objExists("faceit_core_data"):
            if cmds.attributeQuery("asymmetric", node="faceit_core_data", exists=True):
                asymmetric = cmds.getAttr("faceit_core_data.asymmetric")
        
        # Use appropriate bone dictionary
        if asymmetric:
            bone_dict = rig_data.bone_dict_asymmetric
        else:
            bone_dict = rig_data.bone_dict_symmetric
        
        # Get world matrix
        lm_mat = cmds.xform(lm_obj, query=True, worldSpace=True, matrix=True)
        
        # Match each bone
        for idx, bone_data in bone_dict.items():
            target_point = None
            
            if idx < 100:
                # Get vertex position
                pos = cmds.xform(f"{lm_obj}.vtx[{idx}]", query=True, worldSpace=True, translation=True)
                if pos:
                    target_point = pos
            
            elif idx == 101:
                # Left eye
                if cmds.objExists("eye_locator_L"):
                    target_point = cmds.xform("eye_locator_L", query=True, worldSpace=True, translation=True)
            
            elif idx == 111:
                # Right eye
                if cmds.objExists("eye_locator_R"):
                    target_point = cmds.xform("eye_locator_R", query=True, worldSpace=True, translation=True)
            
            if target_point:
                # Move bones
                for bone_name in bone_data.get('all', []):
                    if cmds.objExists(bone_name):
                        cmds.xform(bone_name, worldSpace=True, translation=target_point)
    
    def _setup_rig_constraints(self, rig: str) -> None:
        """Set up rig constraints."""
        if not cmds.objExists(rig):
            return
        
        # Set up lid follow constraints
        for side in ["L", "R"]:
            rig_utils.set_lid_follow_constraints(rig, side)
    
    def _restore_existing_weights(self, rig: str) -> None:
        """Restore existing weights."""
        # In Maya, we'd re-apply skin clusters
        pass
    
    def _restore_existing_expressions(self, rig: str) -> None:
        """Restore existing expressions."""
        # In Maya, we'd re-apply animation
        pass
    
    def _unmask_main(self) -> None:
        """Unmask main object."""
        # In Maya, we'd remove mask modifier
        pass
    
    def _generate_locator_empties(self, context: Any, eye_locators: bool = True,
                                   teeth_locators: bool = False, jaw_locator: bool = False) -> None:
        """Generate locator empties."""
        # In Maya, we'd create locators
        pass


# ============================================================
# Unhide Rig Operator
# ============================================================

class UnhideRig:
    """
    Unhide the Faceit Rig.
    """
    
    name = "UnhideRig"
    label = "Unhide Rig"
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        rig = futils.get_faceit_armature()
        if rig:
            return not cmds.getAttr(f"{rig}.visibility")
        return False
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        rig = futils.get_faceit_armature()
        
        if rig:
            cmds.setAttr(f"{rig}.visibility", 1)
            cmds.warning(f"Unhid rig: {rig}")
        
        return {'FINISHED'}


# ============================================================
# Reconnect Rig Operator
# ============================================================

class ReconnectRig:
    """
    Reconnect the Faceit Rig without removing the shape keys.
    """
    
    name = "ReconnectRig"
    label = "Reconnect Rig"
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return futils.get_faceit_objects_list() and futils.get_faceit_armature()
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        rig = futils.get_faceit_armature()
        faceit_objects = futils.get_faceit_objects_list()
        
        if not rig:
            cmds.warning("The Faceit Armature can't be found.")
            return {'CANCELLED'}
        
        # Show rig
        cmds.setAttr(f"{rig}.visibility", 1)
        
        # Reset pose
        pose_utils.reset_pose(rig)
        
        # Reconnect skin clusters
        for obj in faceit_objects:
            if not cmds.objExists(obj):
                continue
            
            # Check if skin cluster exists
            skin_cluster = None
            history = cmds.listHistory(obj, pruneDagObjects=True, interestLevel=2) or []
            for node in history:
                if cmds.nodeType(node) == 'skinCluster':
                    influences = cmds.skinCluster(node, query=True, influence=True) or []
                    if rig in influences:
                        skin_cluster = node
                        break
            
            if skin_cluster:
                # Enable skin cluster
                if cmds.attributeQuery("envelope", node=skin_cluster, exists=True):
                    cmds.setAttr(f"{skin_cluster}.envelope", 1)
            else:
                # Try to add armature modifier
                # In Maya, we'd add a skin cluster
                pass
        
        return {'FINISHED'}


# ============================================================
# Edit Locator Empties Operator
# ============================================================

class EditLocatorEmpties:
    """
    Edit Locator Empties visibility or remove.
    """
    
    name = "EditLocatorEmpties"
    label = "Show Locator Empties"
    
    def __init__(self):
        self.remove = False
        self.hide_value = False
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return True
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        for n in lm_data.LOCATOR_NAMES:
            if cmds.objExists(n):
                if self.remove:
                    cmds.delete(n)
                    continue
                cmds.setAttr(f"{n}.visibility", 0 if self.hide_value else 1)
        
        if self.remove:
            # Update scene property
            if cmds.objExists("faceit_core_data"):
                if cmds.attributeQuery("show_locator_empties", node="faceit_core_data", exists=True):
                    cmds.setAttr("faceit_core_data.show_locator_empties", 1)
        else:
            if cmds.objExists("faceit_core_data"):
                if cmds.attributeQuery("show_locator_empties", node="faceit_core_data", exists=True):
                    cmds.setAttr("faceit_core_data.show_locator_empties", 0 if self.hide_value else 1)
        
        return {'FINISHED'}


# ============================================================
# Generate Locator Empties Operator
# ============================================================

class GenerateLocatorEmpties:
    """
    Create empties at relevant locations.
    """
    
    name = "GenerateLocatorEmpties"
    label = "Create Locator Empties"
    
    def __init__(self):
        self.eye_locators = True
        self.teeth_locators = True
        self.jaw_locator = True
        self.guess_location = True
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return True
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        # Get asymmetric setting
        asymmetric = False
        if cmds.objExists("faceit_core_data"):
            if cmds.attributeQuery("asymmetric", node="faceit_core_data", exists=True):
                asymmetric = cmds.getAttr("faceit_core_data.asymmetric")
        
        if asymmetric:
            self.jaw_locator = False
        
        # Remove existing locators
        edit_locator = EditLocatorEmpties()
        edit_locator.remove = True
        edit_locator.execute(context)
        
        # Get Faceit collection
        faceit_collection = futils.get_faceit_collection()
        
        if not faceit_collection:
            cmds.warning("Faceit Collection not found.")
            return {'CANCELLED'}
        
        # Get landmark object
        lm_obj = 'facial_landmarks'
        lm_size = 0.1
        if cmds.objExists(lm_obj):
            bbox = cmds.xform(lm_obj, query=True, worldSpace=True, boundingBox=True)
            if bbox:
                lm_size = (bbox[3] - bbox[0]) / 8
        
        faceit_objects = futils.get_faceit_objects_list()
        
        # Create locators
        if self.eye_locators:
            self._create_eye_locators(faceit_objects, faceit_collection, lm_size)
        
        if self.teeth_locators:
            self._create_teeth_locators(faceit_objects, faceit_collection, lm_size)
        
        if self.jaw_locator and cmds.objExists(lm_obj):
            self._create_jaw_locator(lm_obj, faceit_collection, lm_size)
        
        return {'FINISHED'}
    
    def _create_eye_locators(self, faceit_objects: List[str], collection: str, size: float) -> None:
        """Create eye locators."""
        # Left eye
        pos = self._get_eye_position(faceit_objects, 'L')
        if pos:
            self._create_empty('eye_locator_L', pos, collection, size)
        
        # Right eye
        pos = self._get_eye_position(faceit_objects, 'R')
        if pos:
            self._create_empty('eye_locator_R', pos, collection, size)
    
    def _get_eye_position(self, faceit_objects: List[str], side: str) -> Optional[List[float]]:
        """Get eye position from vertex group."""
        vgroup_name = 'faceit_left_eyeball' if side == 'L' else 'faceit_right_eyeball'
        obj = vg_utils.get_objects_with_vertex_group(vgroup_name, objects=faceit_objects)
        
        if obj:
            vertices = vg_utils.get_verts_in_vgroup(obj, vgroup_name)
            if vertices:
                positions = []
                for vtx in vertices:
                    pos = cmds.xform(f"{obj}.vtx[{vtx}]", query=True, worldSpace=True, translation=True)
                    if pos:
                        positions.append(pos)
                
                if positions:
                    # Get median Z
                    z_vals = [p[2] for p in positions]
                    median_z = sum(z_vals) / len(z_vals)
                    
                    # Get center
                    x_vals = [p[0] for p in positions]
                    y_vals = [p[1] for p in positions]
                    center_x = sum(x_vals) / len(x_vals)
                    center_y = sum(y_vals) / len(y_vals)
                    
                    return [center_x, center_y, median_z]
        
        return None
    
    def _create_teeth_locators(self, faceit_objects: List[str], collection: str, size: float) -> None:
        """Create teeth locators."""
        # Upper teeth
        vgroup_name = 'faceit_upper_teeth'
        obj = vg_utils.get_objects_with_vertex_group(vgroup_name, objects=faceit_objects)
        if obj:
            vertices = vg_utils.get_verts_in_vgroup(obj, vgroup_name)
            if vertices:
                positions = []
                for vtx in vertices:
                    pos = cmds.xform(f"{obj}.vtx[{vtx}]", query=True, worldSpace=True, translation=True)
                    if pos:
                        positions.append(pos)
                
                if positions:
                    # Get bounds
                    y_vals = [p[1] for p in positions]
                    z_vals = [p[2] for p in positions]
                    min_y = min(y_vals)
                    median_z = sum(z_vals) / len(z_vals)
                    
                    pos = [0, min_y, median_z]
                    self._create_empty('teeth_upper_locator', pos, collection, size)
        
        # Lower teeth
        vgroup_name = 'faceit_lower_teeth'
        obj = vg_utils.get_objects_with_vertex_group(vgroup_name, objects=faceit_objects)
        if obj:
            vertices = vg_utils.get_verts_in_vgroup(obj, vgroup_name)
            if vertices:
                positions = []
                for vtx in vertices:
                    pos = cmds.xform(f"{obj}.vtx[{vtx}]", query=True, worldSpace=True, translation=True)
                    if pos:
                        positions.append(pos)
                
                if positions:
                    # Get bounds
                    y_vals = [p[1] for p in positions]
                    z_vals = [p[2] for p in positions]
                    min_y = min(y_vals)
                    median_z = sum(z_vals) / len(z_vals)
                    
                    pos = [0, min_y, median_z]
                    self._create_empty('teeth_lower_locator', pos, collection, size)
    
    def _create_jaw_locator(self, lm_obj: str, collection: str, size: float) -> None:
        """Create jaw locator."""
        # Get vertex position
        pos = cmds.xform(f"{lm_obj}.vtx[22]", query=True, worldSpace=True, translation=True)
        if pos:
            pos[0] = 0
            self._create_empty('jaw_locator', pos, collection, size)
    
    def _create_empty(self, name: str, position: List[float], collection: str, size: float) -> str:
        """Create an empty locator."""
        locator = cmds.spaceLocator(name=name)[0]
        cmds.parent(locator, collection)
        cmds.xform(locator, worldSpace=True, translation=position)
        cmds.setAttr(f"{locator}.localScaleX", size)
        cmds.setAttr(f"{locator}.localScaleY", size)
        cmds.setAttr(f"{locator}.localScaleZ", size)
        cmds.setAttr(f"{locator}.visibility", 1)
        
        return locator