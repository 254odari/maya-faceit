# faceit_data.py - Updated with correct paths
# Maya Faceit Plugin - Data Definitions

import os
import pathlib

# ... existing code ...

# Update file paths for Maya
RIG_FILE = 'resources/FaceitRig.ma'
CONTROL_RIG_FILE = 'resources/FaceitControlRig.ma'
LANDMARKS_FILE = 'resources/FaceitLandmarks.ma'
RETARGET_PRESETS = 'resources/retarget_presets/'
EXPRESSION_PRESETS = 'resources/expressions/'
EXPRESSION_PRESETS_RIGIFY_NEW = 'resources/expressions/new_rigify_rig/'

def get_addon_dir():
    """Get the addon directory path."""
    return pathlib.Path(os.path.dirname(__file__)).parent.resolve()

def get_retargeting_presets():
    """Get the retargeting presets directory."""
    return os.path.join(get_addon_dir(), RETARGET_PRESETS)

def get_expression_presets(rig_type='FACEIT'):
    """Get the expressions presets folder for the rig type."""
    if rig_type in ('FACEIT', 'RIGIFY'):
        return os.path.join(get_addon_dir(), EXPRESSION_PRESETS)
    elif rig_type == 'RIGIFY_NEW':
        return os.path.join(get_addon_dir(), EXPRESSION_PRESETS_RIGIFY_NEW)
    return ''

def get_rig_file():
    """Get the rig file path."""
    return os.path.join(get_addon_dir(), RIG_FILE)

def get_control_rig_file():
    """Get the control rig file path."""
    return os.path.join(get_addon_dir(), CONTROL_RIG_FILE)

def get_landmarks_file():
    """Get the landmarks file path."""
    return os.path.join(get_addon_dir(), LANDMARKS_FILE)

# ... rest of existing code ...