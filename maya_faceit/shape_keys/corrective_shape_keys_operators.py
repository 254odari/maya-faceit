# corrective_shape_keys_operators.py
# Maya Faceit Plugin - Corrective Shape Keys Operators
# Converted from Blender to Maya Python 3.11

"""
Corrective shape keys operators for Faceit Maya plugin.
Handles corrective shape key creation, editing, and removal.
"""

import json
import maya.cmds as cmds # type: ignore
import maya.api.OpenMaya as om2 # type: ignore
from typing import List, Dict, Optional, Any

from ..core import faceit_utils as futils
from ..core import shape_key_utils as sk_utils
from ..core import modifier_utils
from . import corrective_shape_keys_utils


# ============================================================
# Reevaluate Corrective Shape Keys Operator
# ============================================================

class ReevaluateCorrectiveShapeKeys:
    """
    Sync Corrective Shape Keys. Re-evaluate the keyframes and properties for each expression.
    """
    
    name = "ReevaluateCorrectiveShapeKeys"
    label = "Re-evaluate Corrective Shape Keys"
    
    def __init__(self):
        self.expression = 'ALL'
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return True
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        expression_list = self._get_expression_list()
        faceit_objects = futils.get_faceit_objects_list()
        
        corrective_shape_keys_utils.reevaluate_corrective_shape_keys(expression_list, faceit_objects)
        
        cmds.warning("Re-evaluated the corrective shape keys.")
        return {'FINISHED'}
    
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


# ============================================================
# Add Corrective Shape Key to Expression Operator
# ============================================================

class AddCorrectiveShapeKeyToExpression:
    """
    Add Corrective Shape Key to this Expression (Selected Object).
    """
    
    name = "AddCorrectiveShapeKeyToExpression"
    label = "Corrective Shape Key"
    
    def __init__(self):
        self.expression = 'ALL'
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        selection = cmds.ls(selection=True, type='transform')
        if selection:
            obj = selection[0]
            if cmds.objExists(obj):
                if sk_utils.has_shape_keys(obj):
                    return True
        return False
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        selection = cmds.ls(selection=True, type='transform')
        
        if not selection:
            cmds.warning("Select at least one registered object!")
            return {'CANCELLED'}
        
        # Filter to faceit objects
        faceit_objects = futils.get_faceit_objects_list()
        objects = [obj for obj in selection if obj in faceit_objects]
        
        if not objects:
            cmds.warning("Select at least one registered object!")
            return {'CANCELLED'}
        
        expression_list = self._get_expression_list()
        
        # Find expression
        exp_item = None
        for item in expression_list:
            if item.get('name') == self.expression:
                exp_item = item
                break
        
        if not exp_item:
            cmds.warning(f"Expression '{self.expression}' not found")
            return {'CANCELLED'}
        
        exp_name = exp_item.get('name', '')
        frame = exp_item.get('frame', 0)
        sk_name = f'faceit_cc_{exp_name}'
        
        # Set current frame
        cmds.currentTime(frame)
        
        # Get mirror state
        mirror_x = exp_item.get('mirror_name', '') != ''
        
        for obj in objects:
            if not cmds.objExists(obj):
                continue
            
            # Set mirror
            if cmds.attributeQuery("useMirrorX", node=obj, exists=True):
                cmds.setAttr(f"{obj}.useMirrorX", 1 if mirror_x else 0)
            
            # Add shape key
            if not sk_utils.has_shape_keys(obj):
                # Create blend shape node
                cmds.blendShape(obj, name=f"{obj}_faceit_blendShape")
                # Add target
                blend_node = sk_utils.get_blend_shape_node(obj)
                if blend_node:
                    # Create a temp mesh
                    temp_mesh = self._create_temp_mesh(obj)
                    if temp_mesh:
                        cmds.blendShape(blend_node, edit=True, target=(obj, 0, temp_mesh, 1.0))
                        cmds.aliasAttr(sk_name, f"{blend_node}.weight[0]")
                        cmds.setAttr(f"{blend_node}.{sk_name}", 0)
                        cmds.delete(temp_mesh)
            else:
                blend_node = sk_utils.get_blend_shape_node(obj)
                if blend_node:
                    if not cmds.attributeQuery(sk_name, node=blend_node, exists=True):
                        # Create temp mesh
                        temp_mesh = self._create_temp_mesh(obj)
                        if temp_mesh:
                            cmds.blendShape(blend_node, edit=True, target=(obj, 0, temp_mesh, 1.0))
                            weight_attrs = cmds.listAttr(f"{blend_node}.weight", multi=True) or []
                            weight_attrs = [a for a in weight_attrs if a.startswith('weight[')]
                            if weight_attrs:
                                cmds.aliasAttr(sk_name, f"{blend_node}.{weight_attrs[-1]}")
                            cmds.setAttr(f"{blend_node}.{sk_name}", 0)
                            cmds.delete(temp_mesh)
            
            # Assign corrective action
            corrective_shape_keys_utils.assign_corrective_sk_action(obj)
        
        # Update expression item
        exp_item['corr_shape_key'] = True
        
        # Keyframe corrective action
        corrective_shape_keys_utils.keyframe_corrective_sk_action(exp_item)
        
        cmds.warning(f"Added corrective shape key '{sk_name}' to {len(objects)} object(s).")
        return {'FINISHED'}
    
    def _create_temp_mesh(self, obj: str) -> Optional[str]:
        """Create a temporary mesh for shape key."""
        if not cmds.objExists(obj):
            return None
        
        # Duplicate mesh
        temp_mesh = cmds.duplicate(obj, name=f"{obj}_temp")[0]
        cmds.delete(temp_mesh, constructionHistory=True)
        
        return temp_mesh
    
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


# ============================================================
# Remove Corrective Shape Key Operator
# ============================================================

class RemoveCorrectiveShapeKey:
    """
    Remove Corrective Shape Key from spec expression.
    """
    
    name = "RemoveCorrectiveShapeKey"
    label = "Remove Corrective Shape Key"
    
    def __init__(self):
        self.expression = 'ALL'
        self.operate_objects = 'None'
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return True
    
    def invoke(self, context: Any) -> str:
        """Invoke the operator."""
        return self.execute(context)
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        # Get operate objects
        operate_objects = []
        objects_txt = ''
        
        if self.operate_objects == 'ALL':
            operate_objects = futils.get_faceit_objects_list()
            objects_txt = 'all objects'
        else:
            obj = self.operate_objects
            if cmds.objExists(obj):
                operate_objects.append(obj)
                objects_txt = f'object {obj}'
            else:
                cmds.warning(f"Object '{obj}' not found")
                return {'CANCELLED'}
        
        if not operate_objects:
            cmds.warning("No objects to operate on")
            return {'CANCELLED'}
        
        expression_list = self._get_expression_list()
        
        # Find expression
        exp_item = None
        for item in expression_list:
            if item.get('name') == self.expression:
                exp_item = item
                break
        
        if not exp_item:
            cmds.warning(f"Expression '{self.expression}' not found")
            return {'CANCELLED'}
        
        exp_name = exp_item.get('name', '')
        frame = exp_item.get('frame', 0)
        
        # Set current frame
        cmds.currentTime(frame)
        
        # Remove corrective shape key
        success = corrective_shape_keys_utils.remove_corrective_shape_key(
            expression_list, operate_objects, expression_name=exp_name
        )
        
        if success:
            cmds.warning(f"Removed the corrective sculpt from {objects_txt} for expression {exp_name}")
        else:
            cmds.warning(f"No corrective sculpt found for {objects_txt}")
        
        return {'FINISHED'}
    
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


# ============================================================
# Clear Corrective Shape Keys Operator
# ============================================================

class ClearCorrectiveShapeKeys:
    """
    Clear all Corrective Shape Keys from registered objects.
    """
    
    name = "ClearCorrectiveShapeKeys"
    label = "Clear all Corrective Shape Keys"
    
    def __init__(self):
        self.expression = 'ALL'
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return True
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        expression_list = self._get_expression_list()
        faceit_objects = futils.get_faceit_objects_list()
        
        if self.expression and self.expression != 'ALL':
            corrective_shape_keys_utils.remove_corrective_shape_key(
                expression_list, faceit_objects, expression_name=self.expression
            )
        else:
            corrective_shape_keys_utils.clear_all_corrective_shape_keys(faceit_objects, expression_list)
        
        cmds.warning("Cleared all corrective shape keys.")
        return {'FINISHED'}
    
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