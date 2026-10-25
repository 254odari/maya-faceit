# retarget_fbx_operators.py
# Maya Faceit Plugin - Retarget FBX Operators
# Converted from Blender to Maya Python 3.11

"""
FBX retarget operators for Faceit Maya plugin.
Handles retargeting of FBX shape key actions.
"""

import maya.cmds as cmds # type: ignore
import maya.api.OpenMaya as om2 # type: ignore
import json
from typing import List, Dict, Optional, Any

from ..core import faceit_utils as futils
from ..core import fc_dr_utils
from ..core import shape_key_utils as sk_utils
from ..core import detection_manager
from ..ctrl_rig import control_rig_utils as ctrl_utils


# ============================================================
# Helper Functions
# ============================================================

def get_enum_sk_actions() -> List[tuple]:
    """
    Get all shape key actions as enum items.
    
    Returns:
        List of (value, label, description) tuples
    """
    actions = []
    
    for action in cmds.ls(type='animCurve'):
        action_name = cmds.getAttr(f"{action}.name") or action
        
        # Check if it contains shape key data
        curves = cmds.listAnimCurves(action) or []
        for curve in curves:
            attr = cmds.getAttr(f"{curve}.attributeName") or ""
            if 'key_block' in attr or 'weight' in attr:
                actions.append((action_name, action_name, action_name))
                break
    
    if not actions:
        actions.append(("-", "-", "-"))
    
    return actions


def update_action_name(self, context: Any) -> None:
    """Update action name with suffix."""
    if hasattr(self, 'retarget_action') and hasattr(self, 'suffix'):
        self.new_name = self.retarget_action + self.suffix


# ============================================================
# Retarget FBX Action Operator
# ============================================================

class RetargetFBXAction:
    """
    Retarget the Source Action to the populated target Shapes.
    """
    
    name = "RetargetFBXAction"
    label = "Initialize Retargeting"
    
    def __init__(self):
        self.retarget_action = ""
        self.suffix = "_retargeted"
        self.new_name = ""
        self.populate_faceit = True
        self.keep_undetected_shapes = False
        self.bake_to_control_rig = False
        self.show_advanced_settings = False
        self.can_bake_to_control_rig = False
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        # Check if retarget mapping exists
        if cmds.objExists("faceit_core_data"):
            if cmds.attributeQuery("fbx_retarget_mapping", node="faceit_core_data", exists=True):
                data_str = cmds.getAttr("faceit_core_data.fbx_retarget_mapping") or "[]"
                try:
                    data = json.loads(data_str)
                    return bool(data)
                except:
                    pass
        return False
    
    def invoke(self, context: Any) -> str:
        """Invoke the operator."""
        # Get retarget properties
        retarget_props = self._get_retarget_props()
        
        source_action = None
        
        if retarget_props.get('mapping_source') == 'OBJECT':
            source_obj = retarget_props.get('source_obj', '')
            if source_obj and cmds.objExists(source_obj):
                if sk_utils.has_shape_keys(source_obj):
                    # Get current action on the object
                    if cmds.attributeQuery("currentAction", node=source_obj, exists=True):
                        action_name = cmds.getAttr(f"{source_obj}.currentAction") or ""
                        if action_name and cmds.objExists(action_name):
                            source_action = action_name
        
        else:
            source_action = retarget_props.get('source_action', '')
            if source_action and not cmds.objExists(source_action):
                source_action = None
        
        if not source_action:
            cmds.warning("No source action found with shape key data.")
            return {'CANCELLED'}
        
        self.new_name = source_action + "_retargeted"
        self.retarget_action = source_action
        
        # Check if can bake to control rig
        if retarget_props.get('mapping_target') == 'CRIG':
            self.can_bake_to_control_rig = bool(futils.get_faceit_control_armature())
            if self.can_bake_to_control_rig:
                self.bake_to_control_rig = True
        
        # In Maya, we'd show a dialog
        return self.execute(context)
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        retarget_props = self._get_retarget_props()
        retarget_list = retarget_props.get('mapping_list', [])
        
        source_action = cmds.objExists(self.retarget_action)
        if not source_action:
            cmds.warning("No source Action found. Choose a valid Shape Keys Action!")
            return {'CANCELLED'}
        
        # Handle control rig baking
        if self.bake_to_control_rig:
            c_rig = futils.get_faceit_control_armature()
            if not c_rig:
                cmds.warning("Can't find the active control rig. Please create/choose control rig first.")
                return {'CANCELLED'}
            
            # Remove existing temp action
            if cmds.objExists("mocap_import"):
                cmds.delete("mocap_import")
            
            # Copy source action
            target_action = cmds.duplicate(source_action, name="mocap_import")[0]
        else:
            # Remove existing action
            if cmds.objExists(self.new_name):
                cmds.delete(self.new_name)
            
            # Copy source action
            target_action = cmds.duplicate(source_action, name=self.new_name)[0]
        
        # Get all data paths from source action
        all_fcurve_data_paths = []
        curves = cmds.listAnimCurves(source_action) or []
        for curve in curves:
            attr = cmds.getAttr(f"{curve}.attributeName") or ""
            if attr:
                all_fcurve_data_paths.append(attr)
        
        retargeted_any = False
        
        for item in retarget_list:
            if not item.get('use_animation', True):
                continue
            
            target_shapes = item.get('target_shapes', [])
            target_shapes_list = [t.get('name', '') for t in target_shapes]
            source_shape = item.get('name', '')
            
            data_paths = [
                f'key_blocks["{source_shape}"].value',
                f'key_blocks["{source_shape}"].slider_min',
                f'key_blocks["{source_shape}"].slider_max'
            ]
            
            for dp in data_paths:
                # Find the fcurve
                curve = self._find_fcurve(source_action, dp)
                if not curve:
                    continue
                
                source_is_target_shape = False
                for target_shape in target_shapes_list:
                    # Copy fcurve data
                    fc_data = self._copy_fcurve_data(curve)
                    new_dp = dp.replace(source_shape, target_shape)
                    
                    if dp != new_dp:
                        source_is_target_shape = True
                    
                    # Create new fcurve
                    self._create_fcurve(target_action, new_dp, fc_data)
                    retargeted_any = True
                
                if source_is_target_shape and dp in all_fcurve_data_paths:
                    all_fcurve_data_paths.remove(dp)
                    # Remove source fcurve
                    if curve and cmds.objExists(curve):
                        cmds.delete(curve)
        
        # Handle undetected fcurves
        if all_fcurve_data_paths:
            for dp in all_fcurve_data_paths:
                cmds.warning(f"Did not retarget fcurve with data_path {dp}")
                if not self.keep_undetected_shapes:
                    curve = self._find_fcurve(target_action, dp)
                    if curve and cmds.objExists(curve):
                        cmds.delete(curve)
        
        # Check if retargeting was successful
        curves = cmds.listAnimCurves(target_action) or []
        if not curves or not retargeted_any:
            cmds.warning("The animation data could not be retargeted.")
            cmds.delete(target_action)
            return {'CANCELLED'}
        
        # Get target objects
        mapping_target = retarget_props.get('mapping_target', 'FACEIT')
        target_objects = self._get_target_objects(mapping_target, retarget_props)
        
        if self.bake_to_control_rig:
            # Bake to control rig
            self._bake_to_control_rig(target_action)
        else:
            # Apply to target objects
            for obj in target_objects:
                if not cmds.objExists(obj):
                    continue
                
                if sk_utils.has_shape_keys(obj):
                    blend_node = sk_utils.get_blend_shape_node(obj)
                    if blend_node:
                        if not cmds.attributeQuery("currentAction", node=blend_node, exists=True):
                            cmds.addAttr(blend_node, ln="currentAction", dt="string")
                        cmds.setAttr(f"{blend_node}.currentAction", target_action, type="string")
        
        cmds.warning("Successfully retargeted the animation data.")
        return {'FINISHED'}
    
    def _get_retarget_props(self) -> Dict:
        """Get retarget properties from scene."""
        if not cmds.objExists("faceit_core_data"):
            return {}
        
        if cmds.attributeQuery("fbx_retarget_mapping", node="faceit_core_data", exists=True):
            data_str = cmds.getAttr("faceit_core_data.fbx_retarget_mapping") or "{}"
            try:
                return json.loads(data_str)
            except:
                pass
        
        return {}
    
    def _find_fcurve(self, action: str, data_path: str) -> Optional[str]:
        """Find an fcurve by data path."""
        if not action or not cmds.objExists(action):
            return None
        
        curves = cmds.listAnimCurves(action) or []
        for curve in curves:
            attr = cmds.getAttr(f"{curve}.attributeName") or ""
            if attr == data_path:
                return curve
        
        return None
    
    def _copy_fcurve_data(self, curve: str) -> Dict:
        """Copy fcurve data to dictionary."""
        if not curve or not cmds.objExists(curve):
            return {}
        
        data = {
            'keyframes': [],
            'values': []
        }
        
        keyframes = cmds.keyframe(curve, query=True, timeChange=True) or []
        values = cmds.keyframe(curve, query=True, valueChange=True) or []
        
        data['keyframes'] = keyframes
        data['values'] = values
        
        return data
    
    def _create_fcurve(self, action: str, data_path: str, data: Dict) -> Optional[str]:
        """Create an fcurve with data."""
        if not action or not cmds.objExists(action):
            return None
        
        # Create new curve
        curve = cmds.createNode("animCurveUA", name=f"{action}_{data_path.replace('.', '_')}")
        cmds.connectAttr(f"{curve}.output", f"{action}.{data_path}")
        
        # Set keyframes
        keyframes = data.get('keyframes', [])
        values = data.get('values', [])
        
        for frame, value in zip(keyframes, values):
            cmds.setKeyframe(curve, t=frame, v=value)
        
        return curve
    
    def _get_target_objects(self, mapping_target: str, retarget_props: Dict) -> List[str]:
        """Get target objects based on mapping target."""
        target_objects = []
        
        if mapping_target == 'FACEIT':
            target_objects = futils.get_faceit_objects_list()
        elif mapping_target == 'CRIG':
            c_rig = futils.get_faceit_control_armature()
            if c_rig:
                target_objects = ctrl_utils.get_crig_objects_list(c_rig)
        elif mapping_target == 'TARGET':
            target_obj = retarget_props.get('target_obj', '')
            if target_obj and cmds.objExists(target_obj):
                target_objects = [target_obj]
        
        return target_objects
    
    def _bake_to_control_rig(self, target_action: str) -> None:
        """Bake retargeted action to control rig."""
        # In Maya, we'd use the bake_shape_keys_to_control_rig functionality
        c_rig = futils.get_faceit_control_armature()
        if c_rig:
            # Set the action as current
            if not cmds.attributeQuery("currentAction", node=c_rig, exists=True):
                cmds.addAttr(c_rig, ln="currentAction", dt="string")
            cmds.setAttr(f"{c_rig}.currentAction", target_action, type="string")


# ============================================================
# Retarget List FBX Operators
# ============================================================

class FBXRetargetBase:
    """Base class for FBX retarget operators."""
    
    @classmethod
    def poll(cls) -> bool:
        """Check if the operator can run."""
        return True
    
    @staticmethod
    def get_retarget_shapes() -> List[Dict]:
        """Get the retarget list property group."""
        if cmds.objExists("faceit_core_data"):
            if cmds.attributeQuery("fbx_retarget_mapping", node="faceit_core_data", exists=True):
                data_str = cmds.getAttr("faceit_core_data.fbx_retarget_mapping") or "[]"
                try:
                    return json.loads(data_str)
                except:
                    pass
        return []


class EditFBXTargetShape:
    """Edit FBX target shape operator."""
    
    name = "EditFBXTargetShape"
    label = "Edit FBX Target Shape"
    
    def __init__(self):
        self.operation = 'ADD'
        self.new_target_shape = ""
        self.source_shape_index = 0
        self.target_shape = ""
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return True
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        retarget_list = self._get_retarget_shapes()
        
        if self.source_shape_index >= len(retarget_list):
            return {'CANCELLED'}
        
        shape_item = retarget_list[self.source_shape_index]
        
        if self.operation == 'CHANGE':
            # Change existing target shape
            targets = shape_item.get('target_shapes', [])
            for i, ts in enumerate(targets):
                if ts.get('name') == self.target_shape:
                    targets[i]['name'] = self.new_target_shape
                    break
        else:
            # Add new target shape
            if 'target_shapes' not in shape_item:
                shape_item['target_shapes'] = []
            
            # Check if already exists
            existing = [t.get('name', '') for t in shape_item['target_shapes']]
            if self.new_target_shape not in existing:
                shape_item['target_shapes'].append({'name': self.new_target_shape})
        
        self._save_retarget_shapes(retarget_list)
        
        return {'FINISHED'}
    
    def _get_retarget_shapes(self) -> List[Dict]:
        """Get retarget shapes."""
        if cmds.objExists("faceit_core_data"):
            if cmds.attributeQuery("fbx_retarget_mapping", node="faceit_core_data", exists=True):
                data_str = cmds.getAttr("faceit_core_data.fbx_retarget_mapping") or "[]"
                try:
                    return json.loads(data_str)
                except:
                    pass
        return []
    
    def _save_retarget_shapes(self, shapes: List[Dict]) -> None:
        """Save retarget shapes."""
        if cmds.objExists("faceit_core_data"):
            if cmds.attributeQuery("fbx_retarget_mapping", node="faceit_core_data", exists=True):
                cmds.setAttr("faceit_core_data.fbx_retarget_mapping", json.dumps(shapes), type="string")


class RemoveFBXTargetShape:
    """Remove FBX target shape operator."""
    
    name = "RemoveFBXTargetShape"
    label = "Remove FBX Target Shape"
    
    def __init__(self):
        self.source_shape_index = 0
        self.target_shape = ""
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return True
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        retarget_list = self._get_retarget_shapes()
        
        if self.source_shape_index >= len(retarget_list):
            return {'CANCELLED'}
        
        shape_item = retarget_list[self.source_shape_index]
        targets = shape_item.get('target_shapes', [])
        
        for i, ts in enumerate(targets):
            if ts.get('name') == self.target_shape:
                targets.pop(i)
                break
        
        self._save_retarget_shapes(retarget_list)
        
        return {'FINISHED'}
    
    def _get_retarget_shapes(self) -> List[Dict]:
        """Get retarget shapes."""
        if cmds.objExists("faceit_core_data"):
            if cmds.attributeQuery("fbx_retarget_mapping", node="faceit_core_data", exists=True):
                data_str = cmds.getAttr("faceit_core_data.fbx_retarget_mapping") or "[]"
                try:
                    return json.loads(data_str)
                except:
                    pass
        return []
    
    def _save_retarget_shapes(self, shapes: List[Dict]) -> None:
        """Save retarget shapes."""
        if cmds.objExists("faceit_core_data"):
            if cmds.attributeQuery("fbx_retarget_mapping", node="faceit_core_data", exists=True):
                cmds.setAttr("faceit_core_data.fbx_retarget_mapping", json.dumps(shapes), type="string")


class ClearFBXTargetShapes:
    """Clear FBX target shapes operator."""
    
    name = "ClearFBXTargetShapes"
    label = "Clear FBX Target Shapes"
    
    def __init__(self):
        self.source_shape_name = ""
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return True
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        retarget_list = self._get_retarget_shapes()
        
        for item in retarget_list:
            if item.get('name') == self.source_shape_name:
                item['target_shapes'] = []
                break
        
        self._save_retarget_shapes(retarget_list)
        
        return {'FINISHED'}
    
    def _get_retarget_shapes(self) -> List[Dict]:
        """Get retarget shapes."""
        if cmds.objExists("faceit_core_data"):
            if cmds.attributeQuery("fbx_retarget_mapping", node="faceit_core_data", exists=True):
                data_str = cmds.getAttr("faceit_core_data.fbx_retarget_mapping") or "[]"
                try:
                    return json.loads(data_str)
                except:
                    pass
        return []
    
    def _save_retarget_shapes(self, shapes: List[Dict]) -> None:
        """Save retarget shapes."""
        if cmds.objExists("faceit_core_data"):
            if cmds.attributeQuery("fbx_retarget_mapping", node="faceit_core_data", exists=True):
                cmds.setAttr("faceit_core_data.fbx_retarget_mapping", json.dumps(shapes), type="string")


class InitFBXRetargeting:
    """
    Initialize the retargeting list and try to match shapes automatically.
    """
    
    name = "InitFBXRetargeting"
    label = "Initialize Retargeting"
    
    def __init__(self):
        self.levenshtein_ratio = 1.0
        self.empty = False
        self.remove_prefix_source = ""
        self.remove_suffix_source = ""
        self.remove_prefix_target = ""
        self.remove_suffix_target = ""
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        # Check if retarget mapping has source and target
        if cmds.objExists("faceit_core_data"):
            if cmds.attributeQuery("fbx_retarget_mapping", node="faceit_core_data", exists=True):
                data_str = cmds.getAttr("faceit_core_data.fbx_retarget_mapping") or "{}"
                try:
                    data = json.loads(data_str)
                    if data.get('mapping_source') == 'OBJECT':
                        return bool(data.get('source_obj', ''))
                    else:
                        return bool(data.get('source_action', ''))
                except:
                    pass
        return False
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        retarget_props = self._get_retarget_props()
        retarget_list = retarget_props.get('mapping_list', [])
        
        if self.empty:
            # Clear list
            retarget_list = []
            self._save_retarget_props(retarget_props)
            return {'FINISHED'}
        
        # Get source shape names
        mapping_source = retarget_props.get('mapping_source', 'OBJECT')
        shape_key_names_source = self._get_source_shape_names(mapping_source, retarget_props)
        
        if not shape_key_names_source:
            cmds.warning("No Shape Keys found in Source.")
            return {'CANCELLED'}
        
        # Get target shape names
        mapping_target = retarget_props.get('mapping_target', 'FACEIT')
        shape_key_names_target = self._get_target_shape_names(mapping_target, retarget_props)
        
        if not shape_key_names_target:
            cmds.warning("The registered objects have no shape keys.")
            return {'CANCELLED'}
        
        # Create matching
        match_names = {}
        new_names = []
        
        if self.remove_prefix_target or self.remove_suffix_target:
            for name in shape_key_names_target:
                name_match = name
                if self.remove_prefix_target and name.startswith(self.remove_prefix_target):
                    name_match = name[len(self.remove_prefix_target):]
                if self.remove_suffix_target and name.endswith(self.remove_suffix_target):
                    name_match = name[:-len(self.remove_suffix_target)]
                new_names.append(name_match)
                match_names[name_match] = name
        
        retarget_list = []
        missing_shapes = []
        
        for source_shape in shape_key_names_source:
            item = {
                'name': source_shape,
                'target_shapes': [],
                'amplify': 1.0,
                'use_animation': True,
                'region': 'other'
            }
            
            if not self.empty:
                source_match = source_shape
                
                if self.remove_prefix_source and source_match.startswith(self.remove_prefix_source):
                    source_match = source_match[len(self.remove_prefix_source):]
                if self.remove_suffix_source and source_match.endswith(self.remove_suffix_source):
                    source_match = source_match[:-len(self.remove_suffix_source)]
                
                if new_names:
                    found_shape = detection_manager.detect_shape(
                        new_names,
                        source_match,
                        min_levenshtein_ratio=self.levenshtein_ratio,
                        remove_suffix=self.remove_suffix_target
                    )
                    found_shape = match_names.get(found_shape)
                else:
                    found_shape = detection_manager.detect_shape(
                        shape_key_names_target,
                        source_match,
                        min_levenshtein_ratio=self.levenshtein_ratio,
                        remove_prefix=self.remove_prefix_target,
                        remove_suffix=self.remove_suffix_target
                    )
                
                if found_shape:
                    item['target_shapes'].append({'name': found_shape})
                    shape_key_names_target.remove(found_shape)
                else:
                    missing_shapes.append(source_shape)
            
            retarget_list.append(item)
        
        if missing_shapes:
            cmds.warning("Couldn't find all target shapes. Are the shape keys missing?")
        
        # Save retarget list
        retarget_props['mapping_list'] = retarget_list
        self._save_retarget_props(retarget_props)
        
        cmds.warning("Retargeting initialized successfully.")
        return {'FINISHED'}
    
    def _get_retarget_props(self) -> Dict:
        """Get retarget properties."""
        if cmds.objExists("faceit_core_data"):
            if cmds.attributeQuery("fbx_retarget_mapping", node="faceit_core_data", exists=True):
                data_str = cmds.getAttr("faceit_core_data.fbx_retarget_mapping") or "{}"
                try:
                    return json.loads(data_str)
                except:
                    pass
        return {}
    
    def _save_retarget_props(self, props: Dict) -> None:
        """Save retarget properties."""
        if cmds.objExists("faceit_core_data"):
            if cmds.attributeQuery("fbx_retarget_mapping", node="faceit_core_data", exists=True):
                cmds.setAttr("faceit_core_data.fbx_retarget_mapping", json.dumps(props), type="string")
    
    def _get_source_shape_names(self, mapping_source: str, retarget_props: Dict) -> List[str]:
        """Get source shape names."""
        if mapping_source == 'OBJECT':
            source_obj = retarget_props.get('source_obj', '')
            if source_obj and cmds.objExists(source_obj):
                if sk_utils.has_shape_keys(source_obj):
                    return sk_utils.get_blend_shape_targets(source_obj)
        else:
            source_action = retarget_props.get('source_action', '')
            if source_action and cmds.objExists(source_action):
                return sk_utils.get_shape_key_names_from_action(source_action)
        
        return []
    
    def _get_target_shape_names(self, mapping_target: str, retarget_props: Dict) -> List[str]:
        """Get target shape names."""
        target_objects = []
        
        if mapping_target == 'TARGET':
            target_obj = retarget_props.get('target_obj', '')
            if target_obj and cmds.objExists(target_obj):
                target_objects = [target_obj]
        elif mapping_target == 'FACEIT':
            target_objects = futils.get_faceit_objects_list()
        elif mapping_target == 'CRIG':
            c_rig = futils.get_faceit_control_armature()
            if c_rig:
                target_objects = ctrl_utils.get_crig_objects_list(c_rig)
        
        return sk_utils.get_shape_key_names_from_objects(target_objects)