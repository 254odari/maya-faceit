# rig_join_to_body.py
# Maya Faceit Plugin - Rig Join to Body
# Converted from Blender to Maya Python 3.11

"""
Rig join to body operators for Faceit Maya plugin.
Handles joining the Faceit rig to a body armature.
"""

import maya.cmds as cmds
import maya.api.OpenMaya as om2
from typing import List, Dict, Optional, Any

from ..core import faceit_utils as futils
from ..core import vgroup_utils as vg_utils
from ..core import shape_key_utils as sk_utils
from ..core import modifier_utils
from ..ctrl_rig.control_rig_data import get_random_rig_id
from . import rig_utils


# ============================================================
# Join With Body Armature Operator
# ============================================================

class JoinWithBodyArmature:
    """
    Remove the def face group to use the faceit armature in regular keyframe animation.
    """
    
    name = "JoinWithBodyArmature"
    label = "Join to Body"
    
    def __init__(self):
        self.combine_animation = False
        self.is_arp_body = False
        self.tag_arp_custom = False
        self.merge_faceit_weights = True
        self.keep_faceit_bone_groups = True
        self.use_armature_modifier_for_baking = True
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        if cmds.selectMode(query=True) == 'object':
            if cmds.objExists("faceit_core_data"):
                if cmds.attributeQuery("armature", node="faceit_core_data", exists=True):
                    if cmds.attributeQuery("body_armature", node="faceit_core_data", exists=True):
                        faceit_rig = cmds.getAttr("faceit_core_data.armature") or ""
                        body_rig = cmds.getAttr("faceit_core_data.body_armature") or ""
                        if faceit_rig and cmds.objExists(faceit_rig):
                            if body_rig and cmds.objExists(body_rig):
                                if cmds.attributeQuery("body_armature_head_bone", node="faceit_core_data", exists=True):
                                    head_bone = cmds.getAttr("faceit_core_data.body_armature_head_bone") or ""
                                    if head_bone and cmds.objExists(head_bone):
                                        return True
        return False
    
    def invoke(self, context: Any) -> str:
        """Invoke the operator."""
        # Check scales
        if cmds.objExists("faceit_core_data"):
            body_rig = cmds.getAttr("faceit_core_data.body_armature") or ""
            faceit_rig = cmds.getAttr("faceit_core_data.armature") or ""
            
            if body_rig and faceit_rig:
                # Check if body rig has scale
                body_scale = cmds.getAttr(f"{body_rig}.scale")[0]
                faceit_scale = cmds.getAttr(f"{faceit_rig}.scale")[0]
                
                if body_scale != [1, 1, 1] or faceit_scale != [1, 1, 1]:
                    cmds.warning("Body and Faceit rigs have different scales. Please apply scale first.")
                    return {'CANCELLED'}
        
        # Check for ARP
        if cmds.objExists("faceit_core_data"):
            body_rig = cmds.getAttr("faceit_core_data.body_armature") or ""
            if body_rig and cmds.objExists(body_rig):
                # Check for ARP attributes
                attrs = cmds.listAttr(body_rig, userDefined=True) or []
                self.is_arp_body = any(a.startswith('arp_') for a in attrs)
                self.tag_arp_custom = self.is_arp_body
        
        # In Maya, we'd show a dialog
        return self.execute(context)
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        # Get objects
        body_rig = None
        faceit_rig = None
        head_bone_name = ""
        
        if cmds.objExists("faceit_core_data"):
            body_rig = cmds.getAttr("faceit_core_data.body_armature") or ""
            faceit_rig = cmds.getAttr("faceit_core_data.armature") or ""
            head_bone_name = cmds.getAttr("faceit_core_data.body_armature_head_bone") or ""
        
        if not body_rig or not cmds.objExists(body_rig):
            cmds.warning("Body rig not found.")
            return {'CANCELLED'}
        
        if not faceit_rig or not cmds.objExists(faceit_rig):
            cmds.warning("Faceit rig not found.")
            return {'CANCELLED'}
        
        if not head_bone_name or not cmds.objExists(head_bone_name):
            cmds.warning("Head bone not found.")
            return {'CANCELLED'}
        
        faceit_objects = futils.get_faceit_objects_list()
        
        if not faceit_objects:
            cmds.warning("No Faceit objects found.")
            return {'CANCELLED'}
        
        # Show rigs
        cmds.setAttr(f"{body_rig}.visibility", 1)
        cmds.setAttr(f"{faceit_rig}.visibility", 1)
        
        # Get bone groups if keeping
        faceit_bone_groups = {}
        if self.keep_faceit_bone_groups:
            faceit_bone_groups = rig_utils.get_bone_groups_dict(faceit_rig)
        
        # Get all Faceit bones
        all_faceit_bones = []
        if self.tag_arp_custom:
            all_faceit_bones = cmds.ls(f"{faceit_rig}.bones", type='joint') or []
        
        # Merge weights
        if self.merge_faceit_weights:
            self._merge_weights(faceit_objects, body_rig, faceit_rig)
        
        # Remove Faceit armature modifier
        for obj in faceit_objects:
            if not cmds.objExists(obj):
                continue
            
            # Find skin cluster using Faceit rig
            history = cmds.listHistory(obj, pruneDagObjects=True, interestLevel=2) or []
            for node in history:
                if cmds.nodeType(node) == 'skinCluster':
                    influences = cmds.skinCluster(node, query=True, influence=True) or []
                    if faceit_rig in influences:
                        cmds.delete(node)
                        break
            
            # Remove Faceit vertex groups if not merging
            if not self.merge_faceit_weights:
                deform_groups = vg_utils.get_deform_bones_from_armature(faceit_rig)
                groups = vg_utils.get_vertex_groups(obj)
                for grp in groups:
                    if grp in deform_groups:
                        vg_utils.delete_vertex_group(obj, grp)
        
        # Join armatures
        self._join_armatures(faceit_rig, body_rig, head_bone_name)
        
        # Restore bone groups
        if self.keep_faceit_bone_groups and faceit_bone_groups:
            rig_utils.set_bone_groups_from_dict(body_rig, faceit_bone_groups)
        
        # Remove eye bone constraints
        self._remove_eye_constraints(body_rig)
        
        # Tag ARP custom bones
        if self.tag_arp_custom:
            all_faceit_bones.append('ORG-face')
            for bone in all_faceit_bones:
                if cmds.objExists(bone):
                    cmds.addAttr(bone, ln="cc", attributeType="float", defaultValue=1.0)
        
        # Set Faceit armature to body rig
        if cmds.objExists("faceit_core_data"):
            if cmds.attributeQuery("armature", node="faceit_core_data", exists=True):
                cmds.setAttr("faceit_core_data.armature", body_rig, type="string")
            
            # Set faceit_rig_id if not present
            if not cmds.attributeQuery("faceit_rig_id", node=body_rig, exists=True):
                cmds.addAttr(body_rig, ln="faceit_rig_id", dt="string")
                cmds.setAttr(f"{body_rig}.faceit_rig_id", str(get_random_rig_id()), type="string")
        
        cmds.warning(f"Successfully joined the FaceitRig to the armature {body_rig}")
        return {'FINISHED'}
    
    def _merge_weights(self, faceit_objects: List[str], body_rig: str, faceit_rig: str) -> None:
        """Merge Faceit weights with body weights."""
        # Get deform groups
        faceit_deform_groups = vg_utils.get_deform_bones_from_armature(faceit_rig)
        body_deform_groups = vg_utils.get_deform_bones_from_armature(body_rig)
        
        # Check for overlapping groups
        overlap = [g for g in faceit_deform_groups if g in body_deform_groups]
        if overlap:
            cmds.warning(f"Some vertex groups are used in both armatures: {overlap}")
        
        # Process each object
        for obj in faceit_objects:
            if not cmds.objExists(obj):
                continue
            
            # Show object
            cmds.setAttr(f"{obj}.visibility", 1)
            
            # Get faceit groups on this object
            obj_groups = vg_utils.get_vertex_groups(obj)
            faceit_groups = [g for g in obj_groups if g in faceit_deform_groups]
            
            if not faceit_groups:
                continue
            
            # Store vertex lock states
            lock_states = {}
            for grp in obj_groups:
                if cmds.attributeQuery("lockWeight", node=f"{obj}.vertexGroups[{grp}]", exists=True):
                    lock_states[grp] = cmds.getAttr(f"{obj}.vertexGroups[{grp}].lockWeight")
            
            # Invert DEF-face weights
            if 'DEF-face' in obj_groups:
                # Create inverted weights
                inv_grp = vg_utils.invert_vertex_group_weights(obj, 'DEF-face')
                vg_utils.delete_vertex_group(obj, 'DEF-face')
            else:
                # Assign all vertices to DEF-face_invert
                vertex_count = cmds.polyEvaluate(obj, vertex=True)
                vertices = list(range(vertex_count))
                vg_utils.assign_vertex_grp(obj, vertices, 'DEF-face_invert', overwrite=True)
            
            # Lock DEF-face_invert
            if 'DEF-face_invert' in vg_utils.get_vertex_groups(obj):
                if cmds.attributeQuery("lockWeight", node=f"{obj}.vertexGroups['DEF-face_invert']", exists=True):
                    cmds.setAttr(f"{obj}.vertexGroups['DEF-face_invert'].lockWeight", 1)
            
            # Normalize weights
            cmds.select(obj)
            cmds.skinCluster(obj, edit=True, normalizeWeights=1)
            
            # Restore lock states
            for grp, locked in lock_states.items():
                if cmds.attributeQuery("lockWeight", node=f"{obj}.vertexGroups[{grp}]", exists=True):
                    cmds.setAttr(f"{obj}.vertexGroups[{grp}].lockWeight", locked)
    
    def _join_armatures(self, source_rig: str, target_rig: str, head_bone: str) -> None:
        """Join two armatures."""
        # Select both rigs
        cmds.select(source_rig, target_rig)
        
        # In Maya, we'd use a combine operation
        # For now, just parent the source rig to the target rig
        cmds.parent(source_rig, target_rig)
        
        # Rename ORG-face
        if cmds.objExists("DEF-face"):
            cmds.rename("DEF-face", "ORG-face")
            cmds.setAttr("ORG-face.deform", 0)
            cmds.parent("ORG-face", head_bone)
    
    def _remove_eye_constraints(self, rig: str) -> None:
        """Remove eye bone constraints."""
        eyelid_def_bones = [
            'DEF-lid.B.L', 'DEF-lid.B.L.001', 'DEF-lid.B.L.002', 'DEF-lid.B.L.003',
            'DEF-lid.T.L', 'DEF-lid.T.L.001', 'DEF-lid.T.L.002', 'DEF-lid.T.L.003',
            'DEF-lid.B.R', 'DEF-lid.B.R.001', 'DEF-lid.B.R.002', 'DEF-lid.B.R.003',
            'DEF-lid.T.R', 'DEF-lid.T.R.001', 'DEF-lid.T.R.002', 'DEF-lid.T.R.003'
        ]
        
        for bone in eyelid_def_bones:
            if not cmds.objExists(bone):
                continue
            
            constraints = cmds.listConnections(f"{bone}.constraints") or []
            for constraint in constraints:
                if cmds.objExists(constraint) and cmds.nodeType(constraint) == 'constraint':
                    # Check if it's a copy rotation constraint
                    if cmds.attributeQuery("rotate", node=constraint, exists=True):
                        cmds.delete(constraint)