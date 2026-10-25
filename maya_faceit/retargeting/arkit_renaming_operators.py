# arkit_renaming_operators.py
# Maya Faceit Plugin - ARKit Renaming Operators
# Converted from Blender to Maya Python 3.11

"""
ARKit renaming operators for Faceit Maya plugin.
Handles name scheme changes and retargeting name application.
"""

import maya.cmds as cmds # type: ignore
import json
from typing import List, Dict, Optional, Any

from ..core import faceit_data as fdata
from ..core import faceit_utils as futils
from ..core import shape_key_utils as sk_utils


# ============================================================
# Change Name Scheme Operator
# ============================================================

class ChangeRetargetingNameScheme:
    """
    Change the retargeting list name scheme.
    """
    
    name = "ChangeRetargetingNameScheme"
    label = "Change Naming Scheme"
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return True
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        # Get retarget shapes from scene
        retarget_list = self._get_retarget_shapes()
        
        if not retarget_list:
            cmds.warning("No retarget shapes found.")
            return {'CANCELLED'}
        
        name_scheme = self._get_name_scheme()
        
        if name_scheme == 'ARKIT':
            shape_dict = fdata.get_arkit_shape_data()
        elif name_scheme == 'FACECAP':
            shape_dict = fdata.get_face_cap_shape_data()
        else:
            cmds.warning(f"Unknown name scheme: {name_scheme}")
            return {'CANCELLED'}
        
        # Update display names
        new_index_dict = {}
        for arkit_name, data in shape_dict.items():
            new_index = data.get('index', 0)
            display_name = data.get('name', arkit_name)
            
            # Find item in list
            for item in retarget_list:
                if item.get('name') == arkit_name:
                    item['display_name'] = display_name
                    new_index_dict[arkit_name] = new_index
                    break
        
        # Sort by new indices
        def find_new_index(index):
            if index < len(retarget_list):
                name = retarget_list[index].get('name', '')
                return new_index_dict.get(name, index)
            return index
        
        # Bubble sort
        for passes_left in range(len(retarget_list) - 1, 0, -1):
            for idx in range(passes_left):
                idx_1 = find_new_index(idx)
                idx_2 = find_new_index(idx + 1)
                if idx_1 > idx_2:
                    retarget_list[idx], retarget_list[idx + 1] = retarget_list[idx + 1], retarget_list[idx]
        
        # Save changes
        self._save_retarget_shapes(retarget_list)
        
        cmds.warning("Name scheme updated successfully.")
        return {'FINISHED'}
    
    def _get_retarget_shapes(self) -> List[Dict]:
        """Get retarget shapes from scene."""
        if cmds.objExists("faceit_core_data"):
            if cmds.attributeQuery("arkit_retarget_shapes", node="faceit_core_data", exists=True):
                data_str = cmds.getAttr("faceit_core_data.arkit_retarget_shapes") or "[]"
                try:
                    return json.loads(data_str)
                except:
                    pass
        return []
    
    def _save_retarget_shapes(self, shapes: List[Dict]) -> None:
        """Save retarget shapes to scene."""
        if cmds.objExists("faceit_core_data"):
            if cmds.attributeQuery("arkit_retarget_shapes", node="faceit_core_data", exists=True):
                cmds.setAttr("faceit_core_data.arkit_retarget_shapes", json.dumps(shapes), type="string")
    
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
# Retarget Names Operator
# ============================================================

class RetargetNames:
    """
    Apply the ARKit names to the specified Shape Keys.
    """
    
    name = "RetargetNames"
    label = "Apply Source Naming"
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return True
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        faceit_objects = futils.get_faceit_objects_list()
        retarget_list = self._get_retarget_shapes()
        
        if not retarget_list:
            cmds.warning("No retarget shapes found.")
            return {'CANCELLED'}
        
        if not faceit_objects:
            cmds.warning("No Faceit objects found.")
            return {'CANCELLED'}
        
        renamed_count = 0
        
        for obj in faceit_objects:
            if not cmds.objExists(obj):
                continue
            
            if not sk_utils.has_shape_keys(obj):
                continue
            
            blend_node = sk_utils.get_blend_shape_node(obj)
            if not blend_node:
                continue
            
            for item in retarget_list:
                target_shapes = item.get('target_shapes', [])
                
                if not target_shapes:
                    continue
                
                # Get first target shape
                target_shape_item = None
                target_list_index = item.get('target_list_index', 0)
                
                if target_list_index < len(target_shapes):
                    target_shape_item = target_shapes[target_list_index]
                
                if not target_shape_item:
                    target_shape_item = target_shapes[0]
                
                if not target_shape_item:
                    continue
                
                target_name = target_shape_item.get('name', '')
                display_name = item.get('display_name', item.get('name', ''))
                
                # Check if target exists
                if cmds.attributeQuery(target_name, node=blend_node, exists=True):
                    # Rename the target
                    # In Maya, we need to use aliasAttr to rename blend shape targets
                    cmds.aliasAttr(display_name, f"{blend_node}.{target_name}")
                    
                    # Update the target shape name in the list
                    target_shape_item['name'] = display_name
                    renamed_count += 1
        
        # Save changes
        self._save_retarget_shapes(retarget_list)
        
        cmds.warning(f"Successfully renamed {renamed_count} shape keys.")
        return {'FINISHED'}
    
    def _get_retarget_shapes(self) -> List[Dict]:
        """Get retarget shapes from scene."""
        if cmds.objExists("faceit_core_data"):
            if cmds.attributeQuery("arkit_retarget_shapes", node="faceit_core_data", exists=True):
                data_str = cmds.getAttr("faceit_core_data.arkit_retarget_shapes") or "[]"
                try:
                    return json.loads(data_str)
                except:
                    pass
        return []
    
    def _save_retarget_shapes(self, shapes: List[Dict]) -> None:
        """Save retarget shapes to scene."""
        if cmds.objExists("faceit_core_data"):
            if cmds.attributeQuery("arkit_retarget_shapes", node="faceit_core_data", exists=True):
                cmds.setAttr("faceit_core_data.arkit_retarget_shapes", json.dumps(shapes), type="string")