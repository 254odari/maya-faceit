# retarget_list_operators.py
# Maya Faceit Plugin - Retarget List Operators
# Converted from Blender to Maya Python 3.11

"""
Retarget list operators for Faceit Maya plugin.
Handles retargeting list management, initialization, and import/export.
"""

import maya.cmds as cmds # type: ignore
import json
import os
from typing import List, Dict, Optional, Any

from ..core import faceit_data as fdata
from ..core import faceit_utils as futils
from ..core import shape_key_utils as sk_utils
from ..core import detection_manager
from ..core.retarget_list_base import (
    EditTargetShapeBase,
    RemoveTargetShapeBase,
    ClearTargetShapeBase,
    ResetRegionsOperatorBase,
    SetDefaultRegionsBase,
    RetargetingBase
)
from ..core.retarget_list_utils import (
    get_all_set_target_shapes,
    get_target_shapes_dict,
    set_base_regions_from_dict
)


# ============================================================
# Helper Functions
# ============================================================

def get_active_retarget_list() -> List[Dict]:
    """
    Return the active/displayed retarget list collection property.
    """
    if cmds.objExists("faceit_core_data"):
        # Check display retarget list setting
        if cmds.attributeQuery("display_retarget_list", node="faceit_core_data", exists=True):
            display = cmds.getAttr("faceit_core_data.display_retarget_list")
            if display == 0:  # ARKIT
                if cmds.attributeQuery("arkit_retarget_shapes", node="faceit_core_data", exists=True):
                    data_str = cmds.getAttr("faceit_core_data.arkit_retarget_shapes") or "[]"
                    try:
                        return json.loads(data_str)
                    except:
                        pass
            else:  # A2F
                if cmds.attributeQuery("a2f_retarget_shapes", node="faceit_core_data", exists=True):
                    data_str = cmds.getAttr("faceit_core_data.a2f_retarget_shapes") or "[]"
                    try:
                        return json.loads(data_str)
                    except:
                        pass
    return []


def save_active_retarget_list(shapes: List[Dict]) -> None:
    """
    Save the active retarget list.
    """
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery("display_retarget_list", node="faceit_core_data", exists=True):
            display = cmds.getAttr("faceit_core_data.display_retarget_list")
            if display == 0:  # ARKIT
                if cmds.attributeQuery("arkit_retarget_shapes", node="faceit_core_data", exists=True):
                    cmds.setAttr("faceit_core_data.arkit_retarget_shapes", json.dumps(shapes), type="string")
            else:  # A2F
                if cmds.attributeQuery("a2f_retarget_shapes", node="faceit_core_data", exists=True):
                    cmds.setAttr("faceit_core_data.a2f_retarget_shapes", json.dumps(shapes), type="string")


# ============================================================
# Retarget List Base Class
# ============================================================

class RetargetListBase(RetargetingBase):
    """Base class for retarget list operators."""
    
    @classmethod
    def poll(cls) -> bool:
        """Check if the operator can run."""
        return True
    
    @staticmethod
    def get_retarget_shapes() -> List[Dict]:
        """Get the retarget list property group."""
        return get_active_retarget_list()


# ============================================================
# Reset Regions Operator
# ============================================================

class ResetRegions(ResetRegionsOperatorBase):
    """Reset regions operator."""
    
    name = "ResetRegions"
    label = "Reset Regions"
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return True
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        retarget_list = get_active_retarget_list()
        
        for item in retarget_list:
            item['region'] = 'other'
        
        save_active_retarget_list(retarget_list)
        cmds.warning("Regions reset successfully.")
        return {'FINISHED'}


# ============================================================
# Edit Target Shape Operator
# ============================================================

class EditTargetShape(EditTargetShapeBase, RetargetListBase):
    """Edit target shape operator."""
    
    name = "EditTargetShape"
    label = "Edit Target Shape"
    
    def __init__(self):
        self.operation = 'ADD'
        self.new_target_shape = ""
        self.source_shape_index = 0
        self.target_shape = ""
        self.bl_property = 'new_target_shape'
    
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
        
        save_active_retarget_list(retarget_list)
        
        cmds.warning(f"Successfully {'changed' if self.operation == 'CHANGE' else 'added'} target shape")
        return {'FINISHED'}


# ============================================================
# Remove Target Shape Operator
# ============================================================

class RemoveTargetShape(RemoveTargetShapeBase, RetargetListBase):
    """Remove target shape operator."""
    
    name = "RemoveTargetShape"
    label = "Remove Target Shape"
    
    def __init__(self):
        self.source_shape_index = 0
        self.target_shape = ""
    
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
        
        save_active_retarget_list(retarget_list)
        
        cmds.warning(f"Successfully removed target shape '{self.target_shape}'")
        return {'FINISHED'}


# ============================================================
# Clear Target Shapes Operator
# ============================================================

class ClearTargetShapes(ClearTargetShapeBase, RetargetListBase):
    """Clear target shapes operator."""
    
    name = "ClearTargetShapes"
    label = "Clear Target Shapes"
    
    def __init__(self):
        self.source_shape_name = ""
    
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
        
        save_active_retarget_list(retarget_list)
        
        cmds.warning(f"Successfully cleared target shapes for '{self.source_shape_name}'")
        return {'FINISHED'}


# ============================================================
# Set Default Regions Operator
# ============================================================

class SetDefaultRegions(SetDefaultRegionsBase):
    """Set default regions operator."""
    
    name = "SetDefaultRegions"
    label = "Set Default Regions"
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return True
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        retarget_list = get_active_retarget_list()
        
        # Get region mapping from faceit_data
        region_dict = fdata.get_regions_dict()
        
        for item in retarget_list:
            shape_name = item.get('name', '')
            item['region'] = region_dict.get(shape_name, 'other')
        
        save_active_retarget_list(retarget_list)
        
        cmds.warning("Default regions set successfully.")
        return {'FINISHED'}


# ============================================================
# Init Retargeting Operator
# ============================================================

class InitRetargeting:
    """
    Initialize the retargeting list and try to match shapes automatically.
    """
    
    name = "InitRetargeting"
    label = "Smart Match"
    
    def __init__(self):
        self.levenshtein_ratio = 1.0
        self.standart_shapes = False
        self.empty = False
        self.remove_prefix_target = ""
        self.remove_suffix_target = ""
        self.expression_sets = 'ALL'
        self.quick_search = False
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return True
    
    def invoke(self, context: Any) -> str:
        """Invoke the operator."""
        if not self.empty and not self.standart_shapes:
            # In Maya, we'd show a dialog
            return self.execute(context)
        else:
            return self.execute(context)
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        expression_sets_dict = {}
        
        if self.expression_sets in ('ALL', 'ARKIT'):
            name_scheme = self._get_name_scheme()
            if name_scheme == 'ARKIT':
                expression_sets_dict['ARKIT'] = fdata.get_arkit_shape_data()
            elif name_scheme == 'FACECAP':
                expression_sets_dict['ARKIT'] = fdata.get_face_cap_shape_data()
        
        if self.expression_sets in ('ALL', 'A2F'):
            expression_sets_dict['A2F'] = fdata.get_a2f_shape_data()
        
        faceit_objects = futils.get_faceit_objects_list()
        shape_key_names = sk_utils.get_shape_key_names_from_objects(faceit_objects)
        
        if not shape_key_names:
            cmds.warning("The registered objects have no shape keys.")
            return {'CANCELLED'}
        
        # Remove prefix/suffix from shape names
        match_names = {}
        new_names = []
        
        if self.remove_prefix_target or self.remove_suffix_target:
            for name in shape_key_names:
                name_match = name
                if self.remove_prefix_target and name.startswith(self.remove_prefix_target):
                    name_match = name[len(self.remove_prefix_target):]
                if self.remove_suffix_target and name.endswith(self.remove_suffix_target):
                    name_match = name[:-len(self.remove_suffix_target)]
                new_names.append(name_match)
                match_names[name_match] = name
        
        for expression_set, shape_dict in expression_sets_dict.items():
            if expression_set == 'ARKIT':
                retarget_list = self._get_retarget_shapes('ARKIT')
            else:
                retarget_list = self._get_retarget_shapes('A2F')
            
            new_retarget_list = []
            missing_shapes = []
            
            for expression_name, data in shape_dict.items():
                display_name = data.get('name', expression_name)
                
                item = {
                    'name': expression_name,
                    'display_name': display_name,
                    'target_shapes': [],
                    'amplify': 1.0,
                    'use_animation': True,
                    'region': 'other',
                    'target_list_index': 0
                }
                
                if self.empty:
                    new_retarget_list.append(item)
                    continue
                
                if self.standart_shapes:
                    item['target_shapes'].append({'name': expression_name})
                    new_retarget_list.append(item)
                    continue
                
                if display_name in shape_key_names:
                    item['target_shapes'].append({'name': display_name})
                    shape_key_names.remove(display_name)
                elif not self.quick_search:
                    if new_names:
                        found_shape = detection_manager.detect_shape(
                            new_names,
                            display_name,
                            min_levenshtein_ratio=self.levenshtein_ratio,
                            remove_suffix=self.remove_suffix_target
                        )
                        found_shape = match_names.get(found_shape)
                    else:
                        found_shape = detection_manager.detect_shape(
                            shape_key_names,
                            display_name,
                            min_levenshtein_ratio=self.levenshtein_ratio,
                            remove_suffix=self.remove_suffix_target
                        )
                    
                    if found_shape:
                        item['target_shapes'].append({'name': found_shape})
                        if found_shape in shape_key_names:
                            shape_key_names.remove(found_shape)
                    else:
                        missing_shapes.append(display_name)
                
                new_retarget_list.append(item)
            
            # Set regions
            region_dict = fdata.get_regions_dict()
            for item in new_retarget_list:
                shape_name = item.get('name', '')
                item['region'] = region_dict.get(shape_name, 'other')
            
            # Save list
            self._save_retarget_shapes(expression_set, new_retarget_list)
            
            if missing_shapes and not self.quick_search:
                cmds.warning(f"Couldn't find all {expression_set} target shapes. Missing: {', '.join(missing_shapes)}")
        
        cmds.warning("Retargeting initialized successfully.")
        return {'FINISHED'}
    
    def _get_retarget_shapes(self, shape_type: str) -> List[Dict]:
        """Get retarget shapes for a specific type."""
        attr_name = f"{shape_type.lower()}_retarget_shapes"
        if cmds.objExists("faceit_core_data"):
            if cmds.attributeQuery(attr_name, node="faceit_core_data", exists=True):
                data_str = cmds.getAttr(f"faceit_core_data.{attr_name}") or "[]"
                try:
                    return json.loads(data_str)
                except:
                    pass
        return []
    
    def _save_retarget_shapes(self, shape_type: str, shapes: List[Dict]) -> None:
        """Save retarget shapes for a specific type."""
        attr_name = f"{shape_type.lower()}_retarget_shapes"
        if cmds.objExists("faceit_core_data"):
            if cmds.attributeQuery(attr_name, node="faceit_core_data", exists=True):
                cmds.setAttr(f"faceit_core_data.{attr_name}", json.dumps(shapes), type="string")
    
    def _get_name_scheme(self) -> str:
        """Get current name scheme."""
        if cmds.objExists("faceit_core_data"):
            if cmds.attributeQuery("retargeting_naming_scheme", node="faceit_core_data", exists=True):
                scheme = cmds.getAttr("faceit_core_data.retargeting_naming_scheme")
                if scheme == 0:
                    return 'ARKIT'
                elif scheme == 1:
                    return 'FACECAP'
        return 'ARKIT'


# ============================================================
# Reset Retarget Shapes Operator
# ============================================================

class ResetRetargetShapes:
    """
    Clear the retarget shapes list.
    """
    
    name = "ResetRetargetShapes"
    label = "Reset"
    
    def __init__(self):
        self.expression_sets = 'ALL'
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return True
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        if self.expression_sets == 'ARKIT':
            if cmds.objExists("faceit_core_data"):
                if cmds.attributeQuery("arkit_retarget_shapes", node="faceit_core_data", exists=True):
                    cmds.setAttr("faceit_core_data.arkit_retarget_shapes", "[]", type="string")
            cmds.warning("ARKit retarget shapes cleared.")
        elif self.expression_sets == 'A2F':
            if cmds.objExists("faceit_core_data"):
                if cmds.attributeQuery("a2f_retarget_shapes", node="faceit_core_data", exists=True):
                    cmds.setAttr("faceit_core_data.a2f_retarget_shapes", "[]", type="string")
            cmds.warning("A2F retarget shapes cleared.")
        else:
            if cmds.objExists("faceit_core_data"):
                if cmds.attributeQuery("arkit_retarget_shapes", node="faceit_core_data", exists=True):
                    cmds.setAttr("faceit_core_data.arkit_retarget_shapes", "[]", type="string")
                if cmds.attributeQuery("a2f_retarget_shapes", node="faceit_core_data", exists=True):
                    cmds.setAttr("faceit_core_data.a2f_retarget_shapes", "[]", type="string")
            cmds.warning("All retarget shapes cleared.")
        
        return {'FINISHED'}


# ============================================================
# Import Retarget Map Operator
# ============================================================

class ImportRetargetMap:
    """
    Import a Retargeting Map from file.
    """
    
    name = "ImportRetargetMap"
    label = "Load Capture Profile"
    
    def __init__(self):
        self.filepath = "capture_profile.json"
        self.filter_glob = "*.json;"
        self.expression_sets = 'ARKIT'
        self.load_amplify_values = True
        self.load_regions = True
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return True
    
    def invoke(self, context: Any) -> str:
        """Invoke the operator."""
        self.filepath = "capture_profile.json"
        # In Maya, we'd use a file dialog
        return self.execute(context)
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        if not os.path.exists(self.filepath):
            cmds.warning(f"File not found: {self.filepath}")
            return {'CANCELLED'}
        
        try:
            with open(self.filepath, 'r') as f:
                data = json.load(f)
        except Exception as e:
            cmds.warning(f"Error reading file: {str(e)}")
            return {'CANCELLED'}
        
        if not isinstance(data, dict):
            cmds.warning("Invalid file format. Expected JSON object.")
            return {'CANCELLED'}
        
        # Determine which list to use
        if self.expression_sets == 'ARKIT':
            arkit_keys = fdata.get_arkit_shape_data().keys()
            if not any(x in arkit_keys for x in data.keys()):
                cmds.warning("The specified list seems to be an Audio2Face list")
                return {'CANCELLED'}
            retarget_list = self._get_retarget_shapes('ARKIT')
            empty_retarget_list = []
        else:
            a2f_keys = fdata.get_a2f_shape_data().keys()
            if not any(x in a2f_keys for x in data.keys()):
                cmds.warning("The specified list seems to be an ARKit list")
                return {'CANCELLED'}
            retarget_list = self._get_retarget_shapes('A2F')
            empty_retarget_list = []
        
        region_dict = fdata.get_regions_dict()
        
        for arkit_name, target_dict in data.items():
            target_shapes_list = target_dict.get('target_shapes', [])
            
            item = {
                'name': arkit_name,
                'display_name': arkit_name,
                'target_shapes': [],
                'amplify': target_dict.get('amplify', 1.0) if self.load_amplify_values else 1.0,
                'use_animation': True,
                'region': target_dict.get('region', region_dict.get(arkit_name, 'other')) if self.load_regions else region_dict.get(arkit_name, 'other'),
                'target_list_index': 0
            }
            
            for target_shape in target_shapes_list:
                if target_shape not in ('', '---', 'SKIP'):
                    item['target_shapes'].append({'name': target_shape})
            
            empty_retarget_list.append(item)
        
        self._save_retarget_shapes(self.expression_sets, empty_retarget_list)
        
        # Check for missing shapes
        target_shapes = get_all_set_target_shapes(empty_retarget_list)
        if target_shapes:
            scene_shape_keys = sk_utils.get_shape_key_names_from_objects()
            shapes_not_found = [s for s in target_shapes if s not in scene_shape_keys]
            if shapes_not_found:
                cmds.warning(f"Following shapes could not be found: {', '.join(shapes_not_found)}")
            else:
                cmds.warning(f"Successfully imported new {self.expression_sets} target shapes")
        else:
            cmds.warning("Failed to import from the template")
            return {'CANCELLED'}
        
        return {'FINISHED'}
    
    def _get_retarget_shapes(self, shape_type: str) -> List[Dict]:
        """Get retarget shapes for a specific type."""
        attr_name = f"{shape_type.lower()}_retarget_shapes"
        if cmds.objExists("faceit_core_data"):
            if cmds.attributeQuery(attr_name, node="faceit_core_data", exists=True):
                data_str = cmds.getAttr(f"faceit_core_data.{attr_name}") or "[]"
                try:
                    return json.loads(data_str)
                except:
                    pass
        return []
    
    def _save_retarget_shapes(self, shape_type: str, shapes: List[Dict]) -> None:
        """Save retarget shapes for a specific type."""
        attr_name = f"{shape_type.lower()}_retarget_shapes"
        if cmds.objExists("faceit_core_data"):
            if cmds.attributeQuery(attr_name, node="faceit_core_data", exists=True):
                cmds.setAttr(f"faceit_core_data.{attr_name}", json.dumps(shapes), type="string")


# ============================================================
# Export Retarget Map Operator
# ============================================================

class ExportRetargetMap:
    """
    Export mapping to JSON file.
    """
    
    name = "ExportRetargetMap"
    label = "Save Capture Profile"
    
    def __init__(self):
        self.filepath = "capture_profile.json"
        self.filter_glob = "*.json;"
        self.expression_sets = 'ARKIT'
        self.save_regions = True
        self.save_amplify_values = True
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        retarget_list = get_active_retarget_list()
        if retarget_list:
            return any(item.get('target_shapes', []) for item in retarget_list)
        return False
    
    def invoke(self, context: Any) -> str:
        """Invoke the operator."""
        self.filepath = "capture_profile.json"
        # In Maya, we'd use a file dialog
        return self.execute(context)
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        retarget_list = get_active_retarget_list()
        data = {}
        
        shape_dict = get_target_shapes_dict(retarget_list, force_empty_strings=True)
        
        for arkit_name, target_shape_list in shape_dict.items():
            _dict = {'target_shapes': target_shape_list}
            
            # Find the item
            for item in retarget_list:
                if item.get('name') == arkit_name:
                    if self.save_amplify_values:
                        _dict['amplify'] = item.get('amplify', 1.0)
                    if self.save_regions:
                        _dict['region'] = item.get('region', 'OTHER')
                    break
            
            data[arkit_name] = _dict
        
        if not data:
            cmds.warning("Export Failed. Could not find retarget data")
            return {'CANCELLED'}
        
        try:
            if not self.filepath.endswith('.json'):
                self.filepath += '.json'
            
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            
            cmds.warning(f"Exported to {self.filepath}")
        except Exception as e:
            cmds.warning(f"Error exporting: {str(e)}")
            return {'CANCELLED'}
        
        return {'FINISHED'}


# ============================================================
# Set Default Amplify Values Operator
# ============================================================

class SetDefaultAmplifyValues:
    """
    Set default amplify values for all items.
    """
    
    name = "SetDefaultAmplifyValues"
    label = "Set Default Amplify Values"
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return True
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        retarget_list = get_active_retarget_list()
        
        for item in retarget_list:
            item['amplify'] = 1.0
        
        save_active_retarget_list(retarget_list)
        
        cmds.warning("Default amplify values set successfully.")
        return {'FINISHED'}


# ============================================================
# Set Active Shape Key Index Operator
# ============================================================

class SetActiveShapeKeyIndex:
    """
    Set target shape as active shape key index on all registered objects.
    """
    
    name = "SetActiveShapeKeyIndex"
    label = "Set Active Shape Key"
    
    def __init__(self):
        self.debug = False
        self.shape_name = ""
        self.get_active_target_shapes = False
        self.amplify = 1.0
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return True
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        faceit_objects = futils.get_faceit_objects_list()
        
        # Get all possible target shapes
        arkit_list = self._get_retarget_shapes('ARKIT')
        a2f_list = self._get_retarget_shapes('A2F')
        expression_list = self._get_expression_list()
        
        all_expression_names = get_all_set_target_shapes(arkit_list)
        all_expression_names.extend(get_all_set_target_shapes(a2f_list))
        all_expression_names.extend([expr.get('name', '') for expr in expression_list])
        
        # Get target shapes
        target_shapes = []
        jawOpen_item = None
        
        if self.get_active_target_shapes:
            retarget_list = get_active_retarget_list()
            
            if self.shape_name:
                for item in retarget_list:
                    if item.get('name') == self.shape_name:
                        active_shape_item = item
                        break
                else:
                    active_shape_item = None
                
                if self.shape_name == 'mouthClose':
                    for item in retarget_list:
                        if item.get('name') == 'jawOpen':
                            jawOpen_item = item
                            break
            else:
                active_shape_item = retarget_list[0] if retarget_list else None
            
            if active_shape_item:
                target_shapes = [ts.get('name', '') for ts in active_shape_item.get('target_shapes', [])]
        else:
            target_shapes = [self.shape_name]
        
        if not target_shapes:
            return {'CANCELLED'}
        
        for obj in faceit_objects:
            if not cmds.objExists(obj):
                continue
            
            if not sk_utils.has_shape_keys(obj):
                continue
            
            blend_node = sk_utils.get_blend_shape_node(obj)
            if not blend_node:
                continue
            
            # Reset all expression shape values
            for expr_name in all_expression_names:
                if cmds.attributeQuery(expr_name, node=blend_node, exists=True):
                    cmds.setAttr(f"{blend_node}.{expr_name}", 0)
            
            # Set target shapes
            _set_active = False
            
            for target_shape_name in target_shapes:
                if cmds.attributeQuery(target_shape_name, node=blend_node, exists=True):
                    if not _set_active:
                        # Set as active (in Maya, we can't set active blend shape target)
                        # We'll just set the weight
                        _set_active = True
                    
                    # Set amplify value
                    cmds.setAttr(f"{blend_node}.{target_shape_name}", self.amplify)
            
            # Handle jawOpen for mouthClose
            if jawOpen_item is not None:
                for ts in jawOpen_item.get('target_shapes', []):
                    jaw_open_name = ts.get('name', '')
                    if cmds.attributeQuery(jaw_open_name, node=blend_node, exists=True):
                        cmds.setAttr(f"{blend_node}.{jaw_open_name}", jawOpen_item.get('amplify', 1.0))
        
        return {'FINISHED'}
    
    def _get_retarget_shapes(self, shape_type: str) -> List[Dict]:
        """Get retarget shapes for a specific type."""
        attr_name = f"{shape_type.lower()}_retarget_shapes"
        if cmds.objExists("faceit_core_data"):
            if cmds.attributeQuery(attr_name, node="faceit_core_data", exists=True):
                data_str = cmds.getAttr(f"faceit_core_data.{attr_name}") or "[]"
                try:
                    return json.loads(data_str)
                except:
                    pass
        return []
    
    def _get_expression_list(self) -> List[Dict]:
        """Get expression list from scene."""
        if cmds.objExists("faceit_core_data"):
            if cmds.attributeQuery("expression_list", node="faceit_core_data", exists=True):
                data_str = cmds.getAttr("faceit_core_data.expression_list") or "[]"
                try:
                    return json.loads(data_str)
                except:
                    pass
        return []