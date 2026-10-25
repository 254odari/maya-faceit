# osc_handler.py
# Maya Faceit Plugin - OSC Handler
# Converted from Blender to Maya Python 3.11

"""
OSC handler for Faceit Maya plugin.
Handles OSC message queue processing and timer callbacks.
"""

import maya.cmds as cmds # type: ignore
import maya.api.OpenMaya as om2 # type: ignore
import time
from typing import List, Optional, Any, Dict

from .osc_receiver import osc_queue
from .osc_operators import live_animator, receiver

# ============================================================
# Constants
# ============================================================

UPDATE_QUERIES = 60
QUERIES_PER_SECOND = 200
MAX_QUEUE_SIZE = 10000

# ============================================================
# OSC Queue Processing
# ============================================================

def process_osc_queue() -> float:
    """
    Process incoming OSC messages.
    Runs persistently and processes all incoming messages.
    
    Returns:
        Time until next call in seconds
    """
    global osc_queue
    
    if osc_queue and receiver.enabled:
        # Get the last UPDATE_QUERIES messages
        anim_list = osc_queue[-UPDATE_QUERIES:]
        
        for _ in range(len(anim_list)):
            if not anim_list:
                break
            
            # Process the oldest message first (FIFO)
            data = anim_list.pop(0)
            
            try:
                live_animator.process_data(data)
            except Exception as e:
                cmds.warning(f"Error processing OSC data: {str(e)}")
        
        # Clear processed messages
        if osc_queue:
            osc_queue.clear()
        
        return 1.0 / QUERIES_PER_SECOND
    
    # Return small delay when idle
    return 0.01


def clear_osc_queue() -> None:
    """Clear the OSC queue."""
    global osc_queue
    osc_queue.clear()


def get_osc_queue_size() -> int:
    """Get the current OSC queue size."""
    return len(osc_queue)


def is_osc_connected() -> bool:
    """Check if OSC receiver is connected."""
    return receiver.enabled if hasattr(receiver, 'enabled') else False


# ============================================================
# Maya Timer Callbacks
# ============================================================

_timer_id = None


def register_osc_timer() -> None:
    """
    Register the OSC timer with Maya.
    """
    global _timer_id
    
    # Unregister existing timer
    unregister_osc_timer()
    
    # Register new timer
    _timer_id = om2.MEventMessage.addEventCallback(
        "idle",
        _on_idle_callback
    )
    
    print("OSC timer registered")


def unregister_osc_timer() -> None:
    """
    Unregister the OSC timer.
    """
    global _timer_id
    
    if _timer_id is not None:
        try:
            om2.MMessage.removeCallback(_timer_id)
        except:
            pass
        _timer_id = None


def _on_idle_callback(*args, **kwargs) -> None:
    """
    Called during idle time to process OSC messages.
    """
    try:
        process_osc_queue()
    except Exception as e:
        cmds.warning(f"OSC idle callback error: {str(e)}")


# ============================================================
# Scene Save/Load Handlers
# ============================================================

def close_osc_on_scene_save(*args, **kwargs) -> None:
    """
    Close OSC connection when scene is saved.
    """
    if is_osc_connected():
        # Stop receiving but keep data
        try:
            from .osc_operators import stop_receiver
            stop_receiver()
            print("OSC connection closed for scene save")
        except:
            pass


def close_osc_on_scene_load(*args, **kwargs) -> None:
    """
    Close OSC connection when scene is loaded.
    """
    if is_osc_connected():
        try:
            from .osc_operators import stop_receiver
            stop_receiver()
            print("OSC connection closed for scene load")
        except:
            pass


# ============================================================
# Maya Callback Registration
# ============================================================

_handlers_registered = False


def register_osc_handlers() -> None:
    """
    Register all OSC handlers with Maya.
    """
    global _handlers_registered
    
    if _handlers_registered:
        return
    
    # Register scene callbacks
    om2.MEventMessage.addEventCallback(
        "SceneSaved",
        close_osc_on_scene_save
    )
    
    om2.MEventMessage.addEventCallback(
        "SceneOpened",
        close_osc_on_scene_load
    )
    
    # Register timer
    register_osc_timer()
    
    _handlers_registered = True
    print("OSC handlers registered")


def unregister_osc_handlers() -> None:
    """
    Unregister all OSC handlers.
    """
    global _handlers_registered
    
    unregister_osc_timer()
    
    # Remove all event callbacks
    try:
        om2.MEventMessage.removeCallbacks()
    except:
        pass
    
    _handlers_registered = False
    print("OSC handlers unregistered")


# ============================================================
# Utility Functions for UI
# ============================================================

def get_osc_status() -> Dict[str, Any]:
    """
    Get current OSC status information.
    
    Returns:
        Dictionary with status information
    """
    return {
        'connected': is_osc_connected(),
        'queue_size': get_osc_queue_size(),
        'receiver_enabled': receiver.enabled if hasattr(receiver, 'enabled') else False,
        'animator_active': live_animator.animate_shapes if hasattr(live_animator, 'animate_shapes') else False,
    }


def update_osc_ui() -> None:
    """
    Update OSC UI elements.
    """
    # Force UI refresh
    cmds.refresh()