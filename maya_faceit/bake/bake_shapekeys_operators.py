# bake_shapekeys_operators.py
# Maya Faceit Plugin - Bake Shape Keys Operators
# Converted from Blender to Maya Python 3.11

"""
Bake shape keys operators for Faceit Maya plugin.
Handles generating shape keys from expressions and back to rigging.
"""

import maya.cmds as cmds # type: ignore
import maya.api.OpenMaya as om2 # type: ignore
import time
import numpy as np
from typing import List, Dict, Optional, Any, Tuple

from ..core import faceit_data as fdata
from ..core import faceit_utils as futils
from ..core import shape_key_utils
from ..core import modifier_utils
from ..core import pose_utils
from ..core import detection_manager
from ..core import fc_dr_utils


# ============================================================
# Generate Shape Keys Operator
# ============================================================

class GenerateShapekeys:
    """
    Bakes all deformation stored in the created expressions to shape keys on the registered objects.
    """
    
    name = "GenerateShapekeys"
    label = "Bake Shape Keys"
    
    def __init__(self):
        self.modifier_action = 'FACEIT'
        self.load_action = 'NONE'
        self.init_arkit_shape_list = False
        self.init_a2f_shape_list = False
        self.keep_faceit_rig_active = False
        self.disable_auto_keying = True
        self.bake_duplicate_option = 'OVERWRITE'
        
        # State tracking
        self.faceit_action_found = False
        self.expressions_generated = False
        self.arkit_expressions_found = False
        self.a2f_expressions_found = False
        self.faceit_original_rig = True
        self.auto_keying_enabled = False
        self.found_bake_modifiers = False
        self.some_objects_without_bake_modifiers = False
        self.shapes_already_exist = False
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        # Check if shapes are already generated
        if cmds.objExists("faceit_core_data"):
            if cmds.attributeQuery("shapes_generated", node="faceit_core_data", exists=True):
                if cmds.getAttr("faceit_core_data.shapes_generated"):
                    return False
        
        # Check if there are Faceit objects
        faceit_objects = futils.get_faceit_objects_list()
        if not faceit_objects:
            return False
        
        # Check if there's a rig
        rig = futils.get_faceit_armature()
        if not rig:
            return False
        
        # Check if there are expressions
        if cmds.objExists("faceit_core_data"):
            if cmds.attributeQuery("expression_names", node="faceit_core_data", exists=True):
                names_str = cmds.getAttr("faceit_core_data.expression_names") or ""
                if names_str:
                    return True
        
        return False
    
    def invoke(self, context: Any = None) -> str:
        """Invoke the operator."""
        # Check auto keying state
        self.auto_keying_enabled = cmds.autoKeyframe(query=True, state=True)
        self.disable_auto_keying = self.auto_keying_enabled
        
        # Check rig type
        rig = futils.get_faceit_armature()
        self.faceit_original_rig = bool(futils.is_faceit_original_armature(rig))
        
        # Check for action
        if rig and cmds.attributeQuery("currentAction", node=rig, exists=True):
            action = cmds.getAttr(f"{rig}.currentAction") or ""
            if action and cmds.objExists(action):
                self.faceit_action_found = True
        
        # Check expressions
        if cmds.objExists("faceit_core_data"):
            names_str = cmds.getAttr("faceit_core_data.expression_names") or ""
            names = names_str.split(',') if names_str else []
            
            if names:
                self.expressions_generated = True
                
                # Check for ARKit expressions
                arkit_names = fdata.get_arkit_shape_data().keys()
                self.arkit_expressions_found = any(n in arkit_names for n in names)
                
                # Check for A2F expressions
                a2f_names = fdata.get_a2f_shape_data().keys()
                self.a2f_expressions_found = any(n in a2f_names for n in names)
        
        # Check for bake modifiers
        faceit_objects = futils.get_faceit_objects_list()
        for obj in faceit_objects:
            if cmds.objExists(obj):
                if cmds.attributeQuery("faceit_bake_mods", node=obj, exists=True):
                    mods_str = cmds.getAttr(f"{obj}.faceit_bake_mods") or ""
                    if mods_str:
                        self.found_bake_modifiers = True
                    else:
                        self.some_objects_without_bake_modifiers = True
        
        # Check if shapes already exist
        shape_names = shape_key_utils.get_shape_key_names_from_objects()
        if shape_names and names:
            self.shapes_already_exist = any(n in shape_names for n in names)
        
        # In Maya, we'd show a dialog
        return self.execute(context)
    
    def execute(self, context: Any = None) -> str:
        """Execute the operator."""
        # Save scene state
        state_dict = futils.save_scene_state()
        
        # Get objects
        bake_objects = futils.get_faceit_objects_list()
        rig = futils.get_faceit_armature()
        
        if not bake_objects:
            cmds.warning("No Faceit objects found")
            return {'CANCELLED'}
        
        if not rig:
            cmds.warning("No Faceit rig found")
            return {'CANCELLED'}
        
        # Get expression data
        expr_data = self._get_expression_data()
        if not expr_data:
            cmds.warning("No expressions found")
            return {'CANCELLED'}
        
        # Show objects
        for obj in bake_objects:
            if cmds.objExists(obj):
                cmds.setAttr(f"{obj}.visibility", 1)
        
        # Get corrective shape key state
        use_corrective = False
        if cmds.objExists("faceit_core_data"):
            if cmds.attributeQuery("use_corrective_shapes", node="faceit_core_data", exists=True):
                use_corrective = cmds.getAttr("faceit_core_data.use_corrective_shapes")
        
        # Reset expression values
        self._reset_expression_values()
        
        # Prepare objects for baking
        obj_settings = self._prepare_objects_for_baking(bake_objects, rig)
        
        # Bake each expression
        self._bake_expressions(expr_data, bake_objects, obj_settings)
        
        # Handle mouth close special case
        self._fix_mouth_close(bake_objects)
        
        # Restore objects
        self._restore_objects_after_baking(bake_objects, rig, obj_settings)
        
        # Handle actions
        self._handle_actions(rig)
        
        # Set shapes generated flag
        set_shapes_generated(True)
        
        # Initialize retargeting
        self._init_retargeting(context)
        
        # Load action
        self._load_action(context)
        
        # Restore scene state
        futils.restore_scene_state(state_dict)
        
        # Disable auto keying if requested
        if self.disable_auto_keying:
            cmds.autoKeyframe(state=False)
        
        # Hide landmarks
        if cmds.objExists('facial_landmarks'):
            cmds.setAttr('facial_landmarks.visibility', 0)
        
        # Hide rig if not keeping active
        if self.faceit_original_rig and not self.keep_faceit_rig_active:
            if rig:
                cmds.setAttr(f"{rig}.visibility", 0)
        
        cmds.warning("Shape keys generated successfully")
        return {'FINISHED'}
    
    def _get_expression_data(self) -> Dict:
        """Get expression data from scene."""
        if not cmds.objExists("faceit_core_data"):
            return {}
        
        data = {}
        
        if cmds.attributeQuery("expression_names", node="faceit_core_data", exists=True):
            names_str = cmds.getAttr("faceit_core_data.expression_names") or ""
            data['names'] = names_str.split(',') if names_str else []
        
        if cmds.attributeQuery("expression_frames", node="faceit_core_data", exists=True):
            frames_str = cmds.getAttr("faceit_core_data.expression_frames") or ""
            data['frames'] = [int(x) for x in frames_str.split(',')] if frames_str else []
        
        if cmds.attributeQuery("expression_sides", node="faceit_core_data", exists=True):
            sides_str = cmds.getAttr("faceit_core_data.expression_sides") or ""
            data['sides'] = sides_str.split(',') if sides_str else []
        
        return data
    
    def _reset_expression_values(self) -> None:
        """Reset expression values to default."""
        faceit_objects = futils.get_faceit_objects_list()
        
        for obj in faceit_objects:
            if not cmds.objExists(obj):
                continue
            
            if shape_key_utils.has_shape_keys(obj):
                blend_node = shape_key_utils.get_blend_shape_node(obj)
                if blend_node:
                    targets = shape_key_utils.get_blend_shape_targets(obj)
                    for target in targets:
                        cmds.setAttr(f"{blend_node}.{target}", 0)
    
    def _prepare_objects_for_baking(self, objects: List[str], rig: str) -> Dict:
        """Prepare objects for baking."""
        obj_settings = {}
        
        for obj in objects:
            if not cmds.objExists(obj):
                continue
            
            settings = {
                'mirror_x': False,
                'modifiers': [],
                'drivers': [],
                'has_corrective_sk': False,
            }
            
            # Disable mirror
            if cmds.attributeQuery("useMirrorX", node=obj, exists=True):
                settings['mirror_x'] = cmds.getAttr(f"{obj}.useMirrorX")
                cmds.setAttr(f"{obj}.useMirrorX", 0)
            
            # Get basis data
            settings['basis_data'] = self._get_mesh_data(obj, evaluated=False)
            
            # Get evaluated data
            settings['eval_data'] = self._get_mesh_data(obj, evaluated=True)
            
            # Get world matrix
            settings['matrix_world'] = cmds.xform(obj, query=True, worldSpace=True, matrix=True)
            
            obj_settings[obj] = settings
        
        return obj_settings
    
    def _get_mesh_data(self, obj: str, evaluated: bool = False) -> np.ndarray:
        """Get mesh vertex data."""
        if not cmds.objExists(obj):
            return np.array([])
        
        vertex_count = cmds.polyEvaluate(obj, vertex=True)
        positions = np.zeros((vertex_count, 3), dtype=np.float32)
        
        for i in range(vertex_count):
            if evaluated:
                pos = cmds.xform(f"{obj}.vtx[{i}]", query=True, worldSpace=True, translation=True)
            else:
                pos = cmds.xform(f"{obj}.vtx[{i}]", query=True, objectSpace=True, translation=True)
            
            if pos:
                positions[i] = pos
        
        return positions
    
    def _bake_expressions(self, expr_data: Dict, objects: List[str], obj_settings: Dict) -> None:
        """Bake expressions to shape keys."""
        names = expr_data.get('names', [])
        frames = expr_data.get('frames', [])
        
        for i, name in enumerate(names):
            if i >= len(frames):
                continue
            
            frame = frames[i]
            cmds.currentTime(frame)
            
            for obj in objects:
                if not cmds.objExists(obj) or obj not in obj_settings:
                    continue
                
                settings = obj_settings[obj]
                
                # Check if shape already exists
                shape_exists = False
                if shape_key_utils.has_shape_keys(obj):
                    blend_node = shape_key_utils.get_blend_shape_node(obj)
                    if blend_node and cmds.attributeQuery(name, node=blend_node, exists=True):
                        shape_exists = True
                
                # Handle duplicate
                final_name = name
                if shape_exists:
                    if self.bake_duplicate_option == 'OVERWRITE':
                        # Remove existing shape
                        if blend_node:
                            cmds.removeMultiInstance(f"{blend_node}.weight[{name}]")
                    elif self.bake_duplicate_option == 'RENAME':
                        # Rename existing
                        new_name = detection_manager.get_expression_name_double_entries(
                            name, shape_key_utils.get_blend_shape_targets(obj)
                        )
                        if blend_node:
                            cmds.aliasAttr(new_name, f"{blend_node}.weight[{name}]")
                    elif self.bake_duplicate_option == 'DUPLICATE':
                        # Create duplicate with suffix
                        final_name = detection_manager.get_expression_name_double_entries(
                            name, shape_key_utils.get_blend_shape_targets(obj)
                        )
                
                # Get evaluated mesh data
                exp_data = self._get_mesh_data(obj, evaluated=True)
                
                # Calculate shape data
                basis_data = settings['basis_data']
                eval_data = settings['eval_data']
                shape_data = basis_data + exp_data - eval_data
                
                # Apply world matrix
                mat_rest = settings['matrix_world']
                mat_pose = cmds.xform(obj, query=True, worldSpace=True, matrix=True)
                
                # Create shape key
                self._create_shape_key(obj, final_name, shape_data)
    
    def _create_shape_key(self, obj: str, name: str, data: np.ndarray) -> None:
        """Create a shape key on an object."""
        if not cmds.objExists(obj) or data.size == 0:
            return
        
        # Get or create blend shape node
        blend_node = shape_key_utils.get_blend_shape_node(obj)
        if not blend_node:
            blend_node = cmds.blendShape(obj, name=f"{obj}_faceit_blendShape")[0]
        
        # Create temporary mesh with shape data
        temp_mesh = self._create_temp_mesh(obj, data)
        
        if temp_mesh:
            # Add as blend shape target
            cmds.blendShape(blend_node, edit=True, target=(obj, 0, temp_mesh, 1.0))
            
            # Rename target
            weight_attrs = cmds.listAttr(f"{blend_node}.weight", multi=True) or []
            weight_attrs = [a for a in weight_attrs if a.startswith('weight[')]
            
            if weight_attrs:
                last_weight = weight_attrs[-1]
                cmds.aliasAttr(name, f"{blend_node}.{last_weight}")
            
            # Set weight to 0
            cmds.setAttr(f"{blend_node}.{name}", 0)
            
            # Clean up
            cmds.delete(temp_mesh)
    
    def _create_temp_mesh(self, obj: str, data: np.ndarray) -> Optional[str]:
        """Create a temporary mesh with vertex data."""
        if data.size == 0:
            return None
        
        # Duplicate mesh
        temp_mesh = cmds.duplicate(obj, name=f"{obj}_temp")[0]
        
        # Set vertex positions
        vertex_count = cmds.polyEvaluate(temp_mesh, vertex=True)
        for i in range(min(vertex_count, len(data))):
            cmds.xform(f"{temp_mesh}.vtx[{i}]", objectSpace=True, translation=list(data[i]))
        
        return temp_mesh
    
    def _fix_mouth_close(self, objects: List[str]) -> None:
        """Fix mouth close shape key."""
        for obj in objects:
            if not cmds.objExists(obj):
                continue
            
            if not shape_key_utils.has_shape_keys(obj):
                continue
            
            blend_node = shape_key_utils.get_blend_shape_node(obj)
            if not blend_node:
                continue
            
            if not cmds.attributeQuery("mouthClose", node=blend_node, exists=True):
                continue
            
            if not cmds.attributeQuery("jawOpen", node=blend_node, exists=True):
                continue
            
            # Get shape data
            mouth_close = shape_key_utils.get_blend_shape_targets(obj)
            jaw_open = shape_key_utils.get_blend_shape_targets(obj)
            
            # In Maya, we'd need to calculate the corrected shape
            # This would involve getting the vertex positions from the blend targets
    
    def _restore_objects_after_baking(self, objects: List[str], rig: str, obj_settings: Dict) -> None:
        """Restore objects after baking."""
        for obj in objects:
            if not cmds.objExists(obj) or obj not in obj_settings:
                continue
            
            settings = obj_settings[obj]
            
            # Restore mirror
            if cmds.attributeQuery("useMirrorX", node=obj, exists=True):
                cmds.setAttr(f"{obj}.useMirrorX", 1 if settings['mirror_x'] else 0)
            
            # Remove armature modifier if not keeping rig active
            if not self.keep_faceit_rig_active:
                self._remove_armature_modifier(obj, rig)
    
    def _remove_armature_modifier(self, obj: str, rig: str) -> None:
        """Remove armature modifier from object."""
        if not cmds.objExists(obj) or not cmds.objExists(rig):
            return
        
        history = cmds.listHistory(obj, pruneDagObjects=True, interestLevel=2) or []
        for node in history:
            if cmds.nodeType(node) == 'skinCluster':
                influences = cmds.skinCluster(node, query=True, influence=True) or []
                if rig in influences:
                    cmds.delete(node)
                    break
    
    def _handle_actions(self, rig: str) -> None:
        """Handle actions after baking."""
        # Set fake user on actions
        if cmds.objExists("overwrite_shape_action"):
            cmds.setAttr("overwrite_shape_action.useFakeUser", 1)
        
        if cmds.objExists("faceit_shape_action"):
            cmds.setAttr("faceit_shape_action.useFakeUser", 1)
        
        # Clear rig action
        if rig and cmds.attributeQuery("currentAction", node=rig, exists=True):
            cmds.setAttr(f"{rig}.currentAction", "", type="string")
        
        # Reset bones
        self._reset_rig_bones(rig)
    
    def _reset_rig_bones(self, rig: str) -> None:
        """Reset rig bones to rest pose."""
        if not rig:
            return
        
        bones = cmds.ls(f"{rig}.bones", type='joint') or []
        for bone in bones:
            pose_utils.reset_pb(bone)
    
    def _init_retargeting(self, context: Any) -> None:
        """Initialize retargeting."""
        # In Maya, we'd initialize retarget data
        pass
    
    def _load_action(self, context: Any) -> None:
        """Load action after baking."""
        if self.load_action == 'TEST':
            self._load_test_action()
        elif self.load_action == 'MOCAP':
            self._load_mocap_action()
    
    def _load_test_action(self) -> None:
        """Load test action."""
        # In Maya, we'd load a test animation
        pass
    
    def _load_mocap_action(self) -> None:
        """Load mocap action."""
        # In Maya, we'd load the mocap action
        pass


# ============================================================
# Back To Rigging Operator
# ============================================================

class BackToRigging:
    """
    Reset Faceit to Rigging and Posing functionality, removes the baked Shape Keys.
    """
    
    name = "BackToRigging"
    label = "Back to Rigging"
    
    def __init__(self):
        self.keep_baked_expressions = False
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return True
    
    def invoke(self, context: Any = None) -> str:
        """Invoke the operator."""
        # In Maya, we'd show a dialog
        return self.execute(context)
    
    def execute(self, context: Any = None) -> str:
        """Execute the operator."""
        # Get objects
        faceit_objects = futils.get_faceit_objects_list()
        rig = futils.get_faceit_armature()
        c_rig = futils.get_faceit_control_armature()
        
        # Show rig
        if rig:
            cmds.setAttr(f"{rig}.visibility", 1)
        else:
            cmds.warning("The Faceit Armature can't be found.")
        
        # Remove control rig drivers
        if c_rig:
            self._remove_control_drivers(c_rig)
        
        # Remove test action
        if cmds.objExists("faceit_bake_test_action"):
            cmds.delete("faceit_bake_test_action")
        
        # Get expression data
        expr_data = self._get_expression_data()
        names = expr_data.get('names', [])
        
        # Reset expression values
        self._reset_expression_values()
        
        # Remove shape keys if not keeping
        if not self.keep_baked_expressions:
            for obj in faceit_objects:
                if not cmds.objExists(obj):
                    continue
                
                if shape_key_utils.has_shape_keys(obj):
                    blend_node = shape_key_utils.get_blend_shape_node(obj)
                    if blend_node:
                        for name in names:
                            if cmds.attributeQuery(name, node=blend_node, exists=True):
                                cmds.removeMultiInstance(f"{blend_node}.weight[{name}]")
        
        # Restore bake modifiers
        self._restore_bake_modifiers(faceit_objects)
        
        # Clear animation
        self._clear_animation(faceit_objects)
        
        # Restore corrective shape keys
        if cmds.objExists("faceit_core_data"):
            if cmds.attributeQuery("use_corrective_shapes", node="faceit_core_data", exists=True):
                if cmds.getAttr("faceit_core_data.use_corrective_shapes"):
                    self._restore_corrective_shape_keys(faceit_objects, names)
        
        # Restore rig action
        if rig:
            self._restore_rig_action(rig)
        
        # Reset properties
        set_shapes_generated(False)
        
        # Load bake modifiers
        self._load_bake_modifiers(faceit_objects)
        
        cmds.warning("Back to rigging completed")
        return {'FINISHED'}
    
    def _get_expression_data(self) -> Dict:
        """Get expression data from scene."""
        if not cmds.objExists("faceit_core_data"):
            return {}
        
        data = {}
        
        if cmds.attributeQuery("expression_names", node="faceit_core_data", exists=True):
            names_str = cmds.getAttr("faceit_core_data.expression_names") or ""
            data['names'] = names_str.split(',') if names_str else []
        
        return data
    
    def _reset_expression_values(self) -> None:
        """Reset expression values to default."""
        faceit_objects = futils.get_faceit_objects_list()
        
        for obj in faceit_objects:
            if not cmds.objExists(obj):
                continue
            
            if shape_key_utils.has_shape_keys(obj):
                blend_node = shape_key_utils.get_blend_shape_node(obj)
                if blend_node:
                    targets = shape_key_utils.get_blend_shape_targets(obj)
                    for target in targets:
                        cmds.setAttr(f"{blend_node}.{target}", 0)
    
    def _remove_control_drivers(self, c_rig: str) -> None:
        """Remove control drivers."""
        if not cmds.objExists(c_rig):
            return
        
        # Get target objects
        if cmds.attributeQuery("faceit_crig_objects", node=c_rig, exists=True):
            objects_str = cmds.getAttr(f"{c_rig}.faceit_crig_objects") or ""
            target_objects = objects_str.split(',') if objects_str else []
            
            for obj in target_objects:
                if not cmds.objExists(obj):
                    continue
                
                if shape_key_utils.has_shape_keys(obj):
                    blend_node = shape_key_utils.get_blend_shape_node(obj)
                    if blend_node:
                        targets = shape_key_utils.get_blend_shape_targets(obj)
                        for target in targets:
                            connections = cmds.listConnections(f"{blend_node}.{target}", source=True, destination=False) or []
                            for conn in connections:
                                if cmds.nodeType(conn) == 'animCurve':
                                    cmds.delete(conn)
    
    def _restore_bake_modifiers(self, objects: List[str]) -> None:
        """Restore bake modifiers."""
        for obj in objects:
            if not cmds.objExists(obj):
                continue
            
            if cmds.attributeQuery("faceit_modifier_data", node=obj, exists=True):
                data_str = cmds.getAttr(f"{obj}.faceit_modifier_data") or "[]"
                try:
                    import json
                    mod_data_list = json.loads(data_str)
                    
                    for mod_data in mod_data_list:
                        mod_name = mod_data.get('name', '')
                        if cmds.objExists(mod_name):
                            if 'bake' in mod_data and mod_data['bake']:
                                if cmds.attributeQuery("envelope", node=mod_name, exists=True):
                                    cmds.setAttr(f"{mod_name}.envelope", 1)
                                if cmds.attributeQuery("visibility", node=mod_name, exists=True):
                                    cmds.setAttr(f"{mod_name}.visibility", 1)
                except:
                    pass
    
    def _clear_animation(self, objects: List[str]) -> None:
        """Clear animation from objects."""
        for obj in objects:
            if not cmds.objExists(obj):
                continue
            
            if shape_key_utils.has_shape_keys(obj):
                blend_node = shape_key_utils.get_blend_shape_node(obj)
                if blend_node:
                    if cmds.attributeQuery("currentAction", node=blend_node, exists=True):
                        cmds.setAttr(f"{blend_node}.currentAction", "", type="string")
    
    def _restore_corrective_shape_keys(self, objects: List[str], names: List[str]) -> None:
        """Restore corrective shape keys."""
        for obj in objects:
            if not cmds.objExists(obj):
                continue
            
            if shape_key_utils.has_shape_keys(obj):
                blend_node = shape_key_utils.get_blend_shape_node(obj)
                if blend_node:
                    for name in names:
                        sk_name = f"faceit_cc_{name}"
                        if cmds.attributeQuery(sk_name, node=blend_node, exists=True):
                            cmds.setAttr(f"{blend_node}.{sk_name}", 1)
    
    def _restore_rig_action(self, rig: str) -> None:
        """Restore rig action."""
        if not rig:
            return
        
        action = None
        if cmds.objExists("overwrite_shape_action"):
            action = "overwrite_shape_action"
        elif cmds.objExists("faceit_shape_action"):
            action = "faceit_shape_action"
        
        if action:
            if not cmds.attributeQuery("currentAction", node=rig, exists=True):
                cmds.addAttr(rig, ln="currentAction", dt="string")
            cmds.setAttr(f"{rig}.currentAction", action, type="string")
    
    def _load_bake_modifiers(self, objects: List[str]) -> None:
        """Load bake modifiers."""
        # In Maya, we'd populate bake modifier items
        pass


# ============================================================
# Scene Property Functions
# ============================================================

def get_shapes_generated() -> bool:
    """Get the shapes_generated property."""
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery("shapes_generated", node="faceit_core_data", exists=True):
            return cmds.getAttr("faceit_core_data.shapes_generated")
    return False


def set_shapes_generated(value: bool) -> None:
    """Set the shapes_generated property."""
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery("shapes_generated", node="faceit_core_data", exists=True):
            cmds.setAttr("faceit_core_data.shapes_generated", value)