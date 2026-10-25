# faceit_callback.py
# Maya Faceit Plugin - Callback System
# Converted from Blender to Maya Python 3.11

"""
Faceit callback system for Maya.
Handles scene events, object selection changes, and viewport updates.
"""

import maya.cmds as cmds
import maya.api.OpenMaya as om2
from maya.api.OpenMaya import MSceneMessage
import functools

# Global callback IDs for cleanup
_callback_ids = []


# ============================================================
# Callback Registration Functions
# ============================================================

def register_faceit_callbacks():
    """
    Register all Faceit callbacks with Maya.
    Called during plugin initialization.
    """
    global _callback_ids
    
    # Register scene callbacks
    callback_id = MSceneMessage.addCallback(
        MSceneMessage.kAfterOpen,
        on_scene_open_callback
    )
    _callback_ids.append(callback_id)
    
    callback_id = MSceneMessage.addCallback(
        MSceneMessage.kAfterNew,
        on_scene_new_callback
    )
    _callback_ids.append(callback_id)
    
    callback_id = MSceneMessage.addCallback(
        MSceneMessage.kAfterSave,
        on_scene_save_callback
    )
    _callback_ids.append(callback_id)
    
    # Register selection change callback
    callback_id = om2.MEventMessage.addEventCallback(
        "SelectionChanged",
        on_selection_changed_callback
    )
    _callback_ids.append(callback_id)
    
    # Register time change callback
    callback_id = om2.MEventMessage.addEventCallback(
        "timeChanged",
        on_time_changed_callback
    )
    _callback_ids.append(callback_id)
    
    # Register idle callback
    callback_id = om2.MEventMessage.addEventCallback(
        "idle",
        on_idle_callback
    )
    _callback_ids.append(callback_id)
    
    print(f"Registered {len(_callback_ids)} Faceit callbacks")


def unregister_faceit_callbacks():
    """
    Unregister all Faceit callbacks.
    Called during plugin uninitialization.
    """
    global _callback_ids
    
    for callback_id in _callback_ids:
        try:
            om2.MMessage.removeCallback(callback_id)
        except:
            pass
    
    _callback_ids.clear()
    print("Unregistered all Faceit callbacks")


# ============================================================
# Scene Callbacks
# ============================================================

def on_scene_open_callback(*args, **kwargs):
    """
    Called when a scene is opened.
    Restores Faceit state from scene data.
    """
    print("Faceit: Scene opened")
    
    # Check if Faceit data exists
    if cmds.objExists("faceit_core_data"):
        # Restore Faceit state
        _restore_faceit_state()
    
    # Update UI
    _refresh_faceit_ui()


def on_scene_new_callback(*args, **kwargs):
    """
    Called when a new scene is created.
    Initializes Faceit data.
    """
    print("Faceit: New scene created")
    
    # Create core data nodes
    _ensure_faceit_data_nodes()


def on_scene_save_callback(*args, **kwargs):
    """
    Called when a scene is saved.
    Ensures Faceit data is up to date.
    """
    # Save any pending Faceit state
    _save_faceit_state()


# ============================================================
# Selection Callback
# ============================================================

def on_selection_changed_callback(*args, **kwargs):
    """
    Called when the selection changes in Maya.
    Updates Faceit UI based on selection.
    """
    selection = cmds.ls(selection=True, type='transform')
    
    if selection:
        active_obj = selection[0]
        
        # Check if selected object is a Faceit object
        if _is_faceit_object(active_obj):
            # Update Faceit UI
            _update_faceit_ui_for_object(active_obj)
        
        # Check if selected object is the Faceit armature
        if _is_faceit_armature(active_obj):
            # Update armature UI
            _update_faceit_ui_for_armature(active_obj)
        
        # Check if selected object is the control rig
        if _is_faceit_control_rig(active_obj):
            # Update control rig UI
            _update_faceit_ui_for_control_rig(active_obj)


# ============================================================
# Time Change Callback
# ============================================================

def on_time_changed_callback(*args, **kwargs):
    """
    Called when the timeline time changes.
    Updates expression values based on current frame.
    """
    current_frame = cmds.currentTime(query=True)
    
    # Check if we're on an expression frame
    if cmds.objExists("faceit_core_data"):
        frames_str = cmds.getAttr("faceit_core_data.expression_frames") or ""
        frames = [int(x) for x in frames_str.split(',')] if frames_str else []
        
        if current_frame in frames:
            # Update expression display
            _update_expression_display(current_frame)


# ============================================================
# Idle Callback
# ============================================================

def on_idle_callback(*args, **kwargs):
    """
    Called during idle time.
    Used for deferred updates and UI refreshing.
    """
    # Check if any Faceit updates are pending
    if cmds.objExists("faceit_core_data"):
        pending_updates = cmds.getAttr("faceit_core_data.pending_updates") or 0
        if pending_updates > 0:
            _process_pending_updates()
            cmds.setAttr("faceit_core_data.pending_updates", 0)


# ============================================================
# Helper Functions
# ============================================================

def _ensure_faceit_data_nodes():
    """Create Faceit data nodes if they don't exist."""
    if not cmds.objExists("faceit_core_data"):
        cmds.createNode("transform", name="faceit_core_data")
        
        # Core data attributes
        cmds.addAttr("faceit_core_data", ln="version", dt="string")
        cmds.addAttr("faceit_core_data", ln="expression_names", dt="string")
        cmds.addAttr("faceit_core_data", ln="expression_frames", dt="string")
        cmds.addAttr("faceit_core_data", ln="expression_sides", dt="string")
        cmds.addAttr("faceit_core_data", ln="expression_procedural", dt="string")
        cmds.addAttr("faceit_core_data", ln="current_index", attributeType="long", min=0, defaultValue=0)
        
        # Pending updates flag
        cmds.addAttr("faceit_core_data", ln="pending_updates", attributeType="long", min=0, defaultValue=0)


def _restore_faceit_state():
    """Restore Faceit state from scene data."""
    # Check if Faceit expressions exist
    if cmds.objExists("faceit_core_data"):
        names_str = cmds.getAttr("faceit_core_data.expression_names") or ""
        names = names_str.split(',') if names_str else []
        
        if names:
            print(f"Faceit: Restored {len(names)} expressions")


def _save_faceit_state():
    """Save Faceit state to scene data."""
    # Ensure core data exists
    _ensure_faceit_data_nodes()


def _is_faceit_object(obj_name: str) -> bool:
    """Check if an object is registered with Faceit."""
    if not cmds.objExists("faceit_core_data"):
        return False
    
    # Check if object is in Faceit objects list
    objects_str = cmds.getAttr("faceit_core_data.faceit_objects") or ""
    objects = objects_str.split(',') if objects_str else []
    
    return obj_name in objects


def _is_faceit_armature(obj_name: str) -> bool:
    """Check if an object is the Faceit armature."""
    # Check by name or attribute
    if cmds.objExists(obj_name):
        # Check for Faceit armature attribute
        if cmds.attributeQuery("faceit_armature", node=obj_name, exists=True):
            return True
        
        # Check by name
        if obj_name == "FaceitRig":
            return True
    
    return False


def _is_faceit_control_rig(obj_name: str) -> bool:
    """Check if an object is the Faceit control rig."""
    if cmds.objExists(obj_name):
        # Check for control rig attribute
        if cmds.attributeQuery("ctrl_rig_id", node=obj_name, exists=True):
            return True
        
        # Check by name
        if "FaceitControlRig" in obj_name:
            return True
    
    return False


def _update_faceit_ui_for_object(obj_name: str):
    """Update Faceit UI for a selected object."""
    # This would trigger UI updates in the Faceit panels
    pass


def _update_faceit_ui_for_armature(obj_name: str):
    """Update Faceit UI for the armature."""
    # Update armature-related UI elements
    pass


def _update_faceit_ui_for_control_rig(obj_name: str):
    """Update Faceit UI for the control rig."""
    # Update control rig-related UI elements
    pass


def _update_expression_display(frame: int):
    """Update expression display for a specific frame."""
    # Find expression at this frame
    if cmds.objExists("faceit_core_data"):
        names_str = cmds.getAttr("faceit_core_data.expression_names") or ""
        frames_str = cmds.getAttr("faceit_core_data.expression_frames") or ""
        
        names = names_str.split(',') if names_str else []
        frames = [int(x) for x in frames_str.split(',')] if frames_str else []
        
        for i, f in enumerate(frames):
            if f == frame and i < len(names):
                # Update current expression index
                cmds.setAttr("faceit_core_data.current_index", i)
                break


def _process_pending_updates():
    """Process any pending Faceit updates."""
    # This would handle deferred updates like:
    # - Updating expression sliders
    # - Refreshing viewport
    # - Updating UI panels
    pass


def _refresh_faceit_ui():
    """Refresh all Faceit UI elements."""
    # This would trigger a refresh of all Faceit panels
    pass


# ============================================================
# Callback Decorators for Maya
# ============================================================

def on_object_change_callback(func):
    """Decorator for object change callbacks."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"Faceit callback error: {str(e)}")
    return wrapper


def on_attribute_change_callback(attribute_name: str):
    """Decorator for attribute change callbacks."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                print(f"Faceit attribute change error for {attribute_name}: {str(e)}")
        return wrapper
    return decorator


# ============================================================
# Callback Utilities for UI Refresh
# ============================================================

def refresh_faceit_properties_panel():
    """Refresh the Faceit properties panel."""
    # Find and refresh the Faceit panel
    for panel in cmds.getPanel(scriptType='faceitPanel'):
        cmds.refreshEditorTemplates(panel)


def update_faceit_viewport_overlay():
    """Update Faceit viewport overlays."""
    # Force viewport update
    cmds.refresh()


def set_pending_update():
    """Set a pending update flag."""
    if cmds.objExists("faceit_core_data"):
        current = cmds.getAttr("faceit_core_data.pending_updates") or 0
        cmds.setAttr("faceit_core_data.pending_updates", current + 1)