# finalize_operators.py
# Maya Faceit Plugin - Finalize Operators
# Converted from Blender to Maya Python 3.11

"""
Finalize operators for Faceit Maya plugin.
Handles cleanup and finalization of Faceit data.
"""

import maya.cmds as cmds # type: ignore
from typing import List, Dict, Optional, Any

from ..core import faceit_utils as futils
from ..core import vgroup_utils as vg_utils
from ..core import shape_key_utils as sk_utils
from ..core import modifier_utils
from ..core import corrective_utils


# ============================================================
# CleanUp Objects Operator
# ============================================================

class CleanUpObjects:
    """
    Clean up all traces of the Faceit Rigging process for faceit objects.
    """
    
    name = "CleanUpObjects"
    label = "Clean Up Objects"
    
    def __init__(self):
        self.operate_scope = 'SELECTED'
        self.remove_faceit_armature_modifier = True
        self.remove_faceit_bind_weights = True
        self.remove_faceit_vertex_groups = True
        self.remove_faceit_corrective_shapes = True
        self.remove_from_registration = True
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return True
    
    def invoke(self, context: Any = None) -> str:
        """Invoke the operator."""
        # In Maya, we'd show a dialog
        return self.execute(context)
    
    def execute(self, context: Any = None) -> str:
        """Execute the operator."""
        scope = self.operate_scope
        
        # Get objects based on scope
        if scope == 'ALL':
            op_objects = self._get_all_mesh_objects()
        elif scope == 'FACEIT':
            op_objects = futils.get_faceit_objects_list()
        elif scope == 'SELECTED':
            op_objects = cmds.ls(selection=True, type='transform')
            if not op_objects:
                cmds.warning("You need to select at least one object in this scope.")
                return {'CANCELLED'}
        else:
            op_objects = []
        
        # Get deform groups from rig
        rig = futils.get_faceit_armature()
        deform_groups = []
        if rig:
            deform_groups = vg_utils.get_deform_bones_from_armature(rig)
        
        # Process each object
        for obj in op_objects:
            if not cmds.objExists(obj):
                continue
            
            # Check if it's a mesh
            shapes = cmds.listRelatives(obj, shapes=True, type='mesh')
            if not shapes:
                continue
            
            # Remove armature modifier
            if self.remove_faceit_armature_modifier:
                self._remove_armature_modifier(obj, rig)
            
            # Remove bind weights
            if self.remove_faceit_bind_weights:
                self._remove_bind_weights(obj, deform_groups)
            
            # Remove Faceit vertex groups
            if self.remove_faceit_vertex_groups:
                self._remove_faceit_vertex_groups(obj)
        
        # Remove corrective shape keys
        if self.remove_faceit_corrective_shapes:
            self._remove_corrective_shape_keys(op_objects)
        
        # Remove from registration
        if self.remove_from_registration:
            self._remove_from_registration()
        
        return {'FINISHED'}
    
    def _get_all_mesh_objects(self) -> List[str]:
        """Get all mesh objects in the scene."""
        meshes = cmds.ls(type='mesh')
        transforms = []
        
        for mesh in meshes:
            parent = cmds.listRelatives(mesh, parent=True, type='transform')
            if parent:
                transforms.append(parent[0])
        
        return list(set(transforms))
    
    def _remove_armature_modifier(self, obj: str, rig: str) -> None:
        """Remove armature modifier from object."""
        if not rig:
            return
        
        # Find skin cluster
        history = cmds.listHistory(obj, pruneDagObjects=True, interestLevel=2) or []
        for node in history:
            if cmds.nodeType(node) == 'skinCluster':
                influences = cmds.skinCluster(node, query=True, influence=True) or []
                if rig in influences:
                    cmds.delete(node)
                    break
    
    def _remove_bind_weights(self, obj: str, deform_groups: List[str]) -> None:
        """Remove bind weights from object."""
        if not deform_groups:
            return
        
        groups = vg_utils.get_vertex_groups(obj)
        
        for grp in groups:
            if grp in deform_groups:
                # Check if locked
                if cmds.attributeQuery("lockWeight", node=f"{obj}.vertexGroups[{grp}]", exists=True):
                    locked = cmds.getAttr(f"{obj}.vertexGroups[{grp}].lockWeight")
                    if locked:
                        continue
                
                vg_utils.delete_vertex_group(obj, grp)
    
    def _remove_faceit_vertex_groups(self, obj: str) -> None:
        """Remove Faceit vertex groups from object."""
        vg_utils.remove_faceit_vertex_grps(obj)
    
    def _remove_corrective_shape_keys(self, objects: List[str]) -> None:
        """Remove corrective shape keys from objects."""
        for obj in objects:
            if not cmds.objExists(obj):
                continue
            
            if sk_utils.has_shape_keys(obj):
                blend_node = sk_utils.get_blend_shape_node(obj)
                if blend_node:
                    targets = sk_utils.get_blend_shape_targets(obj)
                    for target in targets:
                        if target.startswith(corrective_utils.CORRECTIVE_SK_PREFIX):
                            cmds.removeMultiInstance(f"{blend_node}.weight[{target}]")
    
    def _remove_from_registration(self) -> None:
        """Remove objects from Faceit registration."""
        # In Maya, we'd clear the faceit_objects list
        if cmds.objExists("faceit_core_data"):
            if cmds.attributeQuery("faceit_objects", node="faceit_core_data", exists=True):
                cmds.setAttr("faceit_core_data.faceit_objects", "", type="string")


# ============================================================
# CleanUp Scene Operator
# ============================================================

class CleanUpScene:
    """
    Clean up all traces of the Faceit Rigging process in the scene and other data.
    """
    
    name = "CleanUpScene"
    label = "Clean Up All"
    
    def __init__(self):
        # Quick selection
        self.purge_scope = 'NONE'
        
        # Faceit Properties
        self.reset_faceit_properties = True
        self.purge_scene = True
        
        # Faceit Objects
        self.remove_control_rigs = False
        self.remove_landmarks = False
        self.remove_face_rig = False
        self.remove_actions = False
        
        # Registered Meshes
        self.operate_scope = 'FACEIT'
        self.remove_faceit_armature_modifier = False
        self.remove_faceit_bind_weights = False
        self.remove_faceit_vertex_groups = False
        self.remove_faceit_corrective_shapes = False
        
        # State tracking
        self.control_rigs_found = False
        self.faceit_rig_found = False
        self.faceit_landmarks_found = False
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return True
    
    def invoke(self, context: Any = None) -> str:
        """Invoke the operator."""
        # Check for Faceit objects
        self.control_rigs_found = bool(futils.get_faceit_control_armatures())
        self.faceit_rig_found = bool(futils.get_faceit_armature())
        self.faceit_landmarks_found = cmds.objExists('facial_landmarks')
        
        # In Maya, we'd show a dialog
        return self.execute(context)
    
    def execute(self, context: Any = None) -> str:
        """Execute the operator."""
        # Remove control rigs
        if self.remove_control_rigs:
            self._remove_control_rigs()
        
        # Remove landmarks
        if self.remove_landmarks:
            self._remove_landmarks()
        
        # Clean up objects
        self._cleanup_objects()
        
        # Remove face rig
        if self.remove_face_rig:
            self._remove_face_rig()
        
        # Remove actions
        if self.remove_actions:
            self._remove_actions()
        
        # Reset Faceit properties
        if self.reset_faceit_properties:
            self._reset_faceit_properties()
        
        # Purge scene
        if self.purge_scene:
            self._purge_scene()
        
        return {'FINISHED'}
    
    def _remove_control_rigs(self) -> None:
        """Remove all control rigs."""
        control_rigs = futils.get_faceit_control_armatures()
        
        for crig in control_rigs:
            if not cmds.objExists(crig):
                continue
            
            # Remove drivers
            self._remove_control_drivers(crig)
            
            # Delete the rig
            cmds.delete(crig)
        
        # Clear control rig reference
        if cmds.objExists("faceit_core_data"):
            if cmds.attributeQuery("control_rig", node="faceit_core_data", exists=True):
                cmds.setAttr("faceit_core_data.control_rig", "", type="string")
    
    def _remove_control_drivers(self, c_rig: str) -> None:
        """Remove control drivers from a rig."""
        if not cmds.objExists(c_rig):
            return
        
        # Get target objects
        target_objects = self._get_crig_objects(c_rig)
        
        for obj in target_objects:
            if not cmds.objExists(obj):
                continue
            
            if sk_utils.has_shape_keys(obj):
                blend_node = sk_utils.get_blend_shape_node(obj)
                if blend_node:
                    targets = sk_utils.get_blend_shape_targets(obj)
                    for target in targets:
                        # Remove driver connections
                        connections = cmds.listConnections(f"{blend_node}.{target}", source=True, destination=False) or []
                        for conn in connections:
                            if cmds.nodeType(conn) == 'animCurve':
                                cmds.delete(conn)
    
    def _get_crig_objects(self, c_rig: str) -> List[str]:
        """Get target objects from control rig."""
        if not cmds.objExists(c_rig):
            return []
        
        if cmds.attributeQuery("faceit_crig_objects", node=c_rig, exists=True):
            objects_str = cmds.getAttr(f"{c_rig}.faceit_crig_objects") or ""
            return objects_str.split(',') if objects_str else []
        
        return []
    
    def _remove_landmarks(self) -> None:
        """Remove landmarks mesh."""
        if cmds.objExists('facial_landmarks'):
            cmds.delete('facial_landmarks')
    
    def _cleanup_objects(self) -> None:
        """Clean up objects using CleanUpObjects."""
        cleanup = CleanUpObjects()
        cleanup.operate_scope = self.operate_scope
        cleanup.remove_faceit_armature_modifier = self.remove_faceit_armature_modifier
        cleanup.remove_faceit_bind_weights = self.remove_faceit_bind_weights
        cleanup.remove_faceit_vertex_groups = self.remove_faceit_vertex_groups
        cleanup.remove_faceit_corrective_shapes = self.remove_faceit_corrective_shapes
        cleanup.remove_from_registration = False
        
        cleanup.execute()
    
    def _remove_face_rig(self) -> None:
        """Remove the Faceit armature."""
        rig = futils.get_faceit_armature()
        if rig:
            # Remove skin clusters first
            self._remove_skin_clusters(rig)
            
            # Delete the rig
            cmds.delete(rig)
            
            # Clear armature reference
            if cmds.objExists("faceit_core_data"):
                if cmds.attributeQuery("armature", node="faceit_core_data", exists=True):
                    cmds.setAttr("faceit_core_data.armature", "", type="string")
    
    def _remove_skin_clusters(self, rig: str) -> None:
        """Remove skin clusters using the rig."""
        if not cmds.objExists(rig):
            return
        
        # Find all skin clusters using this rig
        all_objects = cmds.ls(type='transform')
        
        for obj in all_objects:
            history = cmds.listHistory(obj, pruneDagObjects=True, interestLevel=2) or []
            for node in history:
                if cmds.nodeType(node) == 'skinCluster':
                    influences = cmds.skinCluster(node, query=True, influence=True) or []
                    if rig in influences:
                        cmds.delete(node)
    
    def _remove_actions(self) -> None:
        """Remove Faceit actions."""
        action_names = [
            'faceit_bake_test_action',
            'faceit_shape_action',
            'overwrite_shape_action',
            corrective_utils.CORRECTIVE_SK_ACTION_NAME,
        ]
        
        for action_name in action_names:
            if cmds.objExists(action_name):
                cmds.delete(action_name)
    
    def _reset_faceit_properties(self) -> None:
        """Reset Faceit properties to defaults."""
        if not cmds.objExists("faceit_core_data"):
            return
        
        # Get all attributes
        attrs = cmds.listAttr("faceit_core_data", userDefined=True) or []
        
        for attr in attrs:
            # Skip version attribute
            if attr == 'version':
                continue
            
            # Reset to default
            attr_type = cmds.attributeQuery(attr, node="faceit_core_data", attributeType=True)
            
            if attr_type == 'string':
                cmds.setAttr(f"faceit_core_data.{attr}", "", type="string")
            elif attr_type == 'long':
                cmds.setAttr(f"faceit_core_data.{attr}", 0)
            elif attr_type == 'float':
                cmds.setAttr(f"faceit_core_data.{attr}", 0.0)
            elif attr_type == 'double':
                cmds.setAttr(f"faceit_core_data.{attr}", 0.0)
    
    def _purge_scene(self) -> None:
        """Purge unused data from the scene."""
        # Clean up invalid nodes
        cmds.cleanupScene()
        
        # Remove unused nodes
        cmds.mayaNamespace(removeAll=True, mergeNamespaceWithRoot=True)