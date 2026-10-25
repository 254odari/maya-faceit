# retarget_list_fbx_operators.py
# Maya Faceit Plugin - Retarget List FBX Operators
# Converted from Blender to Maya Python 3.11

"""
Retarget list FBX operators for Faceit Maya plugin.
Handles FBX retargeting list management and initialization.
"""

import maya.cmds as cmds # type: ignore
import json
from typing import List, Dict, Optional, Any

from ..core import shape_key_utils as sk_utils
from ..core import detection_manager
from ..core import faceit_utils as futils
from ..core.retarget_list_base import RetargetingBase
from ..ctrl_rig import control_rig_utils as ctrl_utils


# ============================================================
# FBX Retarget Base Class
# ============================================================

class FBXRetargetBase:
    """
    Base class for FBX retarget operators.
    """
    
    @classmethod
    def poll(cls) -> bool:
        """
        Check if the operator can run.
        """
        return True
    
    @staticmethod
    def get_retarget_shapes() -> List[Dict]:
        """
        Get the retarget list property group.
        """
        if cmds.objExists("faceit_core_data"):
            if cmds.attributeQuery("fbx_retarget_mapping", node="faceit_core_data", exists=True):
                data_str = cmds.getAttr("faceit_core_data.fbx_retarget_mapping") or "[]"
                try:
                    return json.loads(data_str)
                except:
                    pass
        return []
    
    @staticmethod
    def save_retarget_shapes(shapes: List[Dict]) -> bool:
        """
        Save retarget shapes.
        """
        if cmds.objExists("faceit_core_data"):
            if cmds.attributeQuery("fbx_retarget_mapping", node="faceit_core_data", exists=True):
                cmds.setAttr("faceit_core_data.fbx_retarget_mapping", json.dumps(shapes), type="string")
                return True
        return False


# ============================================================
# Edit FBX Target Shape Operator
# ============================================================

class EditFBXTargetShape(FBXRetargetBase):
    """
    Edit FBX target shape operator.
    """
    
    name = "EditFBXTargetShape"
    label = "Edit FBX Target Shape"
    
    def __init__(self):
        self.operation = 'ADD'  # 'ADD' or 'CHANGE'
        self.new_target_shape = ""
        self.source_shape_index = 0
        self.target_shape = ""
        self.bl_property = 'new_target_shape'
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return True
    
    def invoke(self, context: Any) -> str:
        """Invoke the operator."""
        # In Maya, we'd show a search popup
        return self.execute(context)
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        retarget_list = self.get_retarget_shapes()
        
        if self.source_shape_index >= len(retarget_list):
            cmds.warning("Source shape index out of range")
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
            if self.new_target_shape and self.new_target_shape not in existing:
                shape_item['target_shapes'].append({'name': self.new_target_shape})
            elif not self.new_target_shape:
                cmds.warning("No target shape specified")
                return {'CANCELLED'}
            else:
                cmds.warning(f"Target shape '{self.new_target_shape}' already exists")
                return {'CANCELLED'}
        
        self.save_retarget_shapes(retarget_list)
        
        cmds.warning(f"Successfully {'changed' if self.operation == 'CHANGE' else 'added'} target shape")
        return {'FINISHED'}


# ============================================================
# Remove FBX Target Shape Operator
# ============================================================

class RemoveFBXTargetShape(FBXRetargetBase):
    """
    Remove FBX target shape operator.
    """
    
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
        retarget_list = self.get_retarget_shapes()
        
        if self.source_shape_index >= len(retarget_list):
            cmds.warning("Source shape index out of range")
            return {'CANCELLED'}
        
        shape_item = retarget_list[self.source_shape_index]
        targets = shape_item.get('target_shapes', [])
        
        for i, ts in enumerate(targets):
            if ts.get('name') == self.target_shape:
                targets.pop(i)
                break
        else:
            cmds.warning(f"Target shape '{self.target_shape}' not found")
            return {'CANCELLED'}
        
        self.save_retarget_shapes(retarget_list)
        
        cmds.warning(f"Successfully removed target shape '{self.target_shape}'")
        return {'FINISHED'}


# ============================================================
# Clear FBX Target Shapes Operator
# ============================================================

class ClearFBXTargetShapes(FBXRetargetBase):
    """
    Clear FBX target shapes operator.
    """
    
    name = "ClearFBXTargetShapes"
    label = "Clear FBX Target Shapes"
    
    def __init__(self):
        self.source_shape_name = ""
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return True
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        retarget_list = self.get_retarget_shapes()
        
        for item in retarget_list:
            if item.get('name') == self.source_shape_name:
                item['target_shapes'] = []
                break
        else:
            cmds.warning(f"Source shape '{self.source_shape_name}' not found")
            return {'CANCELLED'}
        
        self.save_retarget_shapes(retarget_list)
        
        cmds.warning(f"Successfully cleared target shapes for '{self.source_shape_name}'")
        return {'FINISHED'}


# ============================================================
# Get Target Shapes Enum
# ============================================================

def get_target_shapes_enum() -> List[tuple]:
    """
    Get target shapes as enum items.
    
    Returns:
        List of (value, label, description) tuples
    """
    shapes = []
    
    # Get retarget shapes
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery("fbx_retarget_mapping", node="faceit_core_data", exists=True):
            data_str = cmds.getAttr("faceit_core_data.fbx_retarget_mapping") or "[]"
            try:
                data = json.loads(data_str)
                # Get source shapes
                for item in data.get('mapping_list', []):
                    shape_name = item.get('name', '')
                    if shape_name:
                        shapes.append((shape_name, shape_name, shape_name))
            except:
                pass
    
    if not shapes:
        shapes.append(("None", "None", "None"))
    
    return shapes


# ============================================================
# Initialize FBX Retargeting Operator
# ============================================================

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
        """
        Check if the operator can run.
        """
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
    
    def invoke(self, context: Any) -> str:
        """Invoke the operator."""
        if not self.empty:
            # In Maya, we'd show a dialog
            return self.execute(context)
        else:
            return self.execute(context)
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        retarget_props = self._get_retarget_props()
        retarget_list = retarget_props.get('mapping_list', [])
        
        if self.empty:
            # Clear list
            retarget_props['mapping_list'] = []
            self._save_retarget_props(retarget_props)
            cmds.warning("Retargeting list cleared")
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
        
        new_retarget_list = []
        missing_shapes = []
        
        for source_shape in shape_key_names_source:
            item = {
                'name': source_shape,
                'target_shapes': [],
                'amplify': 1.0,
                'use_animation': True,
                'region': 'other'
            }
            
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
                if found_shape in shape_key_names_target:
                    shape_key_names_target.remove(found_shape)
            else:
                missing_shapes.append(source_shape)
            
            new_retarget_list.append(item)
        
        if missing_shapes:
            cmds.warning(f"Couldn't find all target shapes. Missing: {', '.join(missing_shapes)}")
        
        # Save retarget list
        retarget_props['mapping_list'] = new_retarget_list
        self._save_retarget_props(retarget_props)
        
        cmds.warning(f"Retargeting initialized successfully. Found {len(new_retarget_list)} mappings.")
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
                cmds.warning(f"Source object '{source_obj}' not found or has no shape keys.")
        else:
            source_action = retarget_props.get('source_action', '')
            if source_action and cmds.objExists(source_action):
                return sk_utils.get_shape_key_names_from_action(source_action)
            else:
                cmds.warning(f"Source action '{source_action}' not found.")
        
        return []
    
    def _get_target_shape_names(self, mapping_target: str, retarget_props: Dict) -> List[str]:
        """Get target shape names."""
        target_objects = []
        
        if mapping_target == 'TARGET':
            target_obj = retarget_props.get('target_obj', '')
            if target_obj and cmds.objExists(target_obj):
                target_objects = [target_obj]
            else:
                cmds.warning(f"Target object '{target_obj}' not found.")
                return []
        elif mapping_target == 'FACEIT':
            target_objects = futils.get_faceit_objects_list()
            if not target_objects:
                cmds.warning("No Faceit objects found. Please register objects in Setup panel.")
                return []
        elif mapping_target == 'CRIG':
            c_rig = futils.get_faceit_control_armature()
            if c_rig:
                target_objects = ctrl_utils.get_crig_objects_list(c_rig)
            if not target_objects:
                cmds.warning("No control rig objects found. Please update the control rig.")
                return []
        
        # Get shape key names from target objects
        shape_names = sk_utils.get_shape_key_names_from_objects(target_objects)
        
        if not shape_names:
            cmds.warning("The target objects have no shape keys.")
        
        return shape_names


# ============================================================
# Clear FBX Retargeting Operator
# ============================================================

class ClearFBXRetargeting:
    """
    Clear all FBX retargeting data.
    """
    
    name = "ClearFBXRetargeting"
    label = "Clear FBX Retargeting"
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return True
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        if cmds.objExists("faceit_core_data"):
            if cmds.attributeQuery("fbx_retarget_mapping", node="faceit_core_data", exists=True):
                # Clear all retarget data
                cmds.setAttr("faceit_core_data.fbx_retarget_mapping", "[]", type="string")
                cmds.warning("FBX retargeting data cleared")
                return {'FINISHED'}
        
        cmds.warning("No FBX retargeting data found to clear.")
        return {'FINISHED'}


# ============================================================
# Import FBX Retarget Preset Operator
# ============================================================

class ImportFBXRetargetPreset:
    """
    Import a retarget preset from a JSON file.
    """
    
    name = "ImportFBXRetargetPreset"
    label = "Import Retarget Preset"
    
    def __init__(self):
        self.filepath = ""
        self.preset_name = ""
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return True
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        if not self.filepath:
            cmds.warning("No file path specified.")
            return {'CANCELLED'}
        
        import os
        if not os.path.exists(self.filepath):
            cmds.warning(f"File not found: {self.filepath}")
            return {'CANCELLED'}
        
        try:
            with open(self.filepath, 'r') as f:
                preset_data = json.load(f)
        except Exception as e:
            cmds.warning(f"Error loading preset: {str(e)}")
            return {'CANCELLED'}
        
        # Convert preset to retarget list
        retarget_list = []
        
        for source_shape, data in preset_data.items():
            item = {
                'name': source_shape,
                'target_shapes': [{'name': t} for t in data.get('target_shapes', [])],
                'amplify': data.get('amplify', 1.0),
                'use_animation': True,
                'region': data.get('region', 'other')
            }
            retarget_list.append(item)
        
        # Save to scene
        retarget_props = self._get_retarget_props()
        retarget_props['mapping_list'] = retarget_list
        self._save_retarget_props(retarget_props)
        
        cmds.warning(f"Successfully imported preset '{self.preset_name or os.path.basename(self.filepath)}'")
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


# ============================================================
# Export FBX Retarget Preset Operator
# ============================================================

class ExportFBXRetargetPreset:
    """
    Export a retarget preset to a JSON file.
    """
    
    name = "ExportFBXRetargetPreset"
    label = "Export Retarget Preset"
    
    def __init__(self):
        self.filepath = ""
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        retarget_props = self._get_retarget_props()
        return bool(retarget_props.get('mapping_list', []))
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        if not self.filepath:
            cmds.warning("No file path specified.")
            return {'CANCELLED'}
        
        retarget_props = self._get_retarget_props()
        retarget_list = retarget_props.get('mapping_list', [])
        
        if not retarget_list:
            cmds.warning("No retarget data to export.")
            return {'CANCELLED'}
        
        # Convert to preset format
        preset_data = {}
        
        for item in retarget_list:
            preset_data[item.get('name', '')] = {
                'target_shapes': [t.get('name', '') for t in item.get('target_shapes', [])],
                'amplify': item.get('amplify', 1.0),
                'region': item.get('region', 'other')
            }
        
        try:
            import os
            with open(self.filepath, 'w') as f:
                json.dump(preset_data, f, indent=2)
            cmds.warning(f"Successfully exported preset to: {self.filepath}")
        except Exception as e:
            cmds.warning(f"Error exporting preset: {str(e)}")
            return {'CANCELLED'}
        
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