# animate_operators.py
# Maya Faceit Plugin - Animation Operators
# Converted from Blender to Maya Python 3.11

"""
Animation operators for Maya Faceit plugin.
Handles expression management, animation operations, and procedural animations.
"""

import os
import json
import time
import math
from typing import List, Dict, Optional, Tuple, Set
import maya.cmds as cmds
import maya.api.OpenMaya as om2
from maya.api.OpenMaya import MVector, MMatrix, MQuaternion, MEulerRotation
import numpy as np

# Import core modules
from ..core.faceit_utils import get_faceit_armature, get_faceit_objects, set_active_object
from ..core.faceit_data import FACEIT_CTRL_BONES, FACEIT_BONES
from ..properties.expression_scene_properties import PROCEDURAL_EXPRESSION_ITEMS

# Mirror side dictionaries
MIRROR_SIDES_DICT_L = {
    'left': 'right',
    'Left': 'Right',
    'LEFT': 'RIGHT',
    'L_': 'R_',
    '_L': '_R',
}

MIRROR_SIDES_DICT_R = {
    'right': 'left',
    'Right': 'Left',
    'RIGHT': 'LEFT',
    'R_': 'L_',
    '_R': '_L',
}

MIRROR_END_L = {'L': 'R', '_l': '_r'}
MIRROR_END_R = {'R': 'L', '_r': '_l'}

# ============================================================
# Helper Functions
# ============================================================

def get_side(expression_name: str) -> str:
    """Return the side L/N/R for the given expression name."""
    if any(x in expression_name for x in MIRROR_SIDES_DICT_L) or \
       any(expression_name.endswith(x) for x in MIRROR_END_L):
        return 'L'
    elif any(x in expression_name for x in MIRROR_SIDES_DICT_R) or \
         any(expression_name.endswith(x) for x in MIRROR_END_R):
        return 'R'
    return 'N'


def poll_side_in_expression_name(side: str, expression_name: str) -> bool:
    """Check if the correct side is in the expression name."""
    if side == 'L':
        return any(x in expression_name for x in MIRROR_SIDES_DICT_L) or \
               any(expression_name.endswith(x) for x in MIRROR_END_L)
    if side == "R":
        return any(x in expression_name for x in MIRROR_SIDES_DICT_R) or \
               any(expression_name.endswith(x) for x in MIRROR_END_R)
    return False


def get_mirror_name(side: str, expression_name: str) -> str:
    """Return the mirror name for the given expression name and side."""
    if side == "L":
        for key, value in MIRROR_SIDES_DICT_L.items():
            if key in expression_name:
                return expression_name.replace(key, value)
        for key, value in MIRROR_END_L.items():
            if expression_name.endswith(key):
                return expression_name.replace(key, value)
    if side == "R":
        for key, value in MIRROR_SIDES_DICT_R.items():
            if key in expression_name:
                return expression_name.replace(key, value)
        for key, value in MIRROR_END_R.items():
            if expression_name.endswith(key):
                return expression_name.replace(key, value)
    return ''


def get_blendshape_names(mesh: str) -> List[str]:
    """Get all blend shape names from a mesh."""
    if not cmds.objExists(mesh):
        return []
    
    # Find blendShape node
    history = cmds.listHistory(mesh, pruneDagObjects=True, interestLevel=2) or []
    for node in history:
        if cmds.nodeType(node) == 'blendShape':
            # Get all targets
            targets = cmds.listAttr(f"{node}.weight", multi=True) or []
            # Get actual target names
            names = []
            for attr in targets:
                if attr.startswith('weight'):
                    names.append(attr)
            return names
    return []


def get_maya_version() -> Tuple[int, int, int]:
    """Get Maya version as tuple."""
    version = cmds.about(version=True)
    parts = version.split('.')
    return tuple(int(p) for p in parts[:3])


# ============================================================
# Main Animation Operators
# ============================================================

class AddExpressionItem:
    """Add a new expression to the expression list and animation."""
    
    name = "AddExpressionItem"
    label = "Add Expression"
    
    def __init__(self):
        self.expression_name = "Expression"
        self.new_exp_index = -1
        self.expression_sk_exists = False
        self.expression_item_exists = False
        self.mirror_name_overwrite = ""
        self.side = 'N'
        self.side_suffix_found = False
        self.custom_shape = False
        self.auto_mirror = False
        self.procedural_eyeblinks = False
        self.procedural = 'NONE'
        self.is_new_rigify_rig = False
    
    def check_expression_valid(self):
        """Check if expression is valid."""
        self.expression_sk_exists = self.expression_name in get_blendshape_names(get_faceit_armature())
        # Check if expression exists in scene data
        if cmds.objExists("faceit_expression_data"):
            data = cmds.getAttr("faceit_expression_data.names") or ""
            self.expression_item_exists = self.expression_name in data.split(',')
    
    def execute(self):
        """Execute the add expression operation."""
        # Get scene data
        if not cmds.objExists("faceit_expression_data"):
            cmds.addAttr("faceit_expression_data", ln="names", dt="string")
            cmds.addAttr("faceit_expression_data", ln="frames", dt="string")
            cmds.addAttr("faceit_expression_data", ln="sides", dt="string")
            cmds.addAttr("faceit_expression_data", ln="procedural", dt="string")
        
        # Get current data
        names_str = cmds.getAttr("faceit_expression_data.names") or ""
        frames_str = cmds.getAttr("faceit_expression_data.frames") or ""
        sides_str = cmds.getAttr("faceit_expression_data.sides") or ""
        procedural_str = cmds.getAttr("faceit_expression_data.procedural") or ""
        
        names = names_str.split(',') if names_str else []
        frames = [int(x) for x in frames_str.split(',')] if frames_str else []
        sides = sides_str.split(',') if sides_str else []
        procedural_list = procedural_str.split(',') if procedural_str else []
        
        # Check for duplicates and generate unique name
        expression_name_final = self.expression_name
        counter = 1
        while expression_name_final in names:
            expression_name_final = f"{self.expression_name}_{counter}"
            counter += 1
        
        # Calculate frame
        if self.new_exp_index == -1:
            index = len(names)
        else:
            index = self.new_exp_index
        
        frame = int((index + 1) * 10)
        
        # Add to lists
        names.append(expression_name_final)
        frames.append(frame)
        sides.append(self.side)
        procedural_list.append(self.procedural)
        
        # Save data
        cmds.setAttr("faceit_expression_data.names", ",".join(names), type="string")
        cmds.setAttr("faceit_expression_data.frames", ",".join(frames), type="string")
        cmds.setAttr("faceit_expression_data.sides", ",".join(sides), type="string")
        cmds.setAttr("faceit_expression_data.procedural", ",".join(procedural_list), type="string")
        
        # Set current index
        cmds.setAttr("faceit_expression_data.current_index", index)
        
        # Custom expression handling
        if self.custom_shape:
            self._handle_custom_expression(expression_name_final, frame)
        
        # Mirror expression
        if self.auto_mirror and self.side != 'N':
            self._mirror_expression(expression_name_final)
        
        return True
    
    def _handle_custom_expression(self, expression_name: str, frame: int):
        """Handle custom expression creation."""
        rig = get_faceit_armature()
        if not rig:
            return
        
        # Get or create animation data
        if not cmds.listConnections(f"{rig}.animationData"):
            cmds.animData(rig, add=True)
        
        # Get or create action
        action_name = "faceit_shape_action"
        if not cmds.objExists(action_name):
            cmds.animData(rig, action=action_name)
        
        # Add keyframes for all control bones
        for bone_name in FACEIT_BONES:
            if "MCH" in bone_name or "DEF" in bone_name:
                continue
            
            base_dp = f"{bone_name}.translate"
            for i in range(3):
                cmds.setKeyframe(rig, attribute=f"translate{i}", t=frame, v=0)
            
            base_dp = f"{bone_name}.scale"
            for i in range(3):
                cmds.setKeyframe(rig, attribute=f"scale{i}", t=frame, v=1)
            
            base_dp = f"{bone_name}.rotate"
            for i in range(3):
                cmds.setKeyframe(rig, attribute=f"rotate{i}", t=frame, v=0)
        
        # Procedural expression
        if self.procedural != 'NONE':
            self._add_procedural_expression(frame)
    
    def _add_procedural_expression(self, frame: int):
        """Add procedural expression."""
        if self.procedural == 'EYEBLINKS':
            # Create procedural eye blink keyframes
            rig = get_faceit_armature()
            if not rig:
                return
            
            side = self.side
            # Get lid bones
            if side == 'L' or side == 'N':
                self._create_eye_blink_animation(rig, 'L', frame)
            if side == 'R' or side == 'N':
                self._create_eye_blink_animation(rig, 'R', frame)
    
    def _create_eye_blink_animation(self, rig: str, side: str, frame: int):
        """Create eye blink animation for one side."""
        # Get lid bones
        top_lid_bones = [
            f"lid.T.{side}.003",
            f"lid.T.{side}.002",
            f"lid.T.{side}.001"
        ]
        bot_lid_bones = [
            f"lid.B.{side}.001",
            f"lid.B.{side}.002",
            f"lid.B.{side}.003"
        ]
        
        # Animate top lid down
        for bone_name in top_lid_bones:
            if cmds.objExists(bone_name):
                # Move lid down by setting translate Y
                current_pos = cmds.getAttr(f"{bone_name}.translate")[0]
                cmds.setKeyframe(bone_name, attribute="translateY", t=frame - 9, v=current_pos[1])
                cmds.setKeyframe(bone_name, attribute="translateY", t=frame, v=current_pos[1] - 0.3)
                cmds.setKeyframe(bone_name, attribute="translateY", t=frame + 1, v=current_pos[1])
        
        # Animate bottom lid slightly up
        for bone_name in bot_lid_bones:
            if cmds.objExists(bone_name):
                current_pos = cmds.getAttr(f"{bone_name}.translate")[0]
                cmds.setKeyframe(bone_name, attribute="translateY", t=frame - 9, v=current_pos[1])
                cmds.setKeyframe(bone_name, attribute="translateY", t=frame, v=current_pos[1] + 0.1)
                cmds.setKeyframe(bone_name, attribute="translateY", t=frame + 1, v=current_pos[1])
    
    def _mirror_expression(self, expression_name: str):
        """Create mirror expression."""
        mirror_side = 'R' if self.side == 'L' else 'L'
        mirror_name = get_mirror_name(self.side, expression_name)
        
        if mirror_name:
            mirror_expr = AddExpressionItem()
            mirror_expr.expression_name = mirror_name
            mirror_expr.custom_shape = True
            mirror_expr.side = mirror_side
            mirror_expr.procedural = self.procedural
            mirror_expr.execute()


class ResetBoneConstraints:
    """Reset all bone constraints to default values."""
    
    name = "ResetBoneConstraints"
    label = "Reset Bone Constraints"
    
    # Default constraint influence values
    CONSTRAINT_DEFAULTS = {
        'lip.T.L.001': {"Copy Location": 0.25, "Copy Location.001": 0.5, "Copy Rotation": 1.0, "Copy Scale": 1.0},
        'lip.T.R.001': {"Copy Location": 0.25, "Copy Location.001": 0.5, "Copy Rotation": 1.0, "Copy Scale": 1.0},
        'lip.B.L.001': {"Copy Location": 0.25, "Copy Location.001": 0.5, "Copy Rotation": 1.0, "Copy Scale": 1.0},
        'lip.B.R.001': {"Copy Location": 0.25, "Copy Location.001": 0.5, "Copy Rotation": 1.0, "Copy Scale": 1.0},
        'lid.T.L.003': {"Copy Location": 0.6, "Copy Rotation": 1.0},
        'lid.T.L.002': {"Copy Location": 0.5},
        'lid.T.L.001': {"Copy Location": 0.6, "Copy Rotation": 1.0},
        'lid.B.L.001': {"Copy Rotation": 1.0, "Copy Location": 0.6},
        'lid.B.L.002': {"Copy Location": 0.5, "Copy Location.001": 0.1},
        'lid.B.L.003': {"Copy Rotation": 1.0, "Copy Location": 0.6},
        'brow.B.L.003': {"Copy Location": 0.6},
        'brow.B.L.002': {"Copy Location": 0.25},
        'brow.B.L.001': {"Copy Location": 0.6},
        'lid.T.R.003': {"Copy Location": 0.6},
        'lid.T.R.002': {"Copy Location": 0.5},
        'lid.T.R.001': {"Copy Location": 0.6},
        'lid.B.R.001': {"Copy Location": 0.6},
        'lid.B.R.002': {"Copy Location": 0.5, "Copy Location.001": 0.1},
        'lid.B.R.003': {"Copy Location": 0.6},
        'brow.B.R.003': {"Copy Location": 0.6},
        'brow.B.R.002': {"Copy Location": 0.25},
        'brow.B.R.001': {"Copy Location": 0.6},
        'nose.005': {'Copy Location': 0.5},
        'nose.003': {'Copy Location': 0.5},
        'nose.L.001': {'Copy Location': 0.2},
        'nose.R.001': {'Copy Location': 0.2},
        'cheek.T.L.001': {'Copy Location': 0.0},
        'cheek.T.R.001': {'Copy Location': 0.0},
        'nose.L': {'Copy Location': 0.25},
        'nose.R': {'Copy Location': 0.25},
        'chin.002': {'Copy Location': 0.5},
        'cheek.B.L.001': {'Copy Location': 0.5},
        'cheek.B.R.001': {'Copy Location': 0.5},
        'brow.T.L.002': {'Copy Location': 0.5, 'Copy Location.001': 0.5},
        'brow.T.R.002': {'Copy Location': 0.5, 'Copy Location.001': 0.5},
    }
    
    def execute(self):
        """Reset all constraints to default values."""
        rig = get_faceit_armature()
        if not rig:
            cmds.warning("No Faceit armature found")
            return False
        
        for bone_name, constraints_dict in self.CONSTRAINT_DEFAULTS.items():
            if not cmds.objExists(bone_name):
                continue
            
            for constraint_name, influence in constraints_dict.items():
                # Find constraint on bone
                constraints = cmds.listConnections(f"{bone_name}.constraints") or []
                for constr in constraints:
                    if cmds.objExists(constr) and cmds.nodeType(constr) == 'constraint':
                        # Check if this is the right constraint
                        if cmds.getAttr(f"{constr}.name") == constraint_name:
                            try:
                                cmds.setAttr(f"{constr}.influence", influence)
                            except:
                                pass
        
        return True


class MirrorCopyExpression:
    """Copy and mirror an expression."""
    
    name = "MirrorCopyExpression"
    label = "Mirror Copy Expression"
    
    def __init__(self, expression_name: str = ""):
        self.expression_name = expression_name
    
    def execute(self):
        """Execute mirror copy operation."""
        # Get expression data
        if not self.expression_name:
            # Use current expression from scene data
            if cmds.objExists("faceit_expression_data"):
                current_idx = cmds.getAttr("faceit_expression_data.current_index") or 0
                names_str = cmds.getAttr("faceit_expression_data.names") or ""
                names = names_str.split(',') if names_str else []
                if current_idx < len(names):
                    self.expression_name = names[current_idx]
                else:
                    return False
        
        side = get_side(self.expression_name)
        if side == 'N':
            cmds.warning("Expression is not side-specific")
            return False
        
        mirror_name = get_mirror_name(side, self.expression_name)
        if not mirror_name:
            return False
        
        # Create mirrored expression
        mirror_side = 'R' if side == 'L' else 'L'
        
        # Copy animation data
        self._copy_animation_to_mirror(self.expression_name, mirror_name, mirror_side)
        
        return True
    
    def _copy_animation_to_mirror(self, source: str, target: str, target_side: str):
        """Copy animation data from source to mirrored target."""
        # Get source frames
        if cmds.objExists("faceit_expression_data"):
            names_str = cmds.getAttr("faceit_expression_data.names") or ""
            frames_str = cmds.getAttr("faceit_expression_data.frames") or ""
            names = names_str.split(',') if names_str else []
            frames = [int(x) for x in frames_str.split(',')] if frames_str else []
            
            if source in names:
                idx = names.index(source)
                source_frame = frames[idx]
                
                # Add target expression
                add_expr = AddExpressionItem()
                add_expr.expression_name = target
                add_expr.side = target_side
                add_expr.custom_shape = True
                add_expr.execute()
                
                # Mirror animation from source frame to target frame
                self._mirror_keyframe(source_frame, target_frame=frames[len(frames) - 1])
    
    def _mirror_keyframe(self, frame_from: int, frame_to: int):
        """Mirror keyframe data from one frame to another."""
        rig = get_faceit_armature()
        if not rig:
            return
        
        # Get animation data
        if not cmds.listConnections(f"{rig}.animationData"):
            return
        
        # For each control bone, copy and mirror transforms
        for bone_name in FACEIT_CTRL_BONES:
            if not cmds.objExists(bone_name):
                continue
            
            # Get transforms at source frame
            cmds.currentTime(frame_from)
            t = cmds.getAttr(f"{bone_name}.translate")[0]
            r = cmds.getAttr(f"{bone_name}.rotate")[0]
            s = cmds.getAttr(f"{bone_name}.scale")[0]
            
            # Mirror transforms (X axis flip)
            t_mirrored = [-t[0], t[1], t[2]]
            r_mirrored = [-r[0], r[1], -r[2]]
            s_mirrored = [s[0], s[1], s[2]]
            
            # Set keyframes at target frame
            cmds.currentTime(frame_to)
            cmds.setAttr(f"{bone_name}.translateX", t_mirrored[0])
            cmds.setAttr(f"{bone_name}.translateY", t_mirrored[1])
            cmds.setAttr(f"{bone_name}.translateZ", t_mirrored[2])
            cmds.setKeyframe(bone_name, attribute="translate", t=frame_to)
            
            cmds.setAttr(f"{bone_name}.rotateX", r_mirrored[0])
            cmds.setAttr(f"{bone_name}.rotateY", r_mirrored[1])
            cmds.setAttr(f"{bone_name}.rotateZ", r_mirrored[2])
            cmds.setKeyframe(bone_name, attribute="rotate", t=frame_to)


class EmptyExpressionsFromBlendShapes:
    """Create empty expressions from existing blend shapes."""
    
    name = "EmptyExpressionsFromBlendShapes"
    label = "Create Expressions from Blend Shapes"
    
    def execute(self):
        """Create expressions from all blend shapes on selected meshes."""
        selection = cmds.ls(selection=True, type='transform')
        if not selection:
            cmds.warning("Please select a mesh with blend shapes")
            return False
        
        for obj in selection:
            # Check if mesh has blend shapes
            history = cmds.listHistory(obj, pruneDagObjects=True, interestLevel=2) or []
            for node in history:
                if cmds.nodeType(node) == 'blendShape':
                    # Get all targets
                    targets = cmds.listAttr(f"{node}.weight", multi=True) or []
                    for attr in targets:
                        if attr.startswith('weight'):
                            # Get target name
                            target_name = attr.replace('weight[', '').replace(']', '')
                            # Add expression
                            add_expr = AddExpressionItem()
                            add_expr.expression_name = target_name
                            add_expr.custom_shape = True
                            add_expr.side = get_side(target_name)
                            add_expr.execute()
        
        return True


class MoveExpressionItem:
    """Move an expression in the list and update animation frames."""
    
    name = "MoveExpressionItem"
    label = "Move Expression"
    
    def __init__(self, direction: str = 'UP'):
        self.direction = direction  # 'UP' or 'DOWN'
    
    def execute(self):
        """Move expression item."""
        if not cmds.objExists("faceit_expression_data"):
            return False
        
        current_idx = cmds.getAttr("faceit_expression_data.current_index") or 0
        
        names_str = cmds.getAttr("faceit_expression_data.names") or ""
        frames_str = cmds.getAttr("faceit_expression_data.frames") or ""
        
        names = names_str.split(',') if names_str else []
        frames = [int(x) for x in frames_str.split(',')] if frames_str else []
        
        if current_idx < 0 or current_idx >= len(names):
            return False
        
        # Calculate new index
        if self.direction == 'UP':
            new_idx = current_idx - 1
        else:
            new_idx = current_idx + 1
        
        if new_idx < 0 or new_idx >= len(names):
            return False
        
        # Swap items
        names[current_idx], names[new_idx] = names[new_idx], names[current_idx]
        frames[current_idx], frames[new_idx] = frames[new_idx], frames[current_idx]
        
        # Save data
        cmds.setAttr("faceit_expression_data.names", ",".join(names), type="string")
        cmds.setAttr("faceit_expression_data.frames", ",".join(frames), type="string")
        cmds.setAttr("faceit_expression_data.current_index", new_idx)
        
        # Update animation frames in all actions
        self._update_action_frames(current_idx, new_idx, frames[current_idx], frames[new_idx])
        
        return True
    
    def _update_action_frames(self, old_idx: int, new_idx: int, old_frame: int, new_frame: int):
        """Update frame numbers in animation actions."""
        rig = get_faceit_armature()
        if not rig:
            return
        
        # Get animation data
        anim_curves = cmds.listAnimCurves(rig) or []
        for curve in anim_curves:
            # Get keyframes
            keyframes = cmds.keyframe(curve, query=True, timeChange=True) or []
            key_values = cmds.keyframe(curve, query=True, valueChange=True) or []
            
            for i, (t, v) in enumerate(zip(keyframes, key_values)):
                if t == old_frame:
                    cmds.keyframe(curve, edit=True, time=(t,), absoluteTime=True, timeChange=new_frame, index=i)
                elif t == new_frame:
                    cmds.keyframe(curve, edit=True, time=(t,), absoluteTime=True, timeChange=old_frame, index=i)


class AppendActionToFaceitRig:
    """Load expressions from a .face file to the Faceit rig."""
    
    name = "AppendActionToFaceitRig"
    label = "Load Faceit Expressions"
    
    EXPRESSION_PRESETS = {
        'ARKIT': "arkit_expressions.face",
        'TONGUE': "tongue_expressions.face",
        'PHONEMES': "phoneme_expressions.face",
        'A2F': "a2f_46_expressions.face",
    }
    
    def __init__(self):
        self.expressions_type = 'ARKIT'
        self.load_custom_path = False
        self.load_method = 'APPEND'  # 'APPEND' or 'OVERWRITE'
        self.filepath = ""
        self.scale_method = 'AUTO'  # 'AUTO' or 'OVERWRITE'
        self.auto_scale_method = 'GLOBAL'  # 'GLOBAL' or 'AVERAGE'
        self.auto_scale_eyes = True
        self.new_action_scale = [1.0, 1.0, 1.0]
        self.auto_scale_anime_eyes = False
        self.apply_existing_corrective_shape_keys = True
        self.convert_animation_to_new_rigify = False
        self.is_new_rigify_rig = False
        self.rig_type = 'FACEIT'
    
    def execute(self):
        """Execute expression loading."""
        rig = get_faceit_armature()
        if not rig:
            cmds.warning("No Faceit armature found")
            return False
        
        # Determine file path
        if self.load_custom_path:
            if not os.path.isfile(self.filepath):
                cmds.warning(f"File not found: {self.filepath}")
                return False
        else:
            # Use preset path
            preset_dir = self._get_preset_dir()
            self.filepath = os.path.join(preset_dir, self.EXPRESSION_PRESETS[self.expressions_type])
            if not os.path.isfile(self.filepath):
                cmds.warning(f"Preset file not found: {self.filepath}")
                return False
        
        # Load expression data
        expression_data, rest_pose, action_data, eye_dimensions = self._load_expression_file()
        if not expression_data:
            cmds.warning("Failed to load expression data")
            return False
        
        # Clear existing expressions if overwriting
        if self.load_method == 'OVERWRITE':
            self._clear_expressions()
        
        # Create new animation for expressions
        new_action = self._create_expression_action(rest_pose, action_data)
        
        # Scale action to rig dimensions
        if self.scale_method == 'AUTO':
            self._auto_scale_action(new_action, rest_pose)
        elif self.scale_method == 'OVERWRITE':
            self._manual_scale_action(new_action)
        
        # Scale eye animation if needed
        if eye_dimensions and self.auto_scale_eyes:
            self._scale_eye_animation(rig, eye_dimensions, new_action)
        
        if self.auto_scale_anime_eyes:
            self._scale_eye_look_animation(rig, scale_factor=0.45, action=new_action)
        
        # Add expressions to list
        self._add_expressions_to_list(expression_data)
        
        return True
    
    def _get_preset_dir(self) -> str:
        """Get the directory containing expression presets."""
        # This would be the path to the resources folder
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(current_dir, "resources", "presets")
    
    def _load_expression_file(self):
        """Load expression data from .face file."""
        try:
            with open(self.filepath, 'r') as f:
                data = json.load(f)
            
            expressions = data.get("expressions", {})
            rest_pose = data.get("rest_pose", {})
            action = data.get("action", {})
            eye_dimensions = data.get("eye_dimensions", [])
            
            return expressions, rest_pose, action, eye_dimensions
        except Exception as e:
            cmds.warning(f"Error loading expression file: {str(e)}")
            return {}, {}, [], []
    
    def _clear_expressions(self):
        """Clear all existing expressions."""
        if cmds.objExists("faceit_expression_data"):
            cmds.setAttr("faceit_expression_data.names", "", type="string")
            cmds.setAttr("faceit_expression_data.frames", "", type="string")
            cmds.setAttr("faceit_expression_data.sides", "", type="string")
            cmds.setAttr("faceit_expression_data.procedural", "", type="string")
            cmds.setAttr("faceit_expression_data.current_index", -1)
    
    def _create_expression_action(self, rest_pose: dict, action_data: dict) -> str:
        """Create a new action with expression keyframes."""
        rig = get_faceit_armature()
        if not rig:
            return ""
        
        action_name = "faceit_shape_action"
        
        # Remove existing action if overwriting
        if self.load_method == 'OVERWRITE' and cmds.objExists(action_name):
            cmds.delete(action_name)
        
        # Create new action
        if not cmds.objExists(action_name):
            # Create action node
            action = cmds.createNode("animCurveUU", name=action_name)
        
        # Set as current action
        cmds.setAttr(f"{rig}.currentAction", action_name, type="string")
        
        # Add keyframes from action data
        for dp, channel_data in action_data.items():
            # Parse bone name from data path
            bone_name = dp.split('"')[1] if '"' in dp else dp.split('.')[0]
            
            # Get bone's transform attribute
            attr = self._get_transform_attribute(dp)
            
            # Add keyframes
            for channel_idx, keyframe_data in channel_data.items():
                channel_idx = int(channel_idx)
                for frame, value in keyframe_data:
                    cmds.setKeyframe(bone_name, attribute=attr, t=frame, v=value, index=channel_idx)
        
        return action_name
    
    def _get_transform_attribute(self, data_path: str) -> str:
        """Get Maya transform attribute from Blender data path."""
        if 'location' in data_path:
            return 'translate'
        elif 'rotation' in data_path:
            return 'rotate'
        elif 'scale' in data_path:
            return 'scale'
        return 'translate'
    
    def _auto_scale_action(self, action: str, rest_pose: dict):
        """Auto-scale action to rig dimensions."""
        rig = get_faceit_armature()
        if not rig:
            return
        
        # Get current rig dimensions
        rig_dims = self._get_rig_dimensions()
        import_dims = self._get_import_dimensions(rest_pose)
        
        # Calculate scale factors
        scale_factors = []
        for i in range(3):
            if import_dims[i] != 0:
                scale_factors.append(rig_dims[i] / import_dims[i])
            else:
                scale_factors.append(1.0)
        
        # Apply scaling to animation
        if self.auto_scale_method == 'GLOBAL':
            self._scale_action_global(action, scale_factors)
        else:
            self._scale_action_average(action, scale_factors)
    
    def _get_rig_dimensions(self) -> List[float]:
        """Get dimensions of the Faceit rig."""
        rig = get_faceit_armature()
        if not rig:
            return [1.0, 1.0, 1.0]
        
        # Get control bone positions
        x_vals, y_vals, z_vals = [], [], []
        
        for bone in FACEIT_CTRL_BONES:
            if cmds.objExists(bone):
                pos = cmds.getAttr(f"{bone}.translate")[0]
                x_vals.append(pos[0])
                y_vals.append(pos[1])
                z_vals.append(pos[2])
        
        if not x_vals:
            return [1.0, 1.0, 1.0]
        
        return [
            max(x_vals) - min(x_vals),
            max(y_vals) - min(y_vals),
            max(z_vals) - min(z_vals)
        ]
    
    def _get_import_dimensions(self, rest_pose: dict) -> List[float]:
        """Get dimensions from imported rest pose."""
        x_vals, y_vals, z_vals = [], [], []
        
        for bone_name, pos in rest_pose.items():
            x_vals.append(pos[0])
            y_vals.append(pos[1])
            z_vals.append(pos[2])
        
        if not x_vals:
            return [1.0, 1.0, 1.0]
        
        return [
            max(x_vals) - min(x_vals),
            max(y_vals) - min(y_vals),
            max(z_vals) - min(z_vals)
        ]
    
    def _scale_action_global(self, action: str, scale_factors: List[float]):
        """Scale action using global scale factors."""
        # Get all animation curves in the action
        curves = cmds.listAnimCurves(action) or []
        
        for curve in curves:
            # Check if it's a transform curve
            attr = cmds.getAttr(f"{curve}.attributeName")
            if attr and attr in ['translateX', 'translateY', 'translateZ']:
                idx = ['X', 'Y', 'Z'].index(attr[-1])
                scale = scale_factors[idx]
                
                # Scale keyframe values
                keyframes = cmds.keyframe(curve, query=True, timeChange=True) or []
                values = cmds.keyframe(curve, query=True, valueChange=True) or []
                
                for i, (t, v) in enumerate(zip(keyframes, values)):
                    cmds.keyframe(curve, edit=True, absolute=True, valueChange=v * scale, index=i, time=(t,))
    
    def _scale_action_average(self, action: str, scale_factors: List[float]):
        """Scale action using average scale factor."""
        avg_scale = sum(scale_factors) / 3
        self._scale_action_global(action, [avg_scale, avg_scale, avg_scale])
    
    def _manual_scale_action(self, action: str):
        """Manually scale action using user-specified scale."""
        self._scale_action_global(action, self.new_action_scale)
    
    def _scale_eye_animation(self, rig: str, eye_dimensions: List[float], action: str):
        """Scale eye animation to match rig dimensions."""
        # Get current eye dimensions
        eye_L, eye_R = self._get_eye_dimensions(rig)
        
        if len(eye_dimensions) >= 2:
            scale_L = eye_L / eye_dimensions[0]
            scale_R = eye_R / eye_dimensions[1]
            
            # Scale lid bones
            lid_bones_L = [
                'lid.T.L.003', 'lid.T.L.002', 'lid.T.L.001',
                'lid.B.L.001', 'lid.B.L.002', 'lid.B.L.003'
            ]
            lid_bones_R = [
                'lid.T.R.003', 'lid.T.R.002', 'lid.T.R.001',
                'lid.B.R.001', 'lid.B.R.002', 'lid.B.R.003'
            ]
            
            self._scale_bone_animation(action, lid_bones_L, scale_L)
            self._scale_bone_animation(action, lid_bones_R, scale_R)
    
    def _get_eye_dimensions(self, rig: str) -> Tuple[float, float]:
        """Get eye dimensions from rig."""
        # Get top and bottom lid positions
        def get_eye_height(side: str) -> float:
            top = cmds.getAttr(f"lid.T.{side}.002.translate")[0] if cmds.objExists(f"lid.T.{side}.002") else None
            bot = cmds.getAttr(f"lid.B.{side}.002.translate")[0] if cmds.objExists(f"lid.B.{side}.002") else None
            if top and bot:
                return abs(top[1] - bot[1])
            return 1.0
        
        return get_eye_height('L'), get_eye_height('R')
    
    def _scale_bone_animation(self, action: str, bone_names: List[str], scale_factor: float):
        """Scale animation for specific bones."""
        if scale_factor == 1.0:
            return
        
        for bone_name in bone_names:
            if not cmds.objExists(bone_name):
                continue
            
            # Get animation curves for this bone
            curves = cmds.listAnimCurves(bone_name) or []
            
            for curve in curves:
                attr = cmds.getAttr(f"{curve}.attributeName")
                if attr and attr.startswith('translate'):
                    # Scale translate values
                    keyframes = cmds.keyframe(curve, query=True, timeChange=True) or []
                    values = cmds.keyframe(curve, query=True, valueChange=True) or []
                    
                    for i, (t, v) in enumerate(zip(keyframes, values)):
                        cmds.keyframe(curve, edit=True, absolute=True, valueChange=v * scale_factor, index=i, time=(t,))
    
    def _scale_eye_look_animation(self, rig: str, scale_factor: float, action: str):
        """Scale eye look animation."""
        eye_bones = ["eye.R", "eye.L", "eyes", "eye_common"]
        self._scale_bone_animation(action, eye_bones, scale_factor)
    
    def _add_expressions_to_list(self, expression_data: dict):
        """Add expressions to the scene data."""
        for expr_name, expr_info in expression_data.items():
            add_expr = AddExpressionItem()
            add_expr.expression_name = expr_name
            add_expr.side = expr_info.get('side', 'N')
            add_expr.mirror_name_overwrite = expr_info.get('mirror_name', '')
            add_expr.procedural = expr_info.get('procedural', 'NONE')
            add_expr.execute()


class ForceZeroFrames:
    """Add zero keyframes between expression poses."""
    
    name = "ForceZeroFrames"
    label = "Force Zero Frames"
    
    def execute(self):
        """Add zero keyframes at rest positions."""
        rig = get_faceit_armature()
        if not rig:
            return False
        
        # Get expression frames
        if not cmds.objExists("faceit_expression_data"):
            return False
        
        frames_str = cmds.getAttr("faceit_expression_data.frames") or ""
        frames = [int(x) for x in frames_str.split(',')] if frames_str else []
        
        if not frames:
            return False
        
        # Generate zero frames (between expressions)
        zero_frames = set()
        for frame in frames:
            zero_frames.add(frame - 9)
            zero_frames.add(frame + 1)
        zero_frames = sorted(list(zero_frames))
        
        # Add zero keyframes for all bones
        for bone_name in FACEIT_CTRL_BONES:
            if not cmds.objExists(bone_name):
                continue
            
            # Set neutral transforms
            for attr in ['translate', 'rotate']:
                for i in range(3):
                    cmds.setKeyframe(bone_name, attribute=f"{attr}{['X','Y','Z'][i]}", t=zero_frames[0], v=0)
            
            for attr in ['scale']:
                for i in range(3):
                    cmds.setKeyframe(bone_name, attribute=f"{attr}{['X','Y','Z'][i]}", t=zero_frames[0], v=1)
        
        return True


class ExportExpressionsToJson:
    """Export expressions to .face JSON format."""
    
    name = "ExportExpressionsToJson"
    label = "Export Expressions"
    
    def __init__(self):
        self.filepath = "faceit_expressions.face"
    
    def execute(self):
        """Export expressions to JSON file."""
        rig = get_faceit_armature()
        if not rig:
            cmds.warning("No Faceit armature found")
            return False
        
        # Gather expression data
        expression_data = self._gather_expression_data()
        rest_pose = self._get_rest_pose()
        action_data = self._get_action_data()
        eye_dimensions = self._get_eye_dimensions()
        rig_dimensions = self._get_rig_dimensions()
        
        # Build export data
        export_data = {
            "rig_type": self._get_rig_type(),
            "action_scale": rig_dimensions,
            "eye_dimensions": eye_dimensions,
            "expressions": expression_data,
            "rest_pose": rest_pose,
            "action": action_data
        }
        
        # Write to file
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            cmds.warning(f"Error exporting expressions: {str(e)}")
            return False
    
    def _gather_expression_data(self) -> dict:
        """Gather expression data from scene."""
        if not cmds.objExists("faceit_expression_data"):
            return {}
        
        names_str = cmds.getAttr("faceit_expression_data.names") or ""
        sides_str = cmds.getAttr("faceit_expression_data.sides") or ""
        procedural_str = cmds.getAttr("faceit_expression_data.procedural") or ""
        
        names = names_str.split(',') if names_str else []
        sides = sides_str.split(',') if sides_str else []
        procedural_list = procedural_str.split(',') if procedural_str else []
        
        expr_data = {}
        for i, name in enumerate(names):
            expr_data[name] = {
                'mirror_name': get_mirror_name(sides[i] if i < len(sides) else 'N', name),
                'side': sides[i] if i < len(sides) else 'N',
                'procedural': procedural_list[i] if i < len(procedural_list) else 'NONE'
            }
        
        return expr_data
    
    def _get_rest_pose(self) -> dict:
        """Get rest pose of control bones."""
        rest_pose = {}
        
        for bone_name in FACEIT_CTRL_BONES:
            if cmds.objExists(bone_name):
                # Get bind pose position
                pos = cmds.getAttr(f"{bone_name}.translate")[0]
                rest_pose[bone_name] = list(pos)
        
        return rest_pose
    
    def _get_action_data(self) -> dict:
        """Get animation data from current action."""
        rig = get_faceit_armature()
        if not rig:
            return {}
        
        action_data = {}
        curves = cmds.listAnimCurves(rig) or []
        
        for curve in curves:
            # Get data path and channel
            curve_name = cmds.getAttr(f"{curve}.attributeName") or ""
            bone_name = cmds.getAttr(f"{curve}.objectName") or ""
            
            if not bone_name or bone_name not in FACEIT_CTRL_BONES:
                continue
            
            # Get keyframes
            keyframes = cmds.keyframe(curve, query=True, timeChange=True) or []
            values = cmds.keyframe(curve, query=True, valueChange=True) or []
            
            if not keyframes:
                continue
            
            # Determine data path
            dp = f'pose.bones["{bone_name}"].'
            if 'translate' in curve_name:
                dp += 'location'
            elif 'rotate' in curve_name:
                dp += 'rotation_euler'
            elif 'scale' in curve_name:
                dp += 'scale'
            
            # Get channel index
            channel_idx = 0
            if curve_name.endswith('X'):
                channel_idx = 0
            elif curve_name.endswith('Y'):
                channel_idx = 1
            elif curve_name.endswith('Z'):
                channel_idx = 2
            
            # Add to action data
            if dp not in action_data:
                action_data[dp] = {}
            
            if str(channel_idx) not in action_data[dp]:
                action_data[dp][str(channel_idx)] = []
            
            for t, v in zip(keyframes, values):
                action_data[dp][str(channel_idx)].append([t, v])
        
        return action_data
    
    def _get_eye_dimensions(self) -> List[float]:
        """Get eye dimensions."""
        rig = get_faceit_armature()
        if not rig:
            return [1.0, 1.0]
        
        # Try to get eye dimensions from lid bones
        def get_eye_height(side: str) -> float:
            top = cmds.getAttr(f"lid.T.{side}.002.translate")[0] if cmds.objExists(f"lid.T.{side}.002") else None
            bot = cmds.getAttr(f"lid.B.{side}.002.translate")[0] if cmds.objExists(f"lid.B.{side}.002") else None
            if top and bot:
                return abs(top[1] - bot[1])
            return 1.0
        
        return [get_eye_height('L'), get_eye_height('R')]
    
    def _get_rig_dimensions(self) -> List[float]:
        """Get rig dimensions."""
        return self._get_rig_dimensions()
    
    def _get_rig_type(self) -> str:
        """Get rig type."""
        return 'FACEIT'


class ClearFaceitExpressions:
    """Clear all Faceit expressions."""
    
    name = "ClearFaceitExpressions"
    label = "Clear Expressions"
    
    def __init__(self, keep_corrective_shape_keys: bool = True):
        self.keep_corrective_shape_keys = keep_corrective_shape_keys
    
    def execute(self):
        """Clear all expressions."""
        # Clear expression data
        if cmds.objExists("faceit_expression_data"):
            cmds.setAttr("faceit_expression_data.names", "", type="string")
            cmds.setAttr("faceit_expression_data.frames", "", type="string")
            cmds.setAttr("faceit_expression_data.sides", "", type="string")
            cmds.setAttr("faceit_expression_data.procedural", "", type="string")
            cmds.setAttr("faceit_expression_data.current_index", -1)
        
        # Clear animation actions
        action_names = ["faceit_shape_action", "overwrite_shape_action"]
        for action_name in action_names:
            if cmds.objExists(action_name):
                cmds.delete(action_name)
        
        # Reset rig
        rig = get_faceit_armature()
        if rig:
            # Clear animation data
            cmds.setAttr(f"{rig}.currentAction", "", type="string")
            
            # Reset bone transforms
            for bone_name in FACEIT_CTRL_BONES:
                if cmds.objExists(bone_name):
                    for attr in ['translateX', 'translateY', 'translateZ']:
                        cmds.setAttr(f"{bone_name}.{attr}", 0)
                    for attr in ['rotateX', 'rotateY', 'rotateZ']:
                        cmds.setAttr(f"{bone_name}.{attr}", 0)
                    for attr in ['scaleX', 'scaleY', 'scaleZ']:
                        cmds.setAttr(f"{bone_name}.{attr}", 1)
        
        return True


class RemoveExpressionItem:
    """Remove an expression item."""
    
    name = "RemoveExpressionItem"
    label = "Remove Expression"
    
    def __init__(self, remove_item: str = ""):
        self.remove_item = remove_item
    
    def execute(self):
        """Remove expression item."""
        if not cmds.objExists("faceit_expression_data"):
            return False
        
        names_str = cmds.getAttr("faceit_expression_data.names") or ""
        frames_str = cmds.getAttr("faceit_expression_data.frames") or ""
        sides_str = cmds.getAttr("faceit_expression_data.sides") or ""
        procedural_str = cmds.getAttr("faceit_expression_data.procedural") or ""
        
        names = names_str.split(',') if names_str else []
        frames = [int(x) for x in frames_str.split(',')] if frames_str else []
        sides = sides_str.split(',') if sides_str else []
        procedural_list = procedural_str.split(',') if procedural_str else []
        
        if not names:
            return False
        
        # Find item to remove
        if self.remove_item:
            if self.remove_item in names:
                idx = names.index(self.remove_item)
            else:
                return False
        else:
            current_idx = cmds.getAttr("faceit_expression_data.current_index") or 0
            if current_idx >= len(names):
                return False
            idx = current_idx
        
        frame_to_remove = frames[idx]
        
        # Remove from lists
        names.pop(idx)
        frames.pop(idx)
        sides.pop(idx) if idx < len(sides) else None
        procedural_list.pop(idx) if idx < len(procedural_list) else None
        
        # Shift frames after removal
        for i in range(len(frames)):
            if frames[i] > frame_to_remove:
                frames[i] -= 10
        
        # Save data
        cmds.setAttr("faceit_expression_data.names", ",".join(names), type="string")
        cmds.setAttr("faceit_expression_data.frames", ",".join(frames), type="string")
        cmds.setAttr("faceit_expression_data.sides", ",".join(sides), type="string")
        cmds.setAttr("faceit_expression_data.procedural", ",".join(procedural_list), type="string")
        
        # Update current index
        if cmds.objExists("faceit_expression_data"):
            cmds.setAttr("faceit_expression_data.current_index", min(idx, len(names) - 1))
        
        # Remove animation keyframes
        self._remove_animation_keyframes(frame_to_remove)
        
        return True
    
    def _remove_animation_keyframes(self, frame: int):
        """Remove animation keyframes at specified frame."""
        rig = get_faceit_armature()
        if not rig:
            return
        
        curves = cmds.listAnimCurves(rig) or []
        for curve in curves:
            keyframes = cmds.keyframe(curve, query=True, timeChange=True) or []
            for i, t in enumerate(keyframes):
                if t == frame:
                    cmds.keyframe(curve, edit=True, remove=True, time=(t,))
                    break


class PoseAmplify:
    """Amplify or scale a pose."""
    
    name = "PoseAmplify"
    label = "Amplify Pose"
    
    def __init__(self, expression_index: int = -1, percentage: float = 1.0, selected_bones_only: bool = False):
        self.expression_index = expression_index
        self.percentage = percentage
        self.selected_bones_only = selected_bones_only
    
    def execute(self):
        """Amplify the pose."""
        rig = get_faceit_armature()
        if not rig:
            return False
        
        # Get expression frame
        if self.expression_index != -1:
            names_str = cmds.getAttr("faceit_expression_data.names") or ""
            frames_str = cmds.getAttr("faceit_expression_data.frames") or ""
            names = names_str.split(',') if names_str else []
            frames = [int(x) for x in frames_str.split(',')] if frames_str else []
            
            if self.expression_index < len(frames):
                frame = frames[self.expression_index]
            else:
                return False
        else:
            # Use current timeline
            frame = cmds.currentTime(query=True)
        
        # Get bones to amplify
        bones = FACEIT_CTRL_BONES
        
        if self.selected_bones_only:
            selected = cmds.ls(selection=True, type='transform')
            bones = [b for b in bones if b in selected]
        
        # Amplify transforms
        for bone_name in bones:
            if not cmds.objExists(bone_name):
                continue
            
            # Get current values at frame
            cmds.currentTime(frame)
            
            # Amplify translate
            t = cmds.getAttr(f"{bone_name}.translate")[0]
            if any(abs(v) > 0.01 for v in t):
                t_scaled = [v * self.percentage for v in t]
                cmds.setAttr(f"{bone_name}.translateX", t_scaled[0])
                cmds.setAttr(f"{bone_name}.translateY", t_scaled[1])
                cmds.setAttr(f"{bone_name}.translateZ", t_scaled[2])
                cmds.setKeyframe(bone_name, attribute="translate", t=frame)
            
            # Amplify rotate
            r = cmds.getAttr(f"{bone_name}.rotate")[0]
            if any(abs(v) > 0.01 for v in r):
                r_scaled = [v * self.percentage for v in r]
                cmds.setAttr(f"{bone_name}.rotateX", r_scaled[0])
                cmds.setAttr(f"{bone_name}.rotateY", r_scaled[1])
                cmds.setAttr(f"{bone_name}.rotateZ", r_scaled[2])
                cmds.setKeyframe(bone_name, attribute="rotate", t=frame)
        
        return True


class ResetExpression:
    """Reset expression to its original state."""
    
    name = "ResetExpression"
    label = "Reset Expression"
    
    def __init__(self, expression_to_reset: str = "ALL", remove_corrective: bool = True):
        self.expression_to_reset = expression_to_reset
        self.remove_corrective = remove_corrective
    
    def execute(self):
        """Reset the expression."""
        rig = get_faceit_armature()
        if not rig:
            return False
        
        if not cmds.objExists("faceit_expression_data"):
            return False
        
        names_str = cmds.getAttr("faceit_expression_data.names") or ""
        frames_str = cmds.getAttr("faceit_expression_data.frames") or ""
        names = names_str.split(',') if names_str else []
        frames = [int(x) for x in frames_str.split(',')] if frames_str else []
        
        if self.expression_to_reset == "ALL":
            expression_indices = range(len(names))
        else:
            try:
                idx = int(self.expression_to_reset)
                expression_indices = [idx]
            except:
                if self.expression_to_reset in names:
                    expression_indices = [names.index(self.expression_to_reset)]
                else:
                    return False
        
        # Reset each expression
        for idx in expression_indices:
            if idx < len(frames):
                frame = frames[idx]
                self._reset_frame(rig, frame)
        
        return True
    
    def _reset_frame(self, rig: str, frame: int):
        """Reset all transforms at a specific frame."""
        # Get animation curves
        curves = cmds.listAnimCurves(rig) or []
        
        for curve in curves:
            # Find keyframe at this frame
            keyframes = cmds.keyframe(curve, query=True, timeChange=True) or []
            for i, t in enumerate(keyframes):
                if t == frame:
                    # Get default value for this attribute
                    attr = cmds.getAttr(f"{curve}.attributeName") or ""
                    if 'scale' in attr:
                        default_val = 1.0
                    else:
                        default_val = 0.0
                    
                    # Set default value
                    cmds.keyframe(curve, edit=True, absolute=True, valueChange=default_val, index=i, time=(t,))
                    break


class ProceduralEyeBlinks:
    """Create procedural eye blink animation."""
    
    name = "ProceduralEyeBlinks"
    label = "Procedural Eye Blinks"
    
    def __init__(self, side: str = 'N', anim_mode: str = 'REPLACE', is_new_rigify: bool = False):
        self.side = side
        self.anim_mode = anim_mode
        self.is_new_rigify = is_new_rigify
    
    def execute(self):
        """Create procedural eye blink animation."""
        rig = get_faceit_armature()
        if not rig:
            return False
        
        # Get current expression frame
        if cmds.objExists("faceit_expression_data"):
            current_idx = cmds.getAttr("faceit_expression_data.current_index") or 0
            frames_str = cmds.getAttr("faceit_expression_data.frames") or ""
            frames = [int(x) for x in frames_str.split(',')] if frames_str else []
            
            if current_idx < len(frames):
                frame = frames[current_idx]
            else:
                frame = cmds.currentTime(query=True)
        else:
            frame = cmds.currentTime(query=True)
        
        # Create eye blink animation
        side = self.side
        
        if side == 'L' or side == 'N':
            self._create_eye_blink(rig, 'L', frame)
        if side == 'R' or side == 'N':
            self._create_eye_blink(rig, 'R', frame)
        
        return True
    
    def _create_eye_blink(self, rig: str, side: str, frame: int):
        """Create eye blink for one side."""
        # Get lid bones
        top_lid_bones = [
            f"lid.T.{side}.001",
            f"lid.T.{side}.002",
            f"lid.T.{side}.003"
        ]
        bot_lid_bones = [
            f"lid.B.{side}.001",
            f"lid.B.{side}.002",
            f"lid.B.{side}.003"
        ]
        
        # Get mid lid positions at neutral
        for bone_name in top_lid_bones:
            if cmds.objExists(bone_name):
                pos = cmds.getAttr(f"{bone_name}.translate")[0]
                # Set keyframes for blink
                cmds.setKeyframe(bone_name, attribute="translateY", t=frame - 9, v=pos[1])
                cmds.setKeyframe(bone_name, attribute="translateY", t=frame, v=pos[1] - 0.3)
                cmds.setKeyframe(bone_name, attribute="translateY", t=frame + 1, v=pos[1])
        
        for bone_name in bot_lid_bones:
            if cmds.objExists(bone_name):
                pos = cmds.getAttr(f"{bone_name}.translate")[0]
                cmds.setKeyframe(bone_name, attribute="translateY", t=frame - 9, v=pos[1])
                cmds.setKeyframe(bone_name, attribute="translateY", t=frame, v=pos[1] + 0.1)
                cmds.setKeyframe(bone_name, attribute="translateY", t=frame + 1, v=pos[1])


class ProceduralMouthClose:
    """Create procedural mouth close animation."""
    
    name = "ProceduralMouthClose"
    label = "Procedural Mouth Close"
    
    def __init__(self, jaw_open_expression: str = "jawOpen", mouth_close_expression: str = "mouthClose", is_new_rigify: bool = False):
        self.jaw_open_expression = jaw_open_expression
        self.mouth_close_expression = mouth_close_expression
        self.is_new_rigify = is_new_rigify
    
    def execute(self):
        """Create procedural mouth close animation."""
        rig = get_faceit_armature()
        if not rig:
            return False
        
        if not cmds.objExists("faceit_expression_data"):
            return False
        
        names_str = cmds.getAttr("faceit_expression_data.names") or ""
        frames_str = cmds.getAttr("faceit_expression_data.frames") or ""
        names = names_str.split(',') if names_str else []
        frames = [int(x) for x in frames_str.split(',')] if frames_str else []
        
        # Find jaw open and mouth close frames
        jaw_frame = None
        mouth_frame = None
        
        for i, name in enumerate(names):
            if name == self.jaw_open_expression:
                jaw_frame = frames[i] if i < len(frames) else None
            elif name == self.mouth_close_expression:
                mouth_frame = frames[i] if i < len(frames) else None
        
        if jaw_frame is None or mouth_frame is None:
            cmds.warning("Could not find jaw open or mouth close expressions")
            return False
        
        # Copy jaw open pose to mouth close with mouth lock
        self._copy_jaw_to_mouth(rig, jaw_frame, mouth_frame)
        
        return True
    
    def _copy_jaw_to_mouth(self, rig: str, from_frame: int, to_frame: int):
        """Copy jaw pose to mouth close position."""
        # Get jaw master transforms at from_frame
        cmds.currentTime(from_frame)
        jaw_translate = cmds.getAttr("jaw_master.translate")[0]
        jaw_rotate = cmds.getAttr("jaw_master.rotate")[0]
        
        # Set jaw at to_frame
        cmds.currentTime(to_frame)
        
        # Set jaw keyframe
        cmds.setAttr("jaw_master.translateX", jaw_translate[0])
        cmds.setAttr("jaw_master.translateY", jaw_translate[1])
        cmds.setAttr("jaw_master.translateZ", jaw_translate[2])
        cmds.setKeyframe("jaw_master", attribute="translate", t=to_frame)
        
        cmds.setAttr("jaw_master.rotateX", jaw_rotate[0])
        cmds.setAttr("jaw_master.rotateY", jaw_rotate[1])
        cmds.setAttr("jaw_master.rotateZ", jaw_rotate[2])
        cmds.setKeyframe("jaw_master", attribute="rotate", t=to_frame)


class NewAction:
    """Create a new animation action."""
    
    name = "NewAction"
    label = "New Action"
    
    def __init__(self, action_name: str = "", use_fake_user: bool = True):
        self.action_name = action_name
        self.use_fake_user = use_fake_user
    
    def execute(self):
        """Create a new action."""
        if not self.action_name:
            rig = get_faceit_armature()
            if rig:
                self.action_name = f"{rig}_Action"
            else:
                self.action_name = "FaceitAction"
        
        # Check if action already exists
        if cmds.objExists(self.action_name):
            if cmds.nodeType(self.action_name) == 'animCurve':
                cmds.delete(self.action_name)
        
        # Create new action
        cmds.createNode("animCurveUU", name=self.action_name)
        
        # Set as current action
        rig = get_faceit_armature()
        if rig:
            cmds.setAttr(f"{rig}.currentAction", self.action_name, type="string")
        
        return True


class PopulateAction:
    """Populate action to all Faceit objects."""
    
    name = "PopulateAction"
    label = "Activate Action"
    
    def __init__(self, action_name: str = "", remove_action: bool = False):
        self.action_name = action_name
        self.remove_action = remove_action
    
    def execute(self):
        """Populate action to all Faceit objects."""
        faceit_objects = get_faceit_objects()
        
        if self.remove_action:
            for obj in faceit_objects:
                if cmds.objExists(f"{obj}.currentAction"):
                    cmds.setAttr(f"{obj}.currentAction", "", type="string")
            return True
        
        if not self.action_name or not cmds.objExists(self.action_name):
            cmds.warning("Action not found")
            return False
        
        for obj in faceit_objects:
            if cmds.objExists(obj):
                # Set action on object
                cmds.setAttr(f"{obj}.currentAction", self.action_name, type="string")
                
                # If it's a mesh with blend shapes, update blend shape weights
                if cmds.nodeType(obj) == 'mesh' or cmds.listRelatives(obj, shapes=True):
                    self._update_blend_shapes(obj)
        
        return True
    
    def _update_blend_shapes(self, obj: str):
        """Update blend shape weights for an object."""
        history = cmds.listHistory(obj, pruneDagObjects=True, interestLevel=2) or []
        for node in history:
            if cmds.nodeType(node) == 'blendShape':
                # Force update of blend shape weights
                weights = cmds.listAttr(f"{node}.weight", multi=True) or []
                for weight_attr in weights:
                    value = cmds.getAttr(f"{node}.{weight_attr}")
                    cmds.setAttr(f"{node}.{weight_attr}", value)


class SetBodyBindPose:
    """Set the current pose as the bind pose for the body."""
    
    name = "SetBodyBindPose"
    label = "Reset Pose"
    
    def __init__(self, rig_name: str = ""):
        self.rig_name = rig_name
    
    def execute(self):
        """Set body bind pose."""
        if self.rig_name and cmds.objExists(self.rig_name):
            rig = self.rig_name
        else:
            rig = get_faceit_armature()
            if not rig:
                return False
        
        # Clear animation
        cmds.setAttr(f"{rig}.currentAction", "", type="string")
        
        # Reset all bones
        bones = cmds.ls(f"{rig}.bones", type='joint') or []
        for bone in bones:
            for attr in ['translateX', 'translateY', 'translateZ']:
                cmds.setAttr(f"{bone}.{attr}", 0)
            for attr in ['rotateX', 'rotateY', 'rotateZ']:
                cmds.setAttr(f"{bone}.{attr}", 0)
            for attr in ['scaleX', 'scaleY', 'scaleZ']:
                cmds.setAttr(f"{bone}.{attr}", 1)
        
        return True


# ============================================================
# Register Functions for Maya
# ============================================================

def register_animation_operators():
    """Register all animation operators with Maya."""
    # In Maya, operators are not registered the same way as Blender
    # Instead, we expose them as functions or commands
    
    # Create a dictionary of available operators
    operators = {
        'add_expression': AddExpressionItem,
        'reset_constraints': ResetBoneConstraints,
        'mirror_copy': MirrorCopyExpression,
        'empty_from_blendshapes': EmptyExpressionsFromBlendShapes,
        'move_expression': MoveExpressionItem,
        'append_expression': AppendActionToFaceitRig,
        'force_zero_frames': ForceZeroFrames,
        'export_expressions': ExportExpressionsToJson,
        'clear_expressions': ClearFaceitExpressions,
        'remove_expression': RemoveExpressionItem,
        'pose_amplify': PoseAmplify,
        'reset_expression': ResetExpression,
        'procedural_blinks': ProceduralEyeBlinks,
        'procedural_mouth': ProceduralMouthClose,
        'new_action': NewAction,
        'populate_action': PopulateAction,
        'set_bind_pose': SetBodyBindPose,
    }
    
    return operators


# Expose functions for Maya commands
def faceit_add_expression(*args, **kwargs):
    """Maya command: faceitAddExpression"""
    op = AddExpressionItem()
    # Set properties from kwargs
    for key, value in kwargs.items():
        if hasattr(op, key):
            setattr(op, key, value)
    return op.execute()


def faceit_append_expressions(*args, **kwargs):
    """Maya command: faceitAppendExpressions"""
    op = AppendActionToFaceitRig()
    for key, value in kwargs.items():
        if hasattr(op, key):
            setattr(op, key, value)
    return op.execute()


# Create Maya commands
def create_faceit_commands():
    """Create Maya commands for Faceit operations."""
    # This would be called during plugin initialization
    pass