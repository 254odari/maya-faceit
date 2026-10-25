# __init__.py
# Maya Faceit Plugin - Mocap Module
# Version: 1.0.0

"""
Faceit Mocap Module for Maya
============================

This module provides motion capture functionality for the Faceit pipeline.

Main Components:
    - Motion capture importers (FaceCap, Epic, A2F)
    - OSC live animation receiver
    - Animation utilities
    - Head and shape key animation
"""

__version__ = "1.0.0"
__author__ = "Faceit Team"

# ============================================================
# Module Imports
# ============================================================

from . import mocap_base
from . import mocap_importers
from . import mocap_operators
from . import mocap_utils
from . import osc_handler
from . import osc_operators
from . import osc_receiver

# ============================================================
# Imports from mocap_base
# ============================================================

from .mocap_base import (
    MocapBase,
    MocapImporterBase,
)

# ============================================================
# Imports from mocap_importers
# ============================================================

from .mocap_importers import (
    FaceCapImporter,
    A2FMocapImporter,
    EpicMocapImporter,
    OSCLiveAnimator,
)

# ============================================================
# Imports from mocap_utils
# ============================================================

from .mocap_utils import (
    get_current_timestamp,
    get_scene_frame_rate,
    add_zero_keyframe,
    remove_frame_range,
)

# ============================================================
# Imports from osc_operators
# ============================================================

from .osc_operators import (
    ReceiverStart,
    ReceiverStop,
    ImportLiveMocap,
    ClearLiveData,
    ReceiverCancel,
    stop_receiver,
    cancel_recording,
    clear_data,
    get_head_base_transform,
)

# ============================================================
# Imports from osc_receiver
# ============================================================

from .osc_receiver import (
    QueueManager,
    Receiver,
    osc_queue,
)

# ============================================================
# Imports from osc_handler
# ============================================================

from .osc_handler import (
    process_osc_queue,
    clear_osc_queue,
    get_osc_queue_size,
    is_osc_connected,
    register_osc_handlers,
    unregister_osc_handlers,
    get_osc_status,
    update_osc_ui,
)

# ============================================================
# Module Exports
# ============================================================

__all__ = [
    # Base classes
    'MocapBase',
    'MocapImporterBase',
    
    # Importers
    'FaceCapImporter',
    'A2FMocapImporter',
    'EpicMocapImporter',
    'OSCLiveAnimator',
    
    # Utilities
    'get_current_timestamp',
    'get_scene_frame_rate',
    'add_zero_keyframe',
    'remove_frame_range',
    
    # OSC
    'ReceiverStart',
    'ReceiverStop',
    'ImportLiveMocap',
    'ClearLiveData',
    'ReceiverCancel',
    'stop_receiver',
    'cancel_recording',
    'clear_data',
    'get_head_base_transform',
    'QueueManager',
    'Receiver',
    'osc_queue',
    
    # OSC Handler
    'process_osc_queue',
    'clear_osc_queue',
    'get_osc_queue_size',
    'is_osc_connected',
    'register_osc_handlers',
    'unregister_osc_handlers',
    'get_osc_status',
    'update_osc_ui',
]