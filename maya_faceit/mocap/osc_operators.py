# osc_operators.py
# Maya Faceit Plugin - OSC Operators
# Converted from Blender to Maya Python 3.11

"""
OSC operators for Faceit Maya plugin.
Handles starting, stopping, and managing OSC connections.
"""

import maya.cmds as cmds # type: ignore
import socket
import time
from typing import List, Dict, Optional, Any

from .mocap_base import MocapImporterBase
from .mocap_importers import OSCLiveAnimator
from .osc_receiver import QueueManager, Receiver, osc_queue
from ..core import faceit_utils as futils
from ..core import shape_key_utils
from ..ctrl_rig import control_rig_utils as ctrl_utils

# ============================================================
# Global State
# ============================================================

queue_mgr: QueueManager = QueueManager()
receiver: Receiver = Receiver(queue_mgr)
live_animator: OSCLiveAnimator = OSCLiveAnimator()
reconnect_ctrl_rig: bool = False

# Head transform state
head_base_rotation = None
head_base_location = None


def get_head_base_transform() -> tuple:
    """Get the base head transform."""
    return head_base_rotation, head_base_location


# ============================================================
# Receiver Start Operator
# ============================================================

class ReceiverStart:
    """
    Start receiving animation data from the given connection.
    """
    
    name = "ReceiverStart"
    label = "Start Receiver"
    
    def execute(self, context: Any = None) -> str:
        """Execute the operator."""
        global receiver, live_animator, reconnect_ctrl_rig
        
        # Save scene state
        state_dict = futils.save_scene_state()
        
        # Clear animation targets
        live_animator.clear_animation_targets()
        live_animator.init_new_recording()
        
        # Get scene settings
        scene = context.scene if hasattr(context, 'scene') else None
        if not scene:
            cmds.warning("No scene context available")
            return {'CANCELLED'}
        
        # Get animation settings from scene data
        animate_loc = self._get_scene_setting("osc_animate_head_location", False)
        animate_rot = self._get_scene_setting("osc_animate_head_rotation", True)
        animate_shapes = self._get_scene_setting("osc_animate_shapes", True)
        
        if not (animate_loc or animate_rot or animate_shapes):
            cmds.warning("You need to enable at least one type of motion.")
            return {'CANCELLED'}
        
        # Configure live animator
        live_animator.set_rotation_units(self._get_scene_setting("osc_rotation_units", "DEG"))
        live_animator.flip_animation = self._get_scene_setting("osc_flip_animation", False)
        live_animator.animate_shapes = animate_shapes
        live_animator.animate_head_location = animate_loc
        live_animator.animate_head_rotation = animate_rot
        
        # Setup shape animation targets
        if animate_shapes:
            self._setup_shape_targets()
        
        # Setup head animation targets
        if animate_loc or animate_rot:
            self._setup_head_targets()
        
        # Stop any playing animation
        cmds.play(animation=False)
        
        # Start receiver
        try:
            address = self._get_scene_setting("osc_address", "127.0.0.1")
            port = self._get_scene_setting("osc_port", 7777)
            receiver.start(address, port)
        except OSError as e:
            cmds.warning(f"Socket error: {str(e)}")
            return self.cancel(context)
        
        # Set enabled flag
        self._set_scene_setting("osc_receiver_enabled", True)
        
        # Restore scene state
        futils.restore_scene_state(state_dict)
        
        cmds.warning("OSC Receiver started")
        return {'FINISHED'}
    
    def cancel(self, context: Any = None) -> str:
        """Cancel the operation."""
        global receiver
        receiver.stop()
        queue_mgr.reset()
        return {'CANCELLED'}
    
    def _get_scene_setting(self, key: str, default: Any) -> Any:
        """Get a scene setting."""
        if not cmds.objExists("faceit_core_data"):
            return default
        
        if cmds.attributeQuery(key, node="faceit_core_data", exists=True):
            attr_type = cmds.attributeQuery(key, node="faceit_core_data", attributeType=True)
            if attr_type == 'bool':
                return cmds.getAttr(f"faceit_core_data.{key}")
            elif attr_type == 'long':
                return cmds.getAttr(f"faceit_core_data.{key}")
            elif attr_type == 'float':
                return cmds.getAttr(f"faceit_core_data.{key}")
            elif attr_type == 'string':
                return cmds.getAttr(f"faceit_core_data.{key}") or default
        
        return default
    
    def _set_scene_setting(self, key: str, value: Any) -> None:
        """Set a scene setting."""
        if not cmds.objExists("faceit_core_data"):
            cmds.createNode("transform", name="faceit_core_data")
        
        if not cmds.attributeQuery(key, node="faceit_core_data", exists=True):
            if isinstance(value, bool):
                cmds.addAttr("faceit_core_data", ln=key, attributeType="bool")
            elif isinstance(value, int):
                cmds.addAttr("faceit_core_data", ln=key, attributeType="long")
            elif isinstance(value, float):
                cmds.addAttr("faceit_core_data", ln=key, attributeType="float")
            else:
                cmds.addAttr("faceit_core_data", ln=key, dt="string")
        
        cmds.setAttr(f"faceit_core_data.{key}", value)
    
    def _setup_shape_targets(self) -> None:
        """Setup shape animation targets."""
        global reconnect_ctrl_rig
        
        ctrl_rig = self._get_control_rig()
        reconnect_ctrl_rig = False
        
        if ctrl_rig:
            if ctrl_utils.is_control_rig_connected(ctrl_rig):
                if self._get_scene_setting("auto_disconnect_ctrl_rig", True):
                    objects = ctrl_utils.get_crig_objects_list(ctrl_rig)
                    target_shapes = self._get_crig_targets(ctrl_rig)
                    
                    # Remove control drivers
                    self._remove_control_drivers()
                    reconnect_ctrl_rig = True
        
        if not reconnect_ctrl_rig:
            objects = futils.get_faceit_objects_list()
            target_shapes = self._get_retarget_shapes()
        
        if not objects:
            cmds.warning("You need to register the target objects in Setup tab or select a valid control rig.")
        elif not target_shapes:
            cmds.warning("You need to populate the ARKit target shapes list in the Shapes tab or select a valid control rig.")
        
        live_animator.set_shape_targets(
            objects=objects,
            retarget_shapes=target_shapes
        )
    
    def _setup_head_targets(self) -> None:
        """Setup head animation targets."""
        global head_base_rotation, head_base_location
        
        head_loc_multiplier = self._get_scene_setting("osc_head_location_multiplier", 1.0)
        head_obj = self._get_scene_setting("head_target_object", "")
        head_bone_name = self._get_scene_setting("head_sub_target", "")
        
        if head_obj and cmds.objExists(head_obj):
            if cmds.nodeType(head_obj) == 'joint':
                cmds.select(head_obj)
                cmds.setAttr(f"{head_obj}.visibility", 1)
            else:
                # Store base transform
                if cmds.attributeQuery("rotateOrder", node=head_obj, exists=True):
                    head_base_rotation = cmds.getAttr(f"{head_obj}.rotate")[0]
                head_base_location = cmds.xform(head_obj, query=True, worldSpace=True, translation=True)
        
        live_animator.set_head_targets(
            head_obj=head_obj,
            head_bone_name=head_bone_name,
            head_loc_mult=head_loc_multiplier,
        )
    
    def _get_control_rig(self) -> Optional[str]:
        """Get the control rig."""
        return futils.get_faceit_control_armature()
    
    def _get_crig_targets(self, ctrl_rig: str) -> List[Dict]:
        """Get control rig targets."""
        if not cmds.objExists(ctrl_rig):
            return []
        
        if not cmds.attributeQuery("faceit_crig_targets", node=ctrl_rig, exists=True):
            return []
        
        targets_str = cmds.getAttr(f"{ctrl_rig}.faceit_crig_targets") or "{}"
        try:
            import json
            return json.loads(targets_str)
        except:
            return []
    
    def _get_retarget_shapes(self) -> List[Dict]:
        """Get retarget shapes from scene."""
        if not cmds.objExists("faceit_core_data"):
            return []
        
        if cmds.attributeQuery("arkit_retarget_shapes", node="faceit_core_data", exists=True):
            shapes_str = cmds.getAttr("faceit_core_data.arkit_retarget_shapes") or "{}"
            try:
                import json
                return json.loads(shapes_str)
            except:
                return []
        
        return []
    
    def _remove_control_drivers(self) -> None:
        """Remove control drivers."""
        # Implementation to remove drivers
        pass


# ============================================================
# Receiver Stop Operator
# ============================================================

class ReceiverStop:
    """
    Stop the active live session.
    """
    
    name = "ReceiverStop"
    label = "Stop Receiver"
    
    def execute(self, context: Any = None) -> str:
        """Execute the operator."""
        global reconnect_ctrl_rig
        
        if not osc_queue:
            cmds.warning("No recorded data found.")
            self._reset_expression_values()
            self._reset_head_pose()
        
        stop_receiver()
        
        ctrl_rig = self._get_control_rig()
        if ctrl_rig:
            if self._get_scene_setting("auto_disconnect_ctrl_rig", True) and reconnect_ctrl_rig:
                self._setup_control_drivers()
        
        return {'FINISHED'}
    
    def _reset_expression_values(self) -> None:
        """Reset expression values to default."""
        faceit_objects = futils.get_faceit_objects_list()
        
        for obj in faceit_objects:
            if shape_key_utils.has_shape_keys(obj):
                blend_node = shape_key_utils.get_blend_shape_node(obj)
                if blend_node:
                    targets = shape_key_utils.get_blend_shape_targets(obj)
                    for target in targets:
                        cmds.setAttr(f"{blend_node}.{target}", 0)
    
    def _reset_head_pose(self) -> None:
        """Reset head pose."""
        head_obj = self._get_scene_setting("head_target_object", "")
        if head_obj and cmds.objExists(head_obj):
            # Reset rotation
            for attr in ['rotateX', 'rotateY', 'rotateZ']:
                cmds.setAttr(f"{head_obj}.{attr}", 0)
            
            # Reset location
            for attr in ['translateX', 'translateY', 'translateZ']:
                cmds.setAttr(f"{head_obj}.{attr}", 0)
    
    def _get_control_rig(self) -> Optional[str]:
        """Get the control rig."""
        return futils.get_faceit_control_armature()
    
    def _get_scene_setting(self, key: str, default: Any) -> Any:
        """Get a scene setting."""
        if not cmds.objExists("faceit_core_data"):
            return default
        
        if cmds.attributeQuery(key, node="faceit_core_data", exists=True):
            attr_type = cmds.attributeQuery(key, node="faceit_core_data", attributeType=True)
            if attr_type == 'bool':
                return cmds.getAttr(f"faceit_core_data.{key}")
            elif attr_type == 'long':
                return cmds.getAttr(f"faceit_core_data.{key}")
            elif attr_type == 'float':
                return cmds.getAttr(f"faceit_core_data.{key}")
            elif attr_type == 'string':
                return cmds.getAttr(f"faceit_core_data.{key}") or default
        
        return default
    
    def _setup_control_drivers(self) -> None:
        """Setup control drivers."""
        # Implementation to setup drivers
        pass


# ============================================================
# Import Live Mocap Operator
# ============================================================

class ImportLiveMocap(MocapImporterBase):
    """
    Import the recorded data into a Blender Action.
    """
    
    name = "ImportLiveMocap"
    label = "Import OSC Recording"
    
    def __init__(self):
        super().__init__()
        self.filename = ""
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return True
    
    def invoke(self, context: Any = None) -> str:
        """Invoke the operator."""
        global reconnect_ctrl_rig
        
        self._get_engine_specific_settings()
        
        if not osc_queue:
            cmds.warning("No recorded data found.")
            return {'CANCELLED'}
        
        faceit_objects = futils.get_faceit_objects_list()
        if not faceit_objects:
            cmds.warning("You need to register the character meshes in the setup tab.")
        
        if futils.get_faceit_control_armature():
            if reconnect_ctrl_rig:
                self.bake_to_control_rig = True
            self.can_bake_control_rig = True
        else:
            self.can_bake_control_rig = False
        
        self.new_action_name = "LiveRecording"
        
        # In Maya, we'd show a dialog
        return self.execute(context)
    
    def _get_engine_specific_settings(self) -> None:
        """Get engine-specific settings."""
        self.animate_shapes = live_animator.animate_shapes
        self.animate_head_rotation = live_animator.animate_head_rotation
        self.animate_head_location = live_animator.animate_head_location
        self.can_import_head_rotation = self._get_scene_setting("osc_animate_head_rotation", True)
        self.can_import_head_location = self._get_scene_setting("osc_animate_head_location", False)
        self.use_region_filter = live_animator.use_region_filter
        self.flip_animation = live_animator.flip_animation
        self.filename = ""
    
    def _get_mocap_importer(self):
        """Get the mocap importer."""
        return live_animator
    
    def _get_raw_animation_data(self) -> Any:
        """Return the raw animation data."""
        return osc_queue
    
    def _get_scene_setting(self, key: str, default: Any) -> Any:
        """Get a scene setting."""
        if not cmds.objExists("faceit_core_data"):
            return default
        
        if cmds.attributeQuery(key, node="faceit_core_data", exists=True):
            attr_type = cmds.attributeQuery(key, node="faceit_core_data", attributeType=True)
            if attr_type == 'bool':
                return cmds.getAttr(f"faceit_core_data.{key}")
            elif attr_type == 'long':
                return cmds.getAttr(f"faceit_core_data.{key}")
            elif attr_type == 'float':
                return cmds.getAttr(f"faceit_core_data.{key}")
            elif attr_type == 'string':
                return cmds.getAttr(f"faceit_core_data.{key}") or default
        
        return default


# ============================================================
# Clear Live Data Operator
# ============================================================

class ClearLiveData:
    """
    Clear the recorded data before starting a new recording.
    """
    
    name = "ClearLiveData"
    label = "Clear Recorded Data"
    
    def execute(self, context: Any = None) -> str:
        """Execute the operator."""
        clear_data()
        self._reset_expression_values()
        self._reset_head_pose()
        return {'FINISHED'}
    
    def _reset_expression_values(self) -> None:
        """Reset expression values to default."""
        faceit_objects = futils.get_faceit_objects_list()
        
        for obj in faceit_objects:
            if shape_key_utils.has_shape_keys(obj):
                blend_node = shape_key_utils.get_blend_shape_node(obj)
                if blend_node:
                    targets = shape_key_utils.get_blend_shape_targets(obj)
                    for target in targets:
                        cmds.setAttr(f"{blend_node}.{target}", 0)
    
    def _reset_head_pose(self) -> None:
        """Reset head pose."""
        head_obj = self._get_scene_setting("head_target_object", "")
        if head_obj and cmds.objExists(head_obj):
            for attr in ['rotateX', 'rotateY', 'rotateZ']:
                cmds.setAttr(f"{head_obj}.{attr}", 0)
            for attr in ['translateX', 'translateY', 'translateZ']:
                cmds.setAttr(f"{head_obj}.{attr}", 0)
    
    def _get_scene_setting(self, key: str, default: Any) -> Any:
        """Get a scene setting."""
        if not cmds.objExists("faceit_core_data"):
            return default
        
        if cmds.attributeQuery(key, node="faceit_core_data", exists=True):
            attr_type = cmds.attributeQuery(key, node="faceit_core_data", attributeType=True)
            if attr_type == 'bool':
                return cmds.getAttr(f"faceit_core_data.{key}")
            elif attr_type == 'long':
                return cmds.getAttr(f"faceit_core_data.{key}")
            elif attr_type == 'float':
                return cmds.getAttr(f"faceit_core_data.{key}")
            elif attr_type == 'string':
                return cmds.getAttr(f"faceit_core_data.{key}") or default
        
        return default


# ============================================================
# Receiver Cancel Operator
# ============================================================

class ReceiverCancel:
    """
    Cancel the receiver without saving data.
    """
    
    name = "ReceiverCancel"
    label = "Cancel Receiver"
    
    def execute(self, context: Any = None) -> str:
        """Execute the operator."""
        if self._is_receiver_enabled():
            cmds.warning("Cancelled Receiver without writing keyframes.")
        
        stop_receiver()
        cancel_recording()
        
        # Refresh UI
        self._refresh_ui()
        
        return {'FINISHED'}
    
    def _is_receiver_enabled(self) -> bool:
        """Check if receiver is enabled."""
        if not cmds.objExists("faceit_core_data"):
            return False
        
        if cmds.attributeQuery("osc_receiver_enabled", node="faceit_core_data", exists=True):
            return cmds.getAttr("faceit_core_data.osc_receiver_enabled")
        
        return False
    
    def _refresh_ui(self) -> None:
        """Refresh UI."""
        cmds.refresh()


# ============================================================
# Global Functions
# ============================================================

def stop_receiver() -> None:
    """Stop the receiver."""
    receiver.stop()
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery("osc_receiver_enabled", node="faceit_core_data", exists=True):
            cmds.setAttr("faceit_core_data.osc_receiver_enabled", False)


def cancel_recording() -> None:
    """Stop the receiver and clear recorded data."""
    stop_receiver()
    clear_data()


def clear_data() -> None:
    """Clear the OSC queue and the live data."""
    queue_mgr.reset()
    live_animator.clear_animation_data()