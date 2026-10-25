# faceit_handlers.py
# Maya Faceit Plugin - Handlers System
# Converted from Blender to Maya Python 3.11

"""
Faceit handlers for Maya.
Manages scene updates, undo/redo, and file operations.
"""

import maya.cmds as cmds
import maya.api.OpenMaya as om2
import functools

# Global state tracking
_landmarks_state_pre = 0
_landmarks_active_pre = False
_handlers_registered = False


# ============================================================
# Handler Registration
# ============================================================

def register_faceit_handlers():
    """
    Register all Faceit handlers with Maya.
    Called during plugin initialization.
    """
    global _handlers_registered
    
    if _handlers_registered:
        return
    
    # Register scene update handler
    om2.MEventMessage.addEventCallback(
        "DagObjectChanged",
        on_scene_update_handler
    )
    
    # Register undo handlers
    om2.MEventMessage.addEventCallback(
        "Undo",
        on_undo_pre_handler
    )
    om2.MEventMessage.addEventCallback(
        "Redo",
        on_undo_post_handler
    )
    
    # Register file handlers
    om2.MEventMessage.addEventCallback(
        "SceneOpened",
        on_file_open_handler
    )
    om2.MEventMessage.addEventCallback(
        "SceneSaved",
        on_file_save_handler
    )
    
    # Register selection handler
    om2.MEventMessage.addEventCallback(
        "SelectionChanged",
        on_selection_handler
    )
    
    _handlers_registered = True
    print("Faceit handlers registered")


def unregister_faceit_handlers():
    """
    Unregister all Faceit handlers.
    Called during plugin uninitialization.
    """
    global _handlers_registered
    
    # Remove all event callbacks
    om2.MEventMessage.removeCallbacks()
    
    _handlers_registered = False
    print("Faceit handlers unregistered")


# ============================================================
# Scene Update Handler
# ============================================================

def on_scene_update_handler(*args, **kwargs):
    """
    Called when the scene updates.
    Handles object changes, attribute changes, and scene state.
    """
    try:
        # Get the active object
        active_obj = cmds.ls(selection=True)[0] if cmds.ls(selection=True) else None
        
        # Check for control rig changes
        if cmds.objExists("faceit_core_data"):
            ctrl_rig = cmds.getAttr("faceit_core_data.control_rig") or ""
            if ctrl_rig and not cmds.objExists(ctrl_rig):
                # Control rig was deleted
                cmds.setAttr("faceit_core_data.control_rig", "", type="string")
                _clear_old_control_rig_data()
        
        # Check for armature changes
        armature = cmds.getAttr("faceit_core_data.armature") or ""
        if armature and not cmds.objExists(armature):
            # Armature was deleted
            cmds.setAttr("faceit_core_data.armature", "", type="string")
            cmds.setAttr("faceit_core_data.shapes_generated", 0)
        
        # Check for Faceit objects changes
        if cmds.objExists("faceit_core_data"):
            objects_str = cmds.getAttr("faceit_core_data.faceit_objects") or ""
            objects = objects_str.split(',') if objects_str else []
            
            # Remove deleted objects from list
            valid_objects = [obj for obj in objects if cmds.objExists(obj)]
            if len(valid_objects) != len(objects):
                cmds.setAttr("faceit_core_data.faceit_objects", ",".join(valid_objects), type="string")
        
        # Update modifier list if shapes are generated
        if cmds.objExists("faceit_core_data"):
            shapes_generated = cmds.getAttr("faceit_core_data.shapes_generated") or 0
            if shapes_generated and active_obj:
                _update_modifier_items(active_obj)
        
        # Handle head object
        if cmds.objExists("faceit_core_data"):
            head_obj = cmds.getAttr("faceit_core_data.head_target") or ""
            if head_obj and cmds.objExists(head_obj):
                if cmds.listConnections(f"{head_obj}.animationData"):
                    action = cmds.getAttr(f"{head_obj}.currentAction") or ""
                    if action and action != cmds.getAttr("faceit_core_data.head_action") or "":
                        cmds.setAttr("faceit_core_data.head_action", action, type="string")
    
    except Exception as e:
        print(f"Faceit scene update error: {str(e)}")


# ============================================================
# Undo/Redo Handlers
# ============================================================

def on_undo_pre_handler(*args, **kwargs):
    """
    Called before an undo operation.
    Saves the current state for restoration.
    """
    global _landmarks_state_pre, _landmarks_active_pre
    
    try:
        # Save landmarks state
        if cmds.objExists("facial_landmarks"):
            _landmarks_active_pre = not (cmds.getAttr("facial_landmarks.hide") or 
                                        cmds.getAttr("facial_landmarks.hideViewport"))
            if _landmarks_active_pre:
                _landmarks_state_pre = cmds.getAttr("facial_landmarks.state") or 0
    except:
        pass


def on_undo_post_handler(*args, **kwargs):
    """
    Called after an undo operation.
    Restores the saved state.
    """
    global _landmarks_state_pre, _landmarks_active_pre
    
    try:
        # Restore landmarks state
        if cmds.objExists("facial_landmarks"):
            landmarks_active_post = not (cmds.getAttr("facial_landmarks.hide") or 
                                        cmds.getAttr("facial_landmarks.hideViewport"))
            
            if landmarks_active_post:
                state = cmds.getAttr("facial_landmarks.state") or 0
                if _landmarks_state_pre != 3 and state == 3:
                    # Set front view
                    _set_front_view()
            else:
                if _landmarks_active_pre:
                    _unlock_view()
                    _landmarks_active_pre = False
    except:
        pass


# ============================================================
# File Handlers
# ============================================================

def on_file_open_handler(*args, **kwargs):
    """
    Called when a file is opened.
    Restores Faceit scene state.
    """
    try:
        # Initialize Faceit core data if needed
        if not cmds.objExists("faceit_core_data"):
            _create_core_data()
        
        # Restore bake modifiers
        if cmds.objExists("faceit_core_data"):
            shapes_generated = cmds.getAttr("faceit_core_data.shapes_generated") or 0
            if shapes_generated:
                _restore_bake_modifiers()
        
        # Set default vertex groups
        _set_default_vertex_groups()
        
        # Refresh UI
        _refresh_faceit_ui()
        
    except Exception as e:
        print(f"Faceit file open error: {str(e)}")


def on_file_save_handler(*args, **kwargs):
    """
    Called when a file is saved.
    Ensures Faceit data is saved properly.
    """
    try:
        # Save current Faceit state
        if cmds.objExists("faceit_core_data"):
            _save_faceit_state()
    except Exception as e:
        print(f"Faceit file save error: {str(e)}")


# ============================================================
# Selection Handler
# ============================================================

def on_selection_handler(*args, **kwargs):
    """
    Called when selection changes.
    Updates Faceit UI based on selection.
    """
    try:
        selection = cmds.ls(selection=True, type='transform')
        if not selection:
            return
        
        active_obj = selection[0]
        
        # Check for control rig selection
        if cmds.attributeQuery("ctrl_rig_id", node=active_obj, exists=True):
            cmds.setAttr("faceit_core_data.control_rig", active_obj, type="string")
        
        # Check for Faceit object selection
        if cmds.objExists("faceit_core_data"):
            objects_str = cmds.getAttr("faceit_core_data.faceit_objects") or ""
            objects = objects_str.split(',') if objects_str else []
            
            if active_obj in objects:
                # Update current object index
                index = objects.index(active_obj)
                cmds.setAttr("faceit_core_data.current_object_index", index)
    
    except Exception as e:
        print(f"Faceit selection error: {str(e)}")


# ============================================================
# Helper Functions
# ============================================================

def _create_core_data():
    """Create Faceit core data node."""
    if not cmds.objExists("faceit_core_data"):
        cmds.createNode("transform", name="faceit_core_data")
        
        # Attributes
        cmds.addAttr("faceit_core_data", ln="version", dt="string")
        cmds.addAttr("faceit_core_data", ln="armature", dt="string")
        cmds.addAttr("faceit_core_data", ln="control_rig", dt="string")
        cmds.addAttr("faceit_core_data", ln="head_target", dt="string")
        cmds.addAttr("faceit_core_data", ln="head_action", dt="string")
        cmds.addAttr("faceit_core_data", ln="faceit_objects", dt="string")
        cmds.addAttr("faceit_core_data", ln="shapes_generated", attributeType="long", min=0, defaultValue=0)
        cmds.addAttr("faceit_core_data", ln="current_object_index", attributeType="long", min=0, defaultValue=0)


def _clear_old_control_rig_data():
    """Clear old control rig data."""
    # Implementation to clean up control rig data
    pass


def _update_modifier_items(obj_name: str):
    """Update modifier items for an object."""
    # Implementation to update modifier list
    pass


def _restore_bake_modifiers():
    """Restore bake modifiers from saved data."""
    # Implementation to restore modifiers
    pass


def _set_default_vertex_groups():
    """Set default vertex groups for Faceit objects."""
    if cmds.objExists("faceit_core_data"):
        objects_str = cmds.getAttr("faceit_core_data.faceit_objects") or ""
        objects = objects_str.split(',') if objects_str else []
        
        from .faceit_data import FACEIT_VERTEX_GROUPS
        
        for obj in objects:
            if cmds.objExists(obj):
                # Create vertex groups if they don't exist
                for vg_name in FACEIT_VERTEX_GROUPS:
                    if vg_name not in cmds.listAttr(f"{obj}.vertexGroups"):
                        cmds.vertexGroup(obj, add=vg_name)


def _set_front_view():
    """Set the viewport to front view."""
    # Implementation to set front view
    pass


def _unlock_view():
    """Unlock viewport rotation."""
    # Implementation to unlock view
    pass


def _refresh_faceit_ui():
    """Refresh Faceit UI elements."""
    # Implementation to refresh UI
    pass


def _save_faceit_state():
    """Save Faceit state."""
    # Implementation to save state
    pass


# ============================================================
# Handler Class for Maya
# ============================================================

class FaceitHandlerManager:
    """
    Manages Faceit handlers for Maya.
    """
    
    def __init__(self):
        self.handlers_registered = False
    
    def register(self):
        """Register all handlers."""
        register_faceit_handlers()
        self.handlers_registered = True
    
    def unregister(self):
        """Unregister all handlers."""
        unregister_faceit_handlers()
        self.handlers_registered = False
    
    def is_registered(self):
        """Check if handlers are registered."""
        return self.handlers_registered


# Global handler manager instance
_handler_manager = None

def get_handler_manager():
    """Get the global handler manager instance."""
    global _handler_manager
    if _handler_manager is None:
        _handler_manager = FaceitHandlerManager()
    return _handler_manager