# retarget_presets/__init__.py
# Faceit Maya Plugin - Retarget Presets Loader

"""
Retarget presets for Faceit Maya plugin.
Provides preset mappings for different character systems.
"""

import os
import json
from typing import Dict, List, Optional


def load_preset(preset_name: str) -> Optional[Dict]:
    """
    Load a retarget preset by name.
    
    Args:
        preset_name: Name of the preset (cc3, cc3+, cc4, daz_gen8)
        
    Returns:
        Preset dictionary or None
    """
    preset_file = os.path.join(os.path.dirname(__file__), f"{preset_name}.json")
    
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
        if file.endswith('.json'):
            presets.append(file.replace('.json', ''))
    return presets


def get_preset_mapping(preset_name: str) -> Dict:
    """
    Get the mapping dictionary for a preset.
    
    Args:
        preset_name: Name of the preset
        
    Returns:
        Mapping dictionary
    """
    preset = load_preset(preset_name)
    if preset:
        return preset
    return {}


def get_target_shapes_for_source(preset_name: str, source_shape: str) -> List[str]:
    """
    Get target shapes for a source shape from a preset.
    
    Args:
        preset_name: Name of the preset
        source_shape: Source shape name
        
    Returns:
        List of target shape names
    """
    mapping = get_preset_mapping(preset_name)
    if source_shape in mapping:
        return mapping[source_shape].get('target_shapes', [])
    return []


def get_amplify_for_source(preset_name: str, source_shape: str) -> float:
    """
    Get amplify value for a source shape from a preset.
    
    Args:
        preset_name: Name of the preset
        source_shape: Source shape name
        
    Returns:
        Amplify value
    """
    mapping = get_preset_mapping(preset_name)
    if source_shape in mapping:
        return mapping[source_shape].get('amplify', 1.0)
    return 1.0


def get_region_for_source(preset_name: str, source_shape: str) -> str:
    """
    Get region for a source shape from a preset.
    
    Args:
        preset_name: Name of the preset
        source_shape: Source shape name
        
    Returns:
        Region name
    """
    mapping = get_preset_mapping(preset_name)
    if source_shape in mapping:
        return mapping[source_shape].get('region', 'other')
    return 'other'


# Preset descriptions for UI
PRESET_DESCRIPTIONS = {
    'cc3': 'Character Creator 3',
    'cc3+': 'Character Creator 3+',
    'cc4': 'Character Creator 4',
    'daz_gen8': 'DAZ Studio Genesis 8',
}