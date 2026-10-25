# __init__.py
# Faceit Maya Plugin - New Rigify Rig Expressions

"""
Expression presets for the new Rigify face rig.
These presets are compatible with the new Rigify face rig structure.
"""

import os
import json
from typing import Dict, List, Optional


def load_expression_preset(preset_name: str) -> Optional[Dict]:
    """
    Load an expression preset for the new Rigify rig.
    
    Args:
        preset_name: Name of the preset (arkit, tongue, phoneme, a2f_46)
        
    Returns:
        Preset dictionary or None
    """
    preset_file = os.path.join(os.path.dirname(__file__), f"{preset_name}_expressions.face")
    
    if not os.path.exists(preset_file):
        return None
    
    try:
        with open(preset_file, 'r') as f:
            return json.load(f)
    except:
        return None


def get_available_presets() -> List[str]:
    """
    Get list of available preset names.
    
    Returns:
        List of preset names
    """
    presets = []
    for file in os.listdir(os.path.dirname(__file__)):
        if file.endswith('.face'):
            presets.append(file.replace('_expressions.face', ''))
    return presets


# Preset descriptions for UI
PRESET_DESCRIPTIONS = {
    'arkit': 'ARKit 52 Expressions (New Rigify)',
    'tongue': 'Tongue Expressions (New Rigify)',
    'phoneme': 'Phoneme Expressions (New Rigify)',
    'a2f_46': 'Audio2Face 46 Expressions (New Rigify)',
}