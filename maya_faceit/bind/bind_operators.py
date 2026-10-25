# bind_operators.py
# Maya Faceit Plugin - Bind Operators
# Converted from Blender to Maya Python 3.11

"""
Bind operators for Faceit Maya plugin.
Handles smart binding of facial geometry to the Faceit rig.
"""

import maya.cmds as cmds # type: ignore
import maya.api.OpenMaya as om2 # type: ignore
import time
from typing import List, Dict, Optional, Tuple, Any

from ..core import faceit_utils as futils
from ..core import mesh_utils
from ..core import shape_key_utils
from ..core import vgroup_utils as vg_utils
from ..core.modifier_utils import add_faceit_armature_modifier, get_faceit_armature_modifier, set_bake_modifier_item
from . import bind_utils


# ============================================================
# SmartBind Operator
# ============================================================

class SmartBind:
    """Bind main objects (Face, Eyes, Teeth, Tongue)."""
    
    name = "SmartBind"
    label = "Bind"
    
    def __init__(self):
        # Advanced settings
        self.show_advanced_settings = False
        self.bind_scale_objects = True
        self.bind_scale_factor = 100
        self.smart_weights = True
        self.smooth_main_edges = True
        self.main_smooth_factor = 0.5
        self.main_smooth_steps = 10
        self.main_smooth_expand = 0.1
        self.weight_eyes = True
        self.weight_teeth = True
        self.weight_tongue = True
        self.transfer_weights = True
        self.tranfer_to_hair_only = False
        self.clean_eyelashes_weights = True
        self.remove_rigid_weights = True
        self.keep_split_objects = False
        self.smooth_bind = True
        self.smooth_factor = 0.5
        self.smooth_steps = 1
        self.smooth_expand = 0.0
        self.smooth_expand_eyelashes = True
        self.eyelashes_smooth_factor = 0.5
        self.eyelashes_smooth_steps = 2
        self.eyelashes_smooth_expand = 1.0
        self.remove_old_faceit_weights = True
        self.make_single_user = True
        
        # State tracking
        self.found_faceit_eyelashes_grp = False
        self.found_faceit_eyes_grp = False
        self.found_faceit_teeth_grp = False
        self.found_faceit_tongue_grp = False
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        rig = futils.get_faceit_armature(force_original=True)
        faceit_objects = futils.get_faceit_objects_list()
        if rig and faceit_objects:
            if cmds.getAttr(f"{rig}.visibility") and cmds.selectMode(query=True) == 'object':
                return True
        return False
    
    def invoke(self, context: Any = None) -> str:
        """Invoke the operator."""
        objects = futils.get_faceit_objects_list()
        self.found_faceit_eyelashes_grp = bool(vg_utils.get_objects_with_vertex_group(
            "faceit_eyelashes", objects=objects, get_all=False))
        
        if not self.found_faceit_eyelashes_grp:
            self.smooth_expand_eyelashes = False
            self.clean_eyelashes_weights = False
        
        # In Maya, we'd show a dialog
        return self.execute(context)
    
    def execute(self, context: Any = None) -> str:
        """Execute the operator."""
        start_time = time.time()
        
        # Get relevant objects
        faceit_objects = futils.get_faceit_objects_list()
        if not faceit_objects:
            cmds.warning("No objects registered! Complete Setup")
            return {'FINISHED'}
        
        lm_obj = 'facial_landmarks'
        if not cmds.objExists(lm_obj):
            cmds.warning("Faceit landmarks not found!")
            return {'FINISHED'}
        
        rig = futils.get_faceit_armature()
        if not rig:
            cmds.warning("Faceit rig not found!")
            return {'FINISHED'}
        
        # Check main group/object
        face_obj = futils.get_main_faceit_object()
        if not face_obj:
            cmds.warning("Please assign the Main group to the face before Binding.")
            return {'CANCELLED'}
        
        # Show landmarks and rig
        cmds.setAttr(f"{lm_obj}.visibility", 1)
        cmds.setAttr(f"{rig}.visibility", 1)
        
        # Set rig to rest pose
        cmds.setAttr(f"{rig}.posePosition", 0)  # 0 = rest, 1 = pose
        
        # Get bind objects
        bind_objects = self._get_bind_objects(faceit_objects)
        
        # Scale objects if needed
        if self.bind_scale_objects:
            scale_factor = self.bind_scale_factor
            bind_utils.scale_bind_objects(scale_factor, [rig] + bind_objects + [lm_obj])
        
        # Perform binding
        bind_success = self._bind(context, bind_objects, rig, lm_obj)
        
        # Restore scale
        if self.bind_scale_objects:
            scale_factor = self.bind_scale_factor
            bind_utils.scale_bind_objects(scale_factor, [rig] + bind_objects + [lm_obj], reverse=True)
            cmds.setAttr(f"{rig}.scaleX", 1)
            cmds.setAttr(f"{rig}.scaleY", 1)
            cmds.setAttr(f"{rig}.scaleZ", 1)
        
        # Hide landmarks
        cmds.setAttr(f"{lm_obj}.visibility", 0)
        
        # Cleanup
        cmds.select(rig)
        
        if bind_success:
            cmds.warning("Faceit Binding Successful")
            print(f"Bound in {round(time.time() - start_time, 2)} seconds")
        else:
            cmds.warning("Faceit Binding Failed. See Console for more info.")
        
        return {'FINISHED'}
    
    def _get_bind_objects(self, faceit_objects: List[str]) -> List[str]:
        """Get objects to bind."""
        # Filter to mesh objects
        bind_objects = []
        
        for obj in faceit_objects:
            if not cmds.objExists(obj):
                continue
            
            shapes = cmds.listRelatives(obj, shapes=True, type='mesh')
            if shapes:
                bind_objects.append(obj)
        
        return bind_objects
    
    def _bind(self, context: Any, bind_objects: List[str], rig: str, lm_obj: str) -> bool:
        """Perform the binding process."""
        faceit_vertex_groups = [
            "faceit_right_eyeball",
            "faceit_left_eyeball",
            "faceit_left_eyes_other",
            "faceit_right_eyes_other",
            "faceit_upper_teeth",
            "faceit_lower_teeth",
            "faceit_tongue",
            "faceit_rigid",
        ]
        
        bind_problem = False
        auto_weight_objects = []
        transfer_weights_objects = []
        eyelashes_objects = []
        secondary_bind_objects = []
        all_split_objects = []
        split_bind_objects_dict = {}
        
        # Split objects by Faceit groups
        for obj in bind_objects:
            split_objects = bind_utils.split_by_faceit_groups(obj)
            all_split_objects.extend(split_objects)
            split_bind_objects_dict[obj] = split_objects
        
        # Remove duplicates
        all_split_objects = list(set(all_split_objects))
        
        # Categorize split objects
        for s_obj in all_split_objects:
            if not cmds.objExists(s_obj):
                continue
            
            # Check for faceit_main group
            if self._has_vertex_group(s_obj, "faceit_main"):
                groups = vg_utils.get_vertex_groups(s_obj)
                if len(groups) == 1:
                    auto_weight_objects.append(s_obj)
                    continue
            
            # Check for secondary groups
            if self._has_any_vertex_group(s_obj, faceit_vertex_groups):
                secondary_bind_objects.append(s_obj)
            else:
                transfer_weights_objects.append(s_obj)
                if self._has_vertex_group(s_obj, "faceit_eyelashes"):
                    eyelashes_objects.append(s_obj)
        
        # Auto weight objects
        warning = self._auto_weight_objects(auto_weight_objects, rig)
        if warning:
            cmds.warning(f"Automatic Weights failed! {warning}")
        
        # Smart weights
        if self.smart_weights:
            self._apply_smart_weighting(
                auto_weight_objects,
                rig,
                lm_obj,
                faceit_vertex_groups,
                smooth_weights=self.smooth_main_edges
            )
        
        # Transfer weights to secondary objects
        if self.transfer_weights and transfer_weights_objects:
            self._transfer_weights(auto_weight_objects, transfer_weights_objects)
            
            # Handle eyelashes
            if eyelashes_objects and self.clean_eyelashes_weights:
                lid_bones = [
                    "DEF-lid.B.L", "DEF-lid.B.L.001", "DEF-lid.B.L.002", "DEF-lid.B.L.003",
                    "DEF-lid.T.L", "DEF-lid.T.L.001", "DEF-lid.T.L.002", "DEF-lid.T.L.003",
                    "DEF-lid.B.R", "DEF-lid.B.R.001", "DEF-lid.B.R.002", "DEF-lid.B.R.003",
                    "DEF-lid.T.R", "DEF-lid.T.R.001", "DEF-lid.T.R.002", "DEF-lid.T.R.003",
                ]
                
                for obj in eyelashes_objects:
                    self._clean_eyelashes_weights(obj, lid_bones)
                
                if self.smooth_expand_eyelashes:
                    self._smooth_selected_weights(
                        eyelashes_objects,
                        rig,
                        lid_bones,
                        factor=self.eyelashes_smooth_factor,
                        steps=self.eyelashes_smooth_steps,
                        expand=self.eyelashes_smooth_expand
                    )
        
        # Weight eyes
        if self.weight_eyes:
            eye_grps = ("faceit_left_eyeball", "faceit_right_eyeball",
                        "faceit_left_eyes_other", "faceit_right_eyes_other")
            for vgroup in eye_grps:
                new_grp = "DEF_eye.L" if "left" in vgroup else "DEF_eye.R"
                self._overwrite_faceit_group(all_split_objects, vgroup, new_grp)
        
        # Weight teeth
        if self.weight_teeth:
            teeth_grps = ("faceit_upper_teeth", "faceit_lower_teeth")
            for vgroup in teeth_grps:
                if "lower_teeth" in vgroup:
                    if cmds.objExists("DEF-teeth.B"):
                        new_grp = "DEF-teeth.B"
                    else:
                        cmds.warning("Lower Teeth bone 'DEF-teeth.B' does not exist.")
                        continue
                if "upper_teeth" in vgroup:
                    if cmds.objExists("DEF-teeth.T"):
                        new_grp = "DEF-teeth.T"
                    else:
                        cmds.warning("Upper Teeth bone 'DEF-teeth.T' does not exist.")
                        continue
                self._overwrite_faceit_group(all_split_objects, vgroup, new_grp)
        
        # Weight tongue
        if self.weight_tongue:
            objects_with_vgroup = vg_utils.get_objects_with_vertex_group(
                "faceit_tongue", objects=secondary_bind_objects, get_all=True)
            tongue_bones = ["DEF-tongue", "DEF-tongue.001", "DEF-tongue.002"]
            self._auto_weight_selection_to_bones(objects_with_vgroup, rig, tongue_bones, "faceit_tongue")
        
        # Merge split objects
        for obj, split_objects in split_bind_objects_dict.items():
            if not cmds.objExists(obj):
                continue
            
            if self.keep_split_objects:
                for s_obj in split_objects:
                    if cmds.objExists(s_obj):
                        dup = cmds.duplicate(s_obj)[0]
                        cmds.rename(dup, f"{s_obj}_debug")
            
            # Merge if multiple objects
            if len(split_objects) > 1:
                cmds.select(split_objects)
                cmds.polyUnite(ch=1, mergeUVSets=1, name=obj)
            
            # Add armature modifier
            add_faceit_armature_modifier(obj, rig)
        
        # Smooth all weights
        if self.smooth_bind:
            self._smooth_weights(bind_objects, rig)
        
        # Remove rigid weights
        if self.remove_rigid_weights:
            self._overwrite_faceit_group(bind_objects, "faceit_rigid", None)
        
        # Remove Faceit vertex groups
        for obj in bind_objects:
            if not cmds.objExists(obj):
                continue
            self._remove_faceit_vertex_groups(obj)
        
        return not bind_problem
    
    def _has_vertex_group(self, obj: str, group_name: str) -> bool:
        """Check if an object has a specific vertex group."""
        return group_name in vg_utils.get_vertex_groups(obj)
    
    def _has_any_vertex_group(self, obj: str, group_names: List[str]) -> bool:
        """Check if an object has any of the specified vertex groups."""
        groups = vg_utils.get_vertex_groups(obj)
        return any(g in groups for g in group_names)
    
    def _auto_weight_objects(self, auto_weight_objects: List[str], rig: str) -> Optional[str]:
        """Apply automatic weights to main geometry."""
        if not auto_weight_objects:
            return None
        
        warning = None
        
        # Disable bones for auto weighting
        no_auto_weight = [
            "DEF-tongue", "DEF-tongue.001", "DEF-tongue.002",
            "DEF-teeth.B", "DEF-teeth.T",
            "DEF_eye.R", "DEF_eye.L"
        ]
        
        # Disable deform on these bones
        for bone in no_auto_weight:
            if cmds.objExists(bone):
                cmds.setAttr(f"{bone}.deform", 0)
        
        # Bind each object
        for obj in auto_weight_objects:
            if not cmds.objExists(obj):
                continue
            
            # Select object and rig
            cmds.select(obj, rig)
            
            # Bind with skin cluster
            try:
                cmds.skinCluster(
                    rig,
                    obj,
                    toSelectedBones=True,
                    skinMethod=0,
                    normalizeWeights=1
                )
            except Exception as e:
                warning = f"Failed to bind {obj}: {str(e)}"
        
        # Re-enable deform on bones
        for bone in no_auto_weight:
            if cmds.objExists(bone):
                cmds.setAttr(f"{bone}.deform", 1)
        
        return warning
    
    def _apply_smart_weighting(self, objects: List[str], rig: str, lm_obj: str,
                               faceit_vertex_groups: List[str], smooth_weights: bool = True):
        """Remove weights outside of the facial region."""
        if not objects:
            return
        
        # Create facial hull
        face_hull = bind_utils.create_facial_hull(lm_obj)
        
        if not face_hull:
            return
        
        for obj in objects:
            if not cmds.objExists(obj):
                continue
            
            deform_groups = vg_utils.get_deform_bones_from_armature(rig)
            
            if any(self._has_vertex_group(obj, grp) for grp in deform_groups):
                bind_utils.remove_weights_from_non_facial_geometry(obj, face_hull, faceit_vertex_groups)
            else:
                print(f"Found no auto weights on object {obj}. Skipping smart weights")
        
        # Remove hull
        if cmds.objExists(face_hull):
            cmds.delete(face_hull)
    
    def _transfer_weights(self, from_objects: List[str], to_objects: List[str]):
        """Transfer weights from bound objects to secondary objects."""
        if not from_objects or not to_objects:
            return
        
        for from_obj in from_objects:
            if not cmds.objExists(from_obj):
                continue
            
            for obj in to_objects:
                if not cmds.objExists(obj):
                    continue
                
                # Get existing Faceit groups
                faceit_groups = [g for g in vg_utils.get_vertex_groups(obj) if g.startswith('faceit_')]
                
                # Transfer weights
                bind_utils.data_transfer_vertex_groups(from_obj, obj, method='NEAREST')
                
                # Remove transferred Faceit groups that weren't originally there
                current_groups = vg_utils.get_vertex_groups(obj)
                for grp in current_groups:
                    if grp.startswith('faceit_') and grp not in faceit_groups:
                        vg_utils.delete_vertex_group(obj, grp)
    
    def _clean_eyelashes_weights(self, obj: str, lid_bones: List[str]):
        """Remove non-lid deform groups from eyelashes."""
        if not cmds.objExists(obj):
            return
        
        groups = vg_utils.get_vertex_groups(obj)
        
        for grp in groups:
            if grp.startswith('DEF_') and grp not in lid_bones:
                vg_utils.delete_vertex_group(obj, grp)
    
    def _smooth_selected_weights(self, objects: List[str], rig: str, filter_bone_names: List[str],
                                  factor: float = 0.5, steps: int = 2, expand: float = 1.5):
        """Smooth weights for specific bones."""
        if not objects or not filter_bone_names:
            return
        
        # Select bones in pose mode
        cmds.selectMode(object=True)
        cmds.select(rig)
        cmds.selectMode(component=True)
        
        for bone in filter_bone_names:
            if cmds.objExists(bone):
                cmds.select(f"{bone}.joint", add=True)
        
        for obj in objects:
            if not cmds.objExists(obj):
                continue
            
            # Add armature modifier if needed
            add_faceit_armature_modifier(obj, rig)
            
            # Smooth weights
            # In Maya, we'd use the skinCluster smoothWeights command
            skin_cluster = self._get_skin_cluster(obj)
            if skin_cluster:
                cmds.skinCluster(skin_cluster, edit=True, smoothWeights=steps)
    
    def _get_skin_cluster(self, obj: str) -> Optional[str]:
        """Get the skin cluster on an object."""
        history = cmds.listHistory(obj, pruneDagObjects=True, interestLevel=2) or []
        for node in history:
            if cmds.nodeType(node) == 'skinCluster':
                return node
        return None
    
    def _smooth_weights(self, objects: List[str], rig: str):
        """Smooth weights on all objects."""
        if not objects:
            return
        
        for obj in objects:
            if not cmds.objExists(obj):
                continue
            
            skin_cluster = self._get_skin_cluster(obj)
            if skin_cluster:
                cmds.skinCluster(
                    skin_cluster,
                    edit=True,
                    smoothWeights=self.smooth_steps
                )
    
    def _overwrite_faceit_group(self, objects: List[str], faceit_vertex_group: str, new_grp: Optional[str]):
        """Bind user defined vertices to respective bones with constant weight."""
        objects_with_vgroup = vg_utils.get_objects_with_vertex_group(
            faceit_vertex_group, objects=objects, get_all=True)
        
        for obj in objects_with_vgroup:
            if not cmds.objExists(obj):
                continue
            
            vertices = vg_utils.get_verts_in_vgroup(obj, faceit_vertex_group)
            if not vertices:
                continue
            
            # Remove all weights from these vertices
            self._remove_weights_from_vertices(obj, vertices)
            
            if new_grp:
                # Assign to new group with weight 1
                self._assign_vertex_group(obj, vertices, new_grp)
    
    def _remove_weights_from_vertices(self, obj: str, vertices: List[int]):
        """Remove all weights from specific vertices."""
        if not cmds.objExists(obj):
            return
        
        skin_cluster = self._get_skin_cluster(obj)
        if not skin_cluster:
            return
        
        influences = cmds.skinCluster(skin_cluster, query=True, influence=True) or []
        
        for vtx in vertices:
            for influence in influences:
                cmds.skinCluster(
                    skin_cluster,
                    edit=True,
                    weight=f"{influence}.vtx[{vtx}]",
                    value=0
                )
    
    def _assign_vertex_group(self, obj: str, vertices: List[int], group_name: str):
        """Assign vertices to a vertex group with weight 1."""
        vg_utils.assign_vertex_grp(obj, vertices, group_name, overwrite=True)
    
    def _auto_weight_selection_to_bones(self, objects: List[str], rig: str, bones: List[str], faceit_group: str):
        """Bind a vertex selection to specific bones."""
        if not objects:
            return
        
        for obj in objects:
            if not cmds.objExists(obj):
                continue
            
            vertices = vg_utils.get_verts_in_vgroup(obj, faceit_group)
            if not vertices:
                continue
            
            # Add armature modifier
            add_faceit_armature_modifier(obj, rig)
            
            # Remove weights from other bones
            self._remove_weights_from_vertices(obj, vertices)
            
            # Assign to selected bones with auto weight
            skin_cluster = self._get_skin_cluster(obj)
            if skin_cluster:
                # Add influences if needed
                for bone in bones:
                    if cmds.objExists(bone):
                        cmds.skinCluster(skin_cluster, edit=True, addInfluence=bone)
                
                # Set weights
                for vtx in vertices:
                    for bone in bones:
                        if cmds.objExists(bone):
                            cmds.skinCluster(
                                skin_cluster,
                                edit=True,
                                weight=f"{bone}.vtx[{vtx}]",
                                value=1.0 / len(bones)
                            )
    
    def _remove_faceit_vertex_groups(self, obj: str):
        """Remove Faceit vertex groups from an object."""
        groups = vg_utils.get_vertex_groups(obj)
        
        for grp in groups:
            if grp.startswith('faceit_'):
                vg_utils.delete_vertex_group(obj, grp)


# ============================================================
# PairArmature Operator
# ============================================================

class PairArmature:
    """Pair the FaceitRig to the facial objects without generating weights."""
    
    name = "PairArmature"
    label = "Pair Armature"
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return True
    
    def execute(self, context: Any = None) -> str:
        """Execute the operator."""
        faceit_objects = futils.get_faceit_objects_list()
        faceit_rig = futils.get_faceit_armature(force_original=True)
        
        if not faceit_rig:
            return {'CANCELLED'}
        
        for obj in faceit_objects:
            if cmds.objExists(obj):
                add_faceit_armature_modifier(obj, faceit_rig)
        
        return {'FINISHED'}


# ============================================================
# UnbindFacial Operator
# ============================================================

class UnbindFacial:
    """Unbind the FaceitRig from the facial objects."""
    
    name = "UnbindFacial"
    label = "Unbind"
    
    def __init__(self):
        self.remove_deform_groups = True
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return True
    
    def execute(self, context: Any = None) -> str:
        """Execute the operator."""
        rig = futils.get_faceit_armature()
        faceit_objects = futils.get_faceit_objects_list()
        
        for obj in faceit_objects:
            if not cmds.objExists(obj):
                continue
            
            # Remove skin cluster
            skin_cluster = None
            history = cmds.listHistory(obj, pruneDagObjects=True, interestLevel=2) or []
            for node in history:
                if cmds.nodeType(node) == 'skinCluster':
                    influences = cmds.skinCluster(node, query=True, influence=True) or []
                    if rig in influences:
                        skin_cluster = node
                        break
            
            if skin_cluster:
                cmds.delete(skin_cluster)
            
            # Remove deform groups
            if self.remove_deform_groups and rig:
                deform_groups = vg_utils.get_deform_bones_from_armature(rig)
                groups = vg_utils.get_vertex_groups(obj)
                
                for grp in groups:
                    if grp in deform_groups:
                        vg_utils.delete_vertex_group(obj, grp)
        
        return {'FINISHED'}


# ============================================================
# CorrectiveSmooth Operator
# ============================================================

class CorrectiveSmooth:
    """Add corrective smooth modifier to the active object."""
    
    name = "CorrectiveSmooth"
    label = "Smooth Correct Modifier"
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        selection = cmds.ls(selection=True, type='transform')
        if selection:
            obj = selection[0]
            shapes = cmds.listRelatives(obj, shapes=True, type='mesh')
            if shapes:
                # Check if modifier already exists
                history = cmds.listHistory(obj, pruneDagObjects=True, interestLevel=2) or []
                for node in history:
                    if cmds.nodeType(node) == 'correctiveSmooth':
                        return False
                return True
        return False
    
    def execute(self, context: Any = None) -> str:
        """Execute the operator."""
        selection = cmds.ls(selection=True, type='transform')
        if not selection:
            return {'CANCELLED'}
        
        obj = selection[0]
        
        # Create corrective smooth node
        mod = cmds.createNode("correctiveSmooth", name=f"{obj}_Faceit_CorrectiveSmooth")
        
        # Connect to mesh
        shape = cmds.listRelatives(obj, shapes=True, type='mesh')[0]
        cmds.connectAttr(f"{mod}.output", f"{shape}.inMesh")
        
        # Set attributes
        cmds.setAttr(f"{mod}.iterations", 4)
        cmds.setAttr(f"{mod}.usePinBoundary", 1)
        cmds.setAttr(f"{mod}.smoothType", 1)  # Length weighted
        
        return {'FINISHED'}