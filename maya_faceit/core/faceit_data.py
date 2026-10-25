# faceit_data.py
# Maya Faceit Plugin - Data Definitions
# Converted from Blender to Maya Python 3.11

"""
Faceit data definitions for Maya.
Contains bone lists, vertex group definitions, and expression region mappings.
"""

import os
import pathlib
from typing import List, Dict, Optional

# Import shape data
from . import arkit_shapes as shapes


# ============================================================
# File Paths
# ============================================================

RIG_FILE = 'resources/FaceitRig.ma'
CONTROL_RIG_FILE = 'resources/FaceitControlRig.ma'
LANDMARKS_FILE = 'resources/FaceitLandmarks.ma'
RETARGET_PRESETS = 'resources/retarget_presets/'
EXPRESSION_PRESETS = 'resources/expressions/'
EXPRESSION_PRESETS_RIGIFY_NEW = 'resources/expressions/new_rigify_rig/'


# ============================================================
# Maya Version
# ============================================================

PLUGIN_VERSION = "1.0.0"


def get_faceit_current_version() -> str:
    """Get the current Faceit plugin version."""
    return PLUGIN_VERSION


def get_addon_dir() -> pathlib.Path:
    """Get the addon directory path."""
    return pathlib.Path(os.path.dirname(__file__)).parent.resolve()


def get_retargeting_presets() -> str:
    """Get the retargeting presets directory."""
    return os.path.join(get_addon_dir(), RETARGET_PRESETS)


def get_expression_presets(rig_type: str = 'FACEIT') -> str:
    """
    Get the expressions presets folder for the rig type.
    
    Args:
        rig_type: Value in ['FACEIT', 'RIGIFY_NEW']
        
    Returns:
        Path to expression presets
    """
    if rig_type in ('FACEIT', 'RIGIFY'):
        return os.path.join(get_addon_dir(), EXPRESSION_PRESETS)
    elif rig_type == 'RIGIFY_NEW':
        return os.path.join(get_addon_dir(), EXPRESSION_PRESETS_RIGIFY_NEW)
    return ''


def get_rig_file() -> str:
    """Get the rig file path."""
    return os.path.join(get_addon_dir(), RIG_FILE)


def get_control_rig_file() -> str:
    """Get the control rig file path."""
    return os.path.join(get_addon_dir(), CONTROL_RIG_FILE)


def get_landmarks_file() -> str:
    """Get the landmarks file path."""
    return os.path.join(get_addon_dir(), LANDMARKS_FILE)


# ============================================================
# Shape Data Access
# ============================================================

def get_arkit_shape_data() -> Dict:
    """Returns dictionary of ARKit expression names."""
    return shapes.ARKIT['Data']


def get_face_cap_shape_data() -> Dict:
    """Returns dictionary of FaceCap expression names."""
    return shapes.FACECAP['Data']


def get_epic_shape_data() -> Dict:
    """Returns dictionary of Epic Games expression names."""
    return shapes.EPIC['Data']


def get_a2f_shape_data() -> Dict:
    """Returns dictionary of Audio2Face expression names."""
    return shapes.A2F['Data']


def get_tongue_shape_data() -> Dict:
    """Returns dictionary of tongue expression names."""
    return shapes.TONGUE['Data']


def get_phonemes_shape_data() -> Dict:
    """Returns dictionary of phoneme expression names."""
    return shapes.PHONEMES['Data']


def get_shape_data_for_mocap_engine(mocap_engine: str = None) -> Optional[Dict]:
    """
    Get shape data for a specific mocap engine.
    
    Args:
        mocap_engine: 'ARKIT', 'FACECAP', 'EPIC', or 'A2F'
        
    Returns:
        Dictionary of shape data or None
    """
    engine_map = {
        'ARKIT': get_arkit_shape_data,
        'FACECAP': get_face_cap_shape_data,
        'EPIC': get_epic_shape_data,
        'A2F': get_a2f_shape_data,
    }
    
    if mocap_engine in engine_map:
        return engine_map[mocap_engine]()
    
    return None


# ============================================================
# Rigify Bone Mapping
# ============================================================

def get_rigify_bone_from_old_name(bone_name: str) -> str:
    """
    Map old Rigify bone names to new Rigify bone names.
    
    Args:
        bone_name: Old bone name
        
    Returns:
        New bone name
    """
    RIGIFY_OLD_TO_NEW = {
        'lips.L': 'lip_end.L.001',
        'lips.R': 'lip_end.R.001',
        'tongue_master': 'tongue',
        'tongue': 'tweak_tongue',
        'tongue.001': 'tweak_tongue.001',
        'tongue.002': 'tweak_tongue.002',
        'tongue.003': 'tweak_tongue.003',
        'nose.005': 'nose_end.004',
        'chin.002': 'chin_end.001',
        'eyes': 'eye_common',
    }
    return RIGIFY_OLD_TO_NEW.get(bone_name, bone_name)


# ============================================================
# Vertex Group Definitions
# ============================================================

FACEIT_VERTEX_GROUPS = [
    'faceit_right_eyeball',
    'faceit_left_eyeball',
    'faceit_left_eyes_other',
    'faceit_right_eyes_other',
    'faceit_upper_teeth',
    'faceit_lower_teeth',
    'faceit_tongue',
    'faceit_eyelashes',
    'faceit_rigid',
    'faceit_main',
    'faceit_facial_hair',
]


def get_list_faceit_groups() -> List[str]:
    """Get the list of Faceit vertex group names."""
    return FACEIT_VERTEX_GROUPS


# ============================================================
# Face Bones Definitions
# ============================================================

FACEIT_BONES = [
    'MCH-eyes_parent', 'eyes', 'eye.L', 'eye.R', 'DEF-face', 
    'DEF-forehead.L', 'DEF-forehead.R', 'DEF-forehead.L.001',
    'DEF-forehead.R.001', 'DEF-forehead.L.002', 'DEF-forehead.R.002', 
    'DEF-temple.L', 'DEF-temple.R', 'master_eye.L',
    'brow.B.L', 'DEF-brow.B.L', 'brow.B.L.001', 'DEF-brow.B.L.001', 
    'brow.B.L.002', 'DEF-brow.B.L.002', 'brow.B.L.003',
    'DEF-brow.B.L.003', 'brow.B.L.004', 'lid.B.L', 'lid.B.L.001', 
    'lid.B.L.002', 'lid.B.L.003', 'lid.T.L',
    'lid.T.L.001', 'lid.T.L.002', 'lid.T.L.003', 'MCH-eye.L', 
    'DEF_eye.L', 'MCH-eye.L.001', 'MCH-lid.B.L',
    'DEF-lid.B.L', 'MCH-lid.B.L.001', 'DEF-lid.B.L.001', 
    'MCH-lid.B.L.002', 'DEF-lid.B.L.002', 'MCH-lid.B.L.003',
    'DEF-lid.B.L.003', 'MCH-lid.T.L', 'DEF-lid.T.L', 'MCH-lid.T.L.001',
    'DEF-lid.T.L.001', 'MCH-lid.T.L.002', 'DEF-lid.T.L.002', 
    'MCH-lid.T.L.003', 'DEF-lid.T.L.003', 'master_eye.R', 
    'brow.B.R', 'DEF-brow.B.R', 'brow.B.R.001',
    'DEF-brow.B.R.001', 'brow.B.R.002', 'DEF-brow.B.R.002', 
    'brow.B.R.003', 'DEF-brow.B.R.003', 'brow.B.R.004',
    'lid.B.R', 'lid.B.R.001', 'lid.B.R.002', 'lid.B.R.003', 
    'lid.T.R', 'lid.T.R.001', 'lid.T.R.002', 'lid.T.R.003',
    'MCH-eye.R', 'DEF_eye.R', 'MCH-eye.R.001', 'MCH-lid.B.R', 
    'DEF-lid.B.R', 'MCH-lid.B.R.001', 'DEF-lid.B.R.001',
    'MCH-lid.B.R.002', 'DEF-lid.B.R.002', 'MCH-lid.B.R.003', 
    'DEF-lid.B.R.003', 'MCH-lid.T.R', 'DEF-lid.T.R',
    'MCH-lid.T.R.001', 'DEF-lid.T.R.001', 'MCH-lid.T.R.002', 
    'DEF-lid.T.R.002', 'MCH-lid.T.R.003', 'DEF-lid.T.R.003',
    'jaw_master', 'chin', 'DEF-chin', 'chin.001', 'DEF-chin.001', 
    'chin.L', 'DEF-chin.L', 'chin.R', 'DEF-chin.R', 'jaw',
    'DEF-jaw', 'jaw.L.001', 'DEF-jaw.L.001', 'jaw.R.001', 
    'DEF-jaw.R.001', 'MCH-tongue.001', 'tongue.001',
    'DEF-tongue.001', 'MCH-tongue.002', 'tongue.002', 
    'DEF-tongue.002', 'tongue_master', 'tongue', 'DEF-tongue',
    'tongue.003', 'teeth.B', 'DEF-teeth.B', 'brow.T.L', 
    'DEF-cheek.T.L', 'DEF-brow.T.L', 'brow.T.L.001',
    'DEF-brow.T.L.001', 'brow.T.L.002', 'DEF-brow.T.L.002', 
    'brow.T.L.003', 'DEF-brow.T.L.003', 'brow.T.R',
    'DEF-cheek.T.R', 'DEF-brow.T.R', 'brow.T.R.001', 
    'DEF-brow.T.R.001', 'brow.T.R.002', 'DEF-brow.T.R.002',
    'brow.T.R.003', 'DEF-brow.T.R.003', 'jaw.L', 'DEF-jaw.L', 
    'jaw.R', 'DEF-jaw.R', 'nose', 'DEF-nose', 'nose.L',
    'DEF-nose.L', 'nose.R', 'DEF-nose.R', 'MCH-mouth_lock', 
    'MCH-jaw_master', 'lip.B', 'DEF-lip.B.L', 'DEF-lip.B.R',
    'chin.002', 'MCH-jaw_master.001', 'lip.B.L.001', 
    'DEF-lip.B.L.001', 'lip.B.R.001', 'DEF-lip.B.R.001',
    'MCH-jaw_master.002', 'cheek.B.L.001', 'DEF-cheek.B.L.001', 
    'cheek.B.R.001', 'DEF-cheek.B.R.001', 'lips.L',
    'DEF-cheek.B.L', 'lips.R', 'DEF-cheek.B.R', 'MCH-jaw_master.003', 
    'lip.T.L.001', 'DEF-lip.T.L.001', 'lip.T.R.001',
    'DEF-lip.T.R.001', 'lip.T', 'DEF-lip.T.L', 'DEF-lip.T.R', 
    'nose.005', 'MCH-jaw_master.004', 'nose_master',
    'nose.002', 'DEF-nose.002', 'nose.003', 'DEF-nose.003', 
    'nose.001', 'DEF-nose.001', 'nose.004', 'DEF-nose.004',
    'nose.L.001', 'DEF-nose.L.001', 'nose.R.001', 
    'DEF-nose.R.001', 'cheek.T.L.001', 'DEF-cheek.T.L.001',
    'cheek.T.R.001', 'DEF-cheek.T.R.001', 'DEF_forhead_01.L', 
    'DEF_forhead_02.L', 'DEF_forhead_03.L',
    'DEF_forhead_04.L', 'DEF_forhead_01.R', 'DEF_forhead_02.R', 
    'DEF_forhead_03.R', 'DEF_forhead_04.R', 'teeth.T',
    'DEF-teeth.T']


FACEIT_CTRL_BONES = [
    'eyes', 'eye.L', 'eye.R', 'brow.B.L', 'brow.B.L.001', 
    'brow.B.L.002', 'brow.B.L.003', 'brow.B.L.004', 'lid.B.L',
    'lid.B.L.001', 'lid.B.L.002', 'lid.B.L.003', 'lid.T.L', 
    'lid.T.L.001', 'lid.T.L.002', 'lid.T.L.003', 'brow.B.R',
    'brow.B.R.001', 'brow.B.R.002', 'brow.B.R.003', 
    'brow.B.R.004', 'lid.B.R', 'lid.B.R.001', 'lid.B.R.002',
    'lid.B.R.003', 'lid.T.R', 'lid.T.R.001', 'lid.T.R.002', 
    'lid.T.R.003', 'jaw_master', 'chin', 'chin.001', 'chin.L',
    'chin.R', 'jaw', 'jaw.L.001', 'jaw.R.001', 'tongue.001', 
    'tongue.002', 'tongue_master', 'tongue', 'tongue.003',
    'teeth.B', 'brow.T.L', 'brow.T.L.001', 'brow.T.L.002', 
    'brow.T.L.003', 'brow.T.R', 'brow.T.R.001', 'brow.T.R.002',
    'brow.T.R.003', 'jaw.L', 'jaw.R', 'nose', 'nose.L', 
    'nose.R', 'lip.B', 'chin.002', 'lip.B.L.001', 'lip.B.R.001',
    'cheek.B.L.001', 'cheek.B.R.001', 'lips.L', 'lips.R', 
    'lip.T.L.001', 'lip.T.R.001', 'lip.T', 'nose.005',
    'nose_master', 'nose.002', 'nose.003', 'nose.001', 'nose.004', 
    'nose.L.001', 'nose.R.001', 'cheek.T.L.001',
    'cheek.T.R.001', 'teeth.T']


# ============================================================
# Face Regions Definitions
# ============================================================

FACE_REGIONS_BASE = {
    'Eyes': [
        'eyeBlinkLeft', 'eyeLookDownLeft', 'eyeLookInLeft', 
        'eyeLookOutLeft', 'eyeLookUpLeft', 'eyeSquintLeft', 
        'eyeWideLeft', 'eyeBlinkRight', 'eyeLookDownRight',
        'eyeLookInRight', 'eyeLookOutRight', 'eyeLookUpRight', 
        'eyeSquintRight', 'eyeWideRight', 'eyesLookLeft',
        'eyesLookRight', 'eyesLookUp', 'eyesLookDown', 
        'eyesCloseL', 'eyesCloseR', 'eyesUpperLidRaiserL',
        'eyesUpperLidRaiserR', 'squintL', 'squintR',
    ],
    'Brows': [
        'browDownLeft', 'browDownRight', 'browInnerUp', 
        'browOuterUpLeft', 'browOuterUpRight', 'browLowerL',
        'browLowerR', 'innerBrowRaiserL', 'innerBrowRaiserR',
        'outerBrowRaiserL', 'outerBrowRaiserR',
    ],
    'Cheeks': [
        'cheekPuff', 'cheekSquintLeft', 'cheekSquintRight',
        'cheekRaiserL', 'cheekRaiserR', 'cheekPuffL', 
        'cheekPuffR',
    ],
    'Nose': [
        'noseSneerLeft', 'noseSneerRight', 'noseWrinklerL', 
        'noseWrinklerR',
    ],
    'Mouth': [
        'jawForward', 'jawLeft', 'jawRight', 'jawOpen', 
        'mouthClose', 'mouthFunnel', 'mouthPucker', 
        'mouthRight', 'mouthLeft', 'mouthSmileLeft', 
        'mouthSmileRight', 'mouthFrownRight', 'mouthFrownLeft',
        'mouthDimpleLeft', 'mouthDimpleRight', 'mouthStretchLeft', 
        'mouthStretchRight', 'mouthRollLower', 'mouthRollUpper',
        'mouthShrugLower', 'mouthShrugUpper', 'mouthPressLeft', 
        'mouthPressRight', 'mouthLowerDownLeft', 
        'mouthLowerDownRight', 'mouthUpperUpLeft', 
        'mouthUpperUpRight', 'aa_ah_ax_01', 'aa_02', 'ao_03',
        'ey_eh_uh_04', 'er_05', 'y_iy_ih_ix_06', 'w_uw_07',
        'ow_08', 'aw_09', 'oy_10', 'ay_11', 'h_12', 'r_13', 
        'l_14', 's_z_15', 'sh_ch_jh_zh_16', 'th_dh_17', 
        'f_v_18', 'd_t_n_19', 'k_g_ng_20', 'p_b_m_21',
        'jawDrop', 'jawDropLipTowards', 'jawThrust', 
        'jawSlideLeft', 'jawSlideRight', 'mouthSlideLeft',
        'mouthSlideRight', 'dimplerL', 'dimplerR', 
        'lipCornerPullerL', 'lipCornerPullerR',
        'lipCornerDepressorL', 'lipCornerDepressorR',
        'lipStretcherL', 'lipStretcherR', 'upperLipRaiserL',
        'upperLipRaiserR', 'lowerLipDepressorL', 
        'lowerLipDepressorR', 'chinRaiser', 'lipPressor',
        'pucker', 'funneler', 'lipSuck',
    ],
    'Tongue': [
        'tongueOut', 'tongueBack', 'tongueTwistLeft', 
        'tongueTwistRight', 'tongueLeft', 'tongueRight',
        'tongueWide', 'tongueThin', 'tongueCurlUp', 
        'tongueCurlDown',
    ],
    'Other': []
}


def get_regions_dict() -> Dict[str, str]:
    """
    Get a dictionary mapping shape names to their regions.
    
    Returns:
        Dictionary of shape_name -> region
    """
    region_dict = {}
    for region, shapes in FACE_REGIONS_BASE.items():
        for shape in shapes:
            region_dict[shape] = region
    return region_dict


def get_face_region_items() -> List[tuple]:
    """
    Returns the region names as enum items.
    
    Returns:
        List of (value, label, description) tuples
    """
    region_items = []
    for r in FACE_REGIONS_BASE.keys():
        region_items.append((r, r, r))
    return region_items


# ============================================================
# Modifier Type Mapping
# ============================================================

MOD_TYPE_ICON_DICT = {
    'DATA_TRANSFER': 'MOD_DATA_TRANSFER',
    'MESH_CACHE': 'MOD_MESHDEFORM',
    'MESH_SEQUENCE_CACHE': 'MOD_MESHDEFORM',
    'NORMAL_EDIT': 'MOD_NORMALEDIT',
    'WEIGHTED_NORMAL': 'MOD_NORMALEDIT',
    'UV_PROJECT': 'MOD_UVPROJECT',
    'UV_WARP': 'MOD_UVPROJECT',
    'VERTEX_WEIGHT_EDIT': 'MOD_VERTEX_WEIGHT',
    'VERTEX_WEIGHT_MIX': 'MOD_VERTEX_WEIGHT',
    'VERTEX_WEIGHT_PROXIMITY': 'MOD_VERTEX_WEIGHT',
    'ARRAY': 'MOD_ARRAY',
    'BEVEL': 'MOD_BEVEL',
    'BOOLEAN': 'MOD_BOOLEAN',
    'BUILD': 'MOD_BUILD',
    'DECIMATE': 'MOD_DECIM',
    'EDGE_SPLIT': 'MOD_EDGESPLIT',
    'NODES': 'GEOMETRY_NODES',
    'MASK': 'MOD_MASK',
    'MIRROR': 'MOD_MIRROR',
    'MESH_TO_VOLUME': 'VOLUME_DATA',
    'MULTIRES': 'MOD_MULTIRES',
    'REMESH': 'MOD_REMESH',
    'SCREW': 'MOD_SCREW',
    'SKIN': 'MOD_SKIN',
    'SOLIDIFY': 'MOD_SOLIDIFY',
    'SUBSURF': 'MOD_SUBSURF',
    'TRIANGULATE': 'MOD_TRIANGULATE',
    'VOLUME_TO_MESH': 'VOLUME_DATA',
    'WELD': 'AUTOMERGE_OFF',
    'WIREFRAME': 'MOD_WIREFRAME',
    'ARMATURE': 'MOD_ARMATURE',
    'CAST': 'MOD_CAST',
    'CURVE': 'MOD_CURVE',
    'DISPLACE': 'MOD_DISPLACE',
    'HOOK': 'HOOK',
    'LAPLACIANDEFORM': 'MOD_MESHDEFORM',
    'LATTICE': 'MOD_LATTICE',
    'MESH_DEFORM': 'MOD_MESHDEFORM',
    'SHRINKWRAP': 'MOD_SHRINKWRAP',
    'SIMPLE_DEFORM': 'MOD_SIMPLEDEFORM',
    'SMOOTH': 'MOD_SMOOTH',
    'CORRECTIVE_SMOOTH': 'MOD_SMOOTH',
    'LAPLACIANSMOOTH': 'MOD_SMOOTH',
    'SURFACE_DEFORM': 'MOD_MESHDEFORM',
    'WARP': 'MOD_WARP',
    'WAVE': 'MOD_WAVE',
    'VOLUME_DISPLACE': 'VOLUME_DATA',
    'CLOTH': 'MOD_CLOTH',
    'COLLISION': 'MOD_PHYSICS',
    'DYNAMIC_PAINT': 'MOD_DYNAMICPAINT',
    'EXPLODE': 'MOD_EXPLODE',
    'FLUID': 'MOD_FLUIDSIM',
    'OCEAN': 'MOD_OCEAN',
    'PARTICLE_INSTANCE': 'MOD_PARTICLE_INSTANCE',
    'PARTICLE_SYSTEM': 'MOD_PARTICLES',
    'SOFT_BODY': 'MOD_SOFT',
    'SURFACE': 'MODIFIER',
}


BAKE_MOD_TYPES = [
    'ARMATURE', 'CAST', 'CURVE', 'DISPLACE', 'HOOK', 
    'LAPLACIANDEFORM', 'LATTICE', 'MESH_DEFORM', 
    'SHRINKWRAP', 'SIMPLE_DEFORM', 'SMOOTH', 
    'CORRECTIVE_SMOOTH', 'LAPLACIANSMOOTH', 
    'SURFACE_DEFORM', 'WARP', 'WAVE',
    'VOLUME_DISPLACE', 'DATA_TRANSFER', 'MESH_CACHE', 
    'MESH_SEQUENCE_CACHE', 'VERTEX_WEIGHT_EDIT', 
    'VERTEX_WEIGHT_MIX', 'VERTEX_WEIGHT_PROXIMITY', 
    'CLOTH'
]


GENERATORS = [
    'ARRAY', 'BEVEL', 'BOOLEAN', 'BUILD', 'DECIMATE',
    'EDGE_SPLIT', 'MASK', 'MIRROR', 'MULTIRES', 
    'REMESH', 'SCREW', 'SKIN', 'SOLIDIFY', 'SUBSURF',
    'TRIANGULATE', 'WELD', 'WIREFRAME', 'NODES'
]


DEFORMERS = [
    'ARMATURE', 'CAST', 'CURVE', 'DISPLACE', 'HOOK',
    'LAPLACIANDEFORM', 'LAPLACIANSMOOTH', 'LATTICE',
    'MESH_DEFORM', 'SHRINKWRAP', 'SIMPLE_DEFORM',
    'SMOOTH', 'WARP', 'WAVE', 'SURFACE_DEFORM',
    'CLOTH', 'SOFT_BODY',
]


def get_mod_type_icon(mod_type: str) -> str:
    """Get the icon name for a modifier type."""
    return MOD_TYPE_ICON_DICT.get(mod_type, 'MODIFIER')