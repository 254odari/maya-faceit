# __init__.py
# Maya Faceit Plugin - Core Module
# Version: 1.0.0

"""
Faceit Core Module for Maya
===========================

This module provides core functionality for the Faceit facial rigging system.
It contains data definitions, utilities, and shape management functionality.

Main Components:
    - ARKit expression shape definitions
    - Faceit data structures (bones, vertex groups, regions)
    - Detection and matching utilities
    - Shape key management utilities
    - Rig and landmark utilities
    - Expression and bake utilities
"""

__version__ = "1.0.0"
__author__ = "Faceit Team"

# ============================================================
# Module Imports - All Submodules
# ============================================================

from . import arkit_shapes
from . import detection_manager
from . import faceit_data
from . import faceit_utils
from . import faceit_callback
from . import faceit_handlers
from . import shape_key_utils
from . import vgroup_utils
from . import mesh_utils
from . import modifier_utils
from . import pose_utils
from . import fc_dr_utils
from . import retarget_list_base
from . import retarget_list_utils
from . import bake_utils
from . import rig_utils
from . import landmark_utils
from . import expression_utils
from . import corrective_utils
from . import mirror_utils
from . import scale_utils
from . import animation_utils
from . import constraint_utils
from . import driver_utils
from . import skin_utils
from . import weight_utils


# ============================================================
# Imports from arkit_shapes
# ============================================================

from .arkit_shapes import (
    ARKIT,
    FACECAP,
    EPIC,
    A2F,
    PHONEMES,
    TONGUE,
    get_arkit_shape_data,
    get_face_cap_shape_data,
    get_epic_shape_data,
    get_a2f_shape_data,
    get_tongue_shape_data,
    get_phonemes_shape_data,
    get_shape_data_for_mocap_engine,
    get_all_expression_sets,
)


# ============================================================
# Imports from detection_manager
# ============================================================

from .detection_manager import (
    get_expression_name_double_entries,
    detect_shape,
    find_best_match,
)


# ============================================================
# Imports from faceit_data
# ============================================================

from .faceit_data import (
    PLUGIN_VERSION,
    get_faceit_current_version,
    get_addon_dir,
    get_retargeting_presets,
    get_expression_presets,
    get_rig_file,
    get_control_rig_file,
    get_landmarks_file,
    FACEIT_BONES,
    FACEIT_CTRL_BONES,
    FACEIT_VERTEX_GROUPS,
    get_list_faceit_groups,
    FACE_REGIONS_BASE,
    get_regions_dict,
    get_face_region_items,
    get_rigify_bone_from_old_name,
    MOD_TYPE_ICON_DICT,
    BAKE_MOD_TYPES,
    GENERATORS,
    DEFORMERS,
    get_mod_type_icon,
)


# ============================================================
# Imports from faceit_utils
# ============================================================

from .faceit_utils import (
    get_object,
    clear_active_object,
    set_active_object,
    clear_object_selection,
    get_selected_objects,
    get_faceit_objects_list,
    get_main_faceit_object,
    get_faceit_objects,
    add_faceit_object,
    remove_faceit_object,
    get_faceit_armature,
    get_faceit_control_armature,
    get_faceit_control_armatures,
    is_faceit_original_armature,
    get_rig_type,
    using_rigify_armature,
    is_armature_bound_to_registered_objects,
    get_faceit_collection,
    get_layer_collection,
    set_hide_obj,
    get_hide_obj,
    set_hidden_state_object,
    set_hidden_states,
    get_hidden_states,
    is_collection_visible,
    save_scene_state,
    restore_scene_state,
    get_object_mode_from_context_mode,
    get_object_mode,
    set_object_mode,
    exit_nla_tweak_mode,
    get_median_pos,
    get_center_pos,
    get_action_frame_range,
    set_action_frame_range,
    ui_refresh_properties,
    ui_refresh_view_3d,
    ui_refresh_all,
    remove_item_from_collection_prop,
    find_collection_in_children,
    duplicate_obj,
    get_maya_version,
    is_maya_version_at_least,
)


# ============================================================
# Imports from faceit_callback
# ============================================================

from .faceit_callback import (
    register_faceit_callbacks,
    unregister_faceit_callbacks,
    refresh_faceit_properties_panel,
    update_faceit_viewport_overlay,
    set_pending_update,
)


# ============================================================
# Imports from faceit_handlers
# ============================================================

from .faceit_handlers import (
    register_faceit_handlers,
    unregister_faceit_handlers,
    FaceitHandlerManager,
    get_handler_manager,
)


# ============================================================
# Imports from shape_key_utils
# ============================================================

from .shape_key_utils import (
    has_shape_keys,
    get_blend_shape_node,
    get_blend_shape_targets,
    get_shape_key_names_from_objects,
    get_shape_key_names_from_action,
    get_shape_key_value,
    set_shape_key_value,
    set_rest_position_shape_keys,
    create_shape_key_from_mesh,
    create_shape_key_from_delta,
    get_mesh_data,
    apply_matrix_to_all_mesh_data,
    store_shape_keys,
    apply_stored_shape_keys,
    remove_all_sk_apply_basis,
    get_shape_keys_from_faceit_objects_enum,
    get_enum_shape_key_actions,
    get_all_shape_key_actions,
    set_slider_max,
    set_slider_min,
    keyframe_shape_key,
    get_shape_key_animation,
)


# ============================================================
# Imports from vgroup_utils
# ============================================================

from .vgroup_utils import (
    get_vertex_groups,
    get_vertex_group,
    create_vertex_group,
    delete_vertex_group,
    get_vertex_group_weight,
    set_vertex_group_weight,
    assign_vertex_grp,
    remove_verts_from_grp,
    get_verts_in_vgroup,
    get_vertex_groups_from_objects,
    get_objects_with_vertex_group,
    remove_all_weight,
    remove_zero_weights_from_verts,
    remove_unused_vertex_groups,
    remove_unused_vertex_groups_thresh,
    copy_vertex_groups,
    store_vertex_group,
    apply_vertex_group,
    get_deform_bones_from_armature,
    remove_faceit_vertex_grps,
    remove_deform_vertex_grps,
    get_faceit_vertex_grps,
    has_verts_without_grps,
    invert_vertex_group_weights,
    vertex_group_sanity_check,
    remove_vgroups_from_verts,
    save_vertex_group_data,
    restore_vertex_group_data,
)


# ============================================================
# Imports from mesh_utils
# ============================================================

from .mesh_utils import (
    get_max_dim_in_direction,
    get_object_center,
    get_mesh_vertices,
    get_mesh_data,
    is_inside_dot,
    closest_point_on_mesh,
    get_face_normal_at_point,
    select_vertices,
    select_vertices_bmesh,
    get_selected_vertices,
    GeometryIslands,
    SelectionIslands,
    apply_matrix_to_all_mesh_data,
    get_vertex_count,
    get_edge_count,
    get_face_count,
    get_bounding_box,
    create_mesh_from_vertices,
    duplicate_mesh,
)


# ============================================================
# Imports from modifier_utils
# ============================================================

from .modifier_utils import (
    add_faceit_armature_modifier,
    get_faceit_armature_modifier,
    remove_faceit_armature_modifier,
    reorder_armature_in_modifier_stack,
    get_modifiers_of_type,
    move_above_generators,
    set_bake_modifier_item,
    set_mod_bake,
    populate_bake_modifier_items,
    restore_bake_modifiers,
    bind_valid_bake_modifiers,
    apply_modifier,
    apply_all_modifiers,
    restore_modifier_order,
    set_bake_modifier_properties,
    get_modifier_type_icon,
    is_bakeable_modifier,
    is_generator_modifier,
    save_modifier_data_to_scene,
    load_modifier_data_from_scene,
)


# ============================================================
# Imports from pose_utils
# ============================================================

from .pose_utils import (
    reset_pose,
    reset_pb,
    is_pb_in_rest_pose,
    get_bone_matrix,
    set_bone_matrix,
    get_bone_edit_roll,
    set_bone_edit_roll,
    copy_pose,
    paste_pose,
    mirror_pose,
    keyframe_pose,
    clear_keyframes,
    select_pose_bones,
    get_selected_pose_bones,
    get_pose_bones_in_rig,
    blend_poses,
    apply_pose_to_bones,
    get_bone_constraints,
    remove_bone_constraints,
    set_joint_orientation,
    get_joint_orientation,
    set_joint_rotation_order,
    get_joint_rotation_order,
)


# ============================================================
# Imports from fc_dr_utils
# ============================================================

from .fc_dr_utils import (
    get_fcurve_from_bpy_struct,
    get_fcurve_modifiers,
    clear_all_fc_modifiers,
    populate_modifiers,
    get_keyframe_meta_data,
    populate_kf_meta_data,
    clear_invalid_drivers,
    kf_data_to_numpy_array,
    populate_keyframe_points_from_np_array,
    clear_fcurve_kf_points,
    join_np_array_kf_data,
    sampled_points_to_numpy_array,
    get_fcurve_properties,
    populate_fcurve_properties,
    copy_fcurve_data,
    populate_stored_fcurve_data,
    copy_driver_data,
    populate_driver_data,
)


# ============================================================
# Imports from retarget_list_base
# ============================================================

from .retarget_list_base import (
    TargetShapes,
    RetargetShapesBase,
    FaceRegionsBase,
    ResetRegionsOperatorBase,
    SetDefaultRegionsBase,
    DrawRegionsFilterBase,
    RetargetingBase,
    RetargetShapesListBase,
    DrawTargetShapesListBase,
    EditTargetShapeBase,
    RemoveTargetShapeBase,
    ClearTargetShapeBase,
)


# ============================================================
# Imports from retarget_list_utils
# ============================================================

from .retarget_list_utils import (
    get_index_from_path,
    get_index_of_parent_collection_item,
    get_index_of_collection_item,
    get_all_set_target_shapes,
    get_all_set_target_shapes_regions,
    get_target_shapes_dict,
    is_target_shape_double,
    eval_target_shapes,
    set_base_regions_from_dict,
    get_all_available_shapes_names,
    get_target_shape_keys,
    get_invalid_target_shapes,
    are_target_shapes_valid,
    target_shape_key_in_registered_objects,
    create_retarget_item,
    remove_retarget_item,
    clear_retarget_list,
    find_retarget_item,
    get_retarget_item_index,
    add_target_shape_to_item,
    remove_target_shape_from_item,
    clear_target_shapes_from_item,
    get_target_shapes_for_source,
    get_filtered_retarget_items,
    sort_retarget_items,
    get_side,
    poll_side_in_expression_name,
    get_mirror_name,
    load_retarget_data_from_scene,
    save_retarget_data_to_scene,
)


# ============================================================
# Imports from bake_utils
# ============================================================

from .bake_utils import (
    bake_modifier,
    bake_all_modifiers,
    bake_blend_shapes,
    bake_expression_to_blend_shape,
    bake_current_pose_to_blend_shape,
    bake_shape_key_delta,
    convert_blend_shape_to_shape_key,
    bake_corrective_shape_key,
    bake_all_expressions,
    bake_corrective_shape_keys,
    clear_all_blend_shapes,
    set_blend_shape_weight,
)


# ============================================================
# Imports from rig_utils
# ============================================================

from .rig_utils import (
    get_faceit_control_rig,
    get_faceit_bones,
    get_control_bones,
    get_deform_bones,
    get_bone_children,
    get_bone_parent,
    get_bone_translation,
    get_bone_rotation,
    get_bone_scale,
    set_bone_translation,
    set_bone_rotation,
    validate_rig,
    get_rig_dimensions,
    mirror_bone_name,
    mirror_bone_transform,
)


# ============================================================
# Imports from landmark_utils
# ============================================================

from .landmark_utils import (
    ARKIT_LANDMARKS,
    FACEIT_LANDMARKS,
    create_landmark,
    create_landmark_from_vertex,
    create_landmarks_from_vertices,
    get_landmarks,
    get_landmark_position,
    set_landmark_position,
    delete_landmark,
    delete_all_landmarks,
    snap_landmark_to_mesh,
    snap_all_landmarks_to_mesh,
    export_landmarks,
    import_landmarks,
    lock_3d_view_front,
    unlock_3d_view,
)


# ============================================================
# Imports from expression_utils
# ============================================================

from .expression_utils import (
    get_expression_data,
    save_expression_data,
    get_expression_by_name,
    get_expression_by_frame,
    get_current_expression,
    go_to_expression_frame,
    go_to_current_expression_frame,
    get_expression_frames,
    get_expression_names,
    get_next_expression,
    get_previous_expression,
    add_expression,
    remove_expression,
    clear_all_expressions,
    get_expression_side,
    is_left_expression,
    is_right_expression,
    is_neutral_expression,
    get_mirror_expression_name,
)


# ============================================================
# Imports from corrective_utils
# ============================================================

from .corrective_utils import (
    CORRECTIVE_SK_PREFIX,
    create_corrective_shape_key,
    evaluate_corrective_shape_key,
    get_corrective_shape_keys,
    remove_corrective_shape_key,
    clear_all_corrective_shape_keys,
    bake_corrective_shape_key_to_mesh,
    mirror_corrective_shape_key,
    get_corrective_data,
    is_corrective_shape_key,
    get_expression_from_corrective_sk,
)


# ============================================================
# Imports from mirror_utils
# ============================================================

from .mirror_utils import (
    get_mirror_name,
    is_side_specific,
    mirror_bone_animation,
    mirror_all_bone_animation,
    mirror_expression,
    mirror_all_expressions,
    mirror_shape_key,
    mirror_blend_shape_target,
    mirror_name_list,
    get_mirror_pairs,
    is_mirror_pair,
)


# ============================================================
# Imports from scale_utils
# ============================================================

from .scale_utils import (
    scale_action,
    scale_action_to_rig,
    get_action_dimensions,
    scale_pose,
    scale_all_poses,
    scale_eye_animation,
    scale_eye_look_animation,
    amplify_pose,
    amplify_all_poses,
)


# ============================================================
# Imports from constraint_utils
# ============================================================

from .constraint_utils import (
    create_constraint,
    create_faceit_constraints,
    get_constraints_on_bone,
    get_constraint_targets,
    set_constraint_influence,
    get_constraint_influence,
    animate_constraint_influence,
    animate_constraint_influence_curve,
    remove_constraints_from_bone,
    remove_constraints_by_type,
    enable_constraint,
    is_constraint_enabled,
    bake_constraint,
    bake_all_constraints_on_object,
    get_constraint_defaults,
)


# ============================================================
# Imports from driver_utils
# ============================================================

from .driver_utils import (
    create_driver,
    create_expression_driver,
    get_driver_on_attribute,
    remove_driver,
    get_driver_expression,
    set_driver_expression,
    get_driver_variables,
    add_driver_variable,
    remove_driver_variable,
    update_driver,
    create_faceit_mouth_lock_driver,
    create_faceit_eye_driver,
)


# ============================================================
# Imports from skin_utils
# ============================================================

from .skin_utils import (
    create_skin_cluster,
    add_joints_to_skin_cluster,
    remove_joints_from_skin_cluster,
    bind_skin_to_rig,
    get_skin_cluster,
    get_skin_influences,
    get_skin_weights,
    set_skin_weight,
    normalize_skin_weights,
    prune_skin_weights,
    copy_skin_weights,
    transfer_skin_weights,
    mirror_skin_weights,
    smooth_skin_weights,
    export_skin_weights,
    import_skin_weights,
)


# ============================================================
# Imports from weight_utils
# ============================================================

from .weight_utils import (
    paint_weight,
    get_weight_at_vertex,
    get_all_weights_at_vertex,
    transfer_weights_between_joints,
    mirror_weights,
    smooth_weights,
    get_vertex_neighbors,
    lock_weights,
    unlock_weights,
    normalize_weights,
    clamp_weights,
    export_weights,
    import_weights,
)


# ============================================================
# Module Constants
# ============================================================

EXPRESSION_CATEGORIES = {
    'eyeBlink': 'Eyes',
    'eyeSquint': 'Eyes',
    'eyeLook': 'Eyes',
    'eyeWide': 'Eyes',
    'brow': 'Brows',
    'mouth': 'Mouth',
    'jaw': 'Mouth',
    'cheek': 'Cheeks',
    'nose': 'Nose',
    'tongue': 'Tongue',
}

MAYA_BLEND_SHAPE_NODE_TYPE = 'blendShape'
MAYA_JOINT_NODE_TYPE = 'joint'
MAYA_MESH_NODE_TYPE = 'mesh'


# ============================================================
# Module Initialization
# ============================================================

def initialize_core():
    """
    Initialize the core module when Maya starts.
    Called by the main Faceit plugin.
    """
    print(f"Faceit Core Module v{__version__} initialized")
    _ensure_core_data()


def uninitialize_core():
    """
    Clean up when Maya shuts down.
    Called by the main Faceit plugin.
    """
    print("Faceit Core Module uninitialized")


def _ensure_core_data():
    """
    Ensure core data structures exist in the scene.
    """
    import maya.cmds as cmds
    
    if not cmds.objExists("faceit_core_data"):
        cmds.createNode("transform", name="faceit_core_data")
        
        cmds.addAttr("faceit_core_data", ln="version", dt="string")
        cmds.setAttr("faceit_core_data.version", __version__, type="string")
        
        cmds.addAttr("faceit_core_data", ln="expression_names", dt="string")
        cmds.addAttr("faceit_core_data", ln="expression_frames", dt="string")
        cmds.addAttr("faceit_core_data", ln="expression_sides", dt="string")
        cmds.addAttr("faceit_core_data", ln="expression_procedural", dt="string")
        cmds.addAttr("faceit_core_data", ln="current_index", attributeType="long", min=0, defaultValue=0)
        cmds.addAttr("faceit_core_data", ln="armature", dt="string")
        cmds.addAttr("faceit_core_data", ln="control_rig", dt="string")
        cmds.addAttr("faceit_core_data", ln="faceit_objects", dt="string")
        cmds.addAttr("faceit_core_data", ln="shapes_generated", attributeType="long", min=0, defaultValue=0)
        cmds.addAttr("faceit_core_data", ln="pending_updates", attributeType="long", min=0, defaultValue=0)
        cmds.addAttr("faceit_core_data", ln="head_target", dt="string")
        cmds.addAttr("faceit_core_data", ln="head_action", dt="string")
        cmds.addAttr("faceit_core_data", ln="corrective_data", dt="string")
        cmds.addAttr("faceit_core_data", ln="current_object_index", attributeType="long", min=0, defaultValue=0)


# ============================================================
# Module Exports
# ============================================================

__all__ = [
    '__version__',
    'initialize_core',
    'uninitialize_core',
    
    # arkit_shapes
    'ARKIT', 'FACECAP', 'EPIC', 'A2F', 'PHONEMES', 'TONGUE',
    'get_arkit_shape_data', 'get_face_cap_shape_data', 'get_epic_shape_data',
    'get_a2f_shape_data', 'get_tongue_shape_data', 'get_phonemes_shape_data',
    'get_shape_data_for_mocap_engine', 'get_all_expression_sets',
    
    # detection_manager
    'get_expression_name_double_entries', 'detect_shape', 'find_best_match',
    
    # faceit_data
    'PLUGIN_VERSION', 'get_faceit_current_version', 'get_addon_dir',
    'get_retargeting_presets', 'get_expression_presets', 'get_rig_file',
    'get_control_rig_file', 'get_landmarks_file', 'FACEIT_BONES',
    'FACEIT_CTRL_BONES', 'FACEIT_VERTEX_GROUPS', 'get_list_faceit_groups',
    'FACE_REGIONS_BASE', 'get_regions_dict', 'get_face_region_items',
    'get_rigify_bone_from_old_name', 'MOD_TYPE_ICON_DICT', 'BAKE_MOD_TYPES',
    'GENERATORS', 'DEFORMERS', 'get_mod_type_icon',
    
    # faceit_utils
    'get_object', 'clear_active_object', 'set_active_object',
    'clear_object_selection', 'get_selected_objects', 'get_faceit_objects_list',
    'get_main_faceit_object', 'get_faceit_objects', 'add_faceit_object',
    'remove_faceit_object', 'get_faceit_armature', 'get_faceit_control_armature',
    'get_faceit_control_armatures', 'is_faceit_original_armature',
    'get_rig_type', 'using_rigify_armature', 'is_armature_bound_to_registered_objects',
    'get_faceit_collection', 'get_layer_collection', 'set_hide_obj',
    'get_hide_obj', 'set_hidden_state_object', 'set_hidden_states',
    'get_hidden_states', 'is_collection_visible', 'save_scene_state',
    'restore_scene_state', 'get_object_mode_from_context_mode',
    'get_object_mode', 'set_object_mode', 'exit_nla_tweak_mode',
    'get_median_pos', 'get_center_pos', 'get_action_frame_range',
    'set_action_frame_range', 'ui_refresh_properties', 'ui_refresh_view_3d',
    'ui_refresh_all', 'remove_item_from_collection_prop',
    'find_collection_in_children', 'duplicate_obj', 'get_maya_version',
    'is_maya_version_at_least',
    
    # faceit_callback
    'register_faceit_callbacks', 'unregister_faceit_callbacks',
    'refresh_faceit_properties_panel', 'update_faceit_viewport_overlay',
    'set_pending_update', 'get_handler_manager',
    
    # faceit_handlers
    'register_faceit_handlers', 'unregister_faceit_handlers',
    'FaceitHandlerManager',
    
    # shape_key_utils
    'has_shape_keys', 'get_blend_shape_node', 'get_blend_shape_targets',
    'get_shape_key_names_from_objects', 'get_shape_key_names_from_action',
    'get_shape_key_value', 'set_shape_key_value',
    'set_rest_position_shape_keys', 'create_shape_key_from_mesh',
    'create_shape_key_from_delta', 'get_mesh_data',
    'apply_matrix_to_all_mesh_data', 'store_shape_keys',
    'apply_stored_shape_keys', 'remove_all_sk_apply_basis',
    'get_shape_keys_from_faceit_objects_enum', 'get_enum_shape_key_actions',
    'get_all_shape_key_actions', 'set_slider_max', 'set_slider_min',
    'keyframe_shape_key', 'get_shape_key_animation',
    
    # vgroup_utils
    'get_vertex_groups', 'get_vertex_group', 'create_vertex_group',
    'delete_vertex_group', 'get_vertex_group_weight',
    'set_vertex_group_weight', 'assign_vertex_grp', 'remove_verts_from_grp',
    'get_verts_in_vgroup', 'get_vertex_groups_from_objects',
    'get_objects_with_vertex_group', 'remove_all_weight',
    'remove_zero_weights_from_verts', 'remove_unused_vertex_groups',
    'remove_unused_vertex_groups_thresh', 'copy_vertex_groups',
    'store_vertex_group', 'apply_vertex_group', 'get_deform_bones_from_armature',
    'remove_faceit_vertex_grps', 'remove_deform_vertex_grps',
    'get_faceit_vertex_grps', 'has_verts_without_grps',
    'invert_vertex_group_weights', 'vertex_group_sanity_check',
    'remove_vgroups_from_verts', 'save_vertex_group_data',
    'restore_vertex_group_data',
    
    # mesh_utils
    'get_max_dim_in_direction', 'get_object_center', 'get_mesh_vertices',
    'get_mesh_data', 'is_inside_dot', 'closest_point_on_mesh',
    'get_face_normal_at_point', 'select_vertices', 'select_vertices_bmesh',
    'get_selected_vertices', 'GeometryIslands', 'SelectionIslands',
    'apply_matrix_to_all_mesh_data', 'get_vertex_count', 'get_edge_count',
    'get_face_count', 'get_bounding_box', 'create_mesh_from_vertices',
    'duplicate_mesh',
    
    # modifier_utils
    'add_faceit_armature_modifier', 'get_faceit_armature_modifier',
    'remove_faceit_armature_modifier', 'reorder_armature_in_modifier_stack',
    'get_modifiers_of_type', 'move_above_generators', 'set_bake_modifier_item',
    'set_mod_bake', 'populate_bake_modifier_items', 'restore_bake_modifiers',
    'bind_valid_bake_modifiers', 'apply_modifier', 'apply_all_modifiers',
    'restore_modifier_order', 'set_bake_modifier_properties',
    'get_modifier_type_icon', 'is_bakeable_modifier', 'is_generator_modifier',
    'save_modifier_data_to_scene', 'load_modifier_data_from_scene',
    
    # pose_utils
    'reset_pose', 'reset_pb', 'is_pb_in_rest_pose', 'get_bone_matrix',
    'set_bone_matrix', 'get_bone_edit_roll', 'set_bone_edit_roll',
    'copy_pose', 'paste_pose', 'mirror_pose', 'keyframe_pose',
    'clear_keyframes', 'select_pose_bones', 'get_selected_pose_bones',
    'get_pose_bones_in_rig', 'blend_poses', 'apply_pose_to_bones',
    'get_bone_constraints', 'remove_bone_constraints', 'set_joint_orientation',
    'get_joint_orientation', 'set_joint_rotation_order',
    'get_joint_rotation_order',
    
    # fc_dr_utils
    'get_fcurve_from_bpy_struct', 'get_fcurve_modifiers',
    'clear_all_fc_modifiers', 'populate_modifiers', 'get_keyframe_meta_data',
    'populate_kf_meta_data', 'clear_invalid_drivers', 'kf_data_to_numpy_array',
    'populate_keyframe_points_from_np_array', 'clear_fcurve_kf_points',
    'join_np_array_kf_data', 'sampled_points_to_numpy_array',
    'get_fcurve_properties', 'populate_fcurve_properties', 'copy_fcurve_data',
    'populate_stored_fcurve_data', 'copy_driver_data', 'populate_driver_data',
    
    # retarget_list_base
    'TargetShapes', 'RetargetShapesBase', 'FaceRegionsBase',
    'ResetRegionsOperatorBase', 'SetDefaultRegionsBase',
    'DrawRegionsFilterBase', 'RetargetingBase', 'RetargetShapesListBase',
    'DrawTargetShapesListBase', 'EditTargetShapeBase', 'RemoveTargetShapeBase',
    'ClearTargetShapeBase',
    
    # retarget_list_utils
    'get_index_from_path', 'get_index_of_parent_collection_item',
    'get_index_of_collection_item', 'get_all_set_target_shapes',
    'get_all_set_target_shapes_regions', 'get_target_shapes_dict',
    'is_target_shape_double', 'eval_target_shapes', 'set_base_regions_from_dict',
    'get_all_available_shapes_names', 'get_target_shape_keys',
    'get_invalid_target_shapes', 'are_target_shapes_valid',
    'target_shape_key_in_registered_objects', 'create_retarget_item',
    'remove_retarget_item', 'clear_retarget_list', 'find_retarget_item',
    'get_retarget_item_index', 'add_target_shape_to_item',
    'remove_target_shape_from_item', 'clear_target_shapes_from_item',
    'get_target_shapes_for_source', 'get_filtered_retarget_items',
    'sort_retarget_items', 'get_side', 'poll_side_in_expression_name',
    'get_mirror_name', 'load_retarget_data_from_scene',
    'save_retarget_data_to_scene',
    
    # bake_utils
    'bake_modifier', 'bake_all_modifiers', 'bake_blend_shapes',
    'bake_expression_to_blend_shape', 'bake_current_pose_to_blend_shape',
    'bake_shape_key_delta', 'convert_blend_shape_to_shape_key',
    'bake_corrective_shape_key', 'bake_all_expressions',
    'bake_corrective_shape_keys', 'clear_all_blend_shapes',
    'set_blend_shape_weight',
    
    # rig_utils
    'get_faceit_control_rig', 'get_faceit_bones', 'get_control_bones',
    'get_deform_bones', 'get_bone_children', 'get_bone_parent',
    'get_bone_translation', 'get_bone_rotation', 'get_bone_scale',
    'set_bone_translation', 'set_bone_rotation', 'validate_rig',
    'get_rig_dimensions', 'mirror_bone_name', 'mirror_bone_transform',
    
    # landmark_utils
    'ARKIT_LANDMARKS', 'FACEIT_LANDMARKS', 'create_landmark',
    'create_landmark_from_vertex', 'create_landmarks_from_vertices',
    'get_landmarks', 'get_landmark_position', 'set_landmark_position',
    'delete_landmark', 'delete_all_landmarks', 'snap_landmark_to_mesh',
    'snap_all_landmarks_to_mesh', 'export_landmarks', 'import_landmarks',
    'lock_3d_view_front', 'unlock_3d_view',
    
    # expression_utils
    'get_expression_data', 'save_expression_data', 'get_expression_by_name',
    'get_expression_by_frame', 'get_current_expression',
    'go_to_expression_frame', 'go_to_current_expression_frame',
    'get_expression_frames', 'get_expression_names', 'get_next_expression',
    'get_previous_expression', 'add_expression', 'remove_expression',
    'clear_all_expressions', 'get_expression_side', 'is_left_expression',
    'is_right_expression', 'is_neutral_expression',
    'get_mirror_expression_name',
    
    # corrective_utils
    'CORRECTIVE_SK_PREFIX', 'create_corrective_shape_key',
    'evaluate_corrective_shape_key', 'get_corrective_shape_keys',
    'remove_corrective_shape_key', 'clear_all_corrective_shape_keys',
    'bake_corrective_shape_key_to_mesh', 'mirror_corrective_shape_key',
    'get_corrective_data', 'is_corrective_shape_key',
    'get_expression_from_corrective_sk',
    
    # mirror_utils
    'get_mirror_name', 'is_side_specific', 'mirror_bone_animation',
    'mirror_all_bone_animation', 'mirror_expression',
    'mirror_all_expressions', 'mirror_shape_key',
    'mirror_blend_shape_target', 'mirror_name_list', 'get_mirror_pairs',
    'is_mirror_pair',
    
    # scale_utils
    'scale_action', 'scale_action_to_rig', 'get_action_dimensions',
    'scale_pose', 'scale_all_poses', 'scale_eye_animation',
    'scale_eye_look_animation', 'amplify_pose', 'amplify_all_poses',
    
    # constraint_utils
    'create_constraint', 'create_faceit_constraints',
    'get_constraints_on_bone', 'get_constraint_targets',
    'set_constraint_influence', 'get_constraint_influence',
    'animate_constraint_influence', 'animate_constraint_influence_curve',
    'remove_constraints_from_bone', 'remove_constraints_by_type',
    'enable_constraint', 'is_constraint_enabled', 'bake_constraint',
    'bake_all_constraints_on_object', 'get_constraint_defaults',
    
    # driver_utils
    'create_driver', 'create_expression_driver', 'get_driver_on_attribute',
    'remove_driver', 'get_driver_expression', 'set_driver_expression',
    'get_driver_variables', 'add_driver_variable', 'remove_driver_variable',
    'update_driver', 'create_faceit_mouth_lock_driver',
    'create_faceit_eye_driver',
    
    # skin_utils
    'create_skin_cluster', 'add_joints_to_skin_cluster',
    'remove_joints_from_skin_cluster', 'bind_skin_to_rig',
    'get_skin_cluster', 'get_skin_influences', 'get_skin_weights',
    'set_skin_weight', 'normalize_skin_weights', 'prune_skin_weights',
    'copy_skin_weights', 'transfer_skin_weights', 'mirror_skin_weights',
    'smooth_skin_weights', 'export_skin_weights', 'import_skin_weights',
    
    # weight_utils
    'paint_weight', 'get_weight_at_vertex', 'get_all_weights_at_vertex',
    'transfer_weights_between_joints', 'mirror_weights', 'smooth_weights',
    'get_vertex_neighbors', 'lock_weights', 'unlock_weights',
    'normalize_weights', 'clamp_weights', 'export_weights', 'import_weights',
    
    # Constants
    'EXPRESSION_CATEGORIES',
    'MAYA_BLEND_SHAPE_NODE_TYPE',
    'MAYA_JOINT_NODE_TYPE',
    'MAYA_MESH_NODE_TYPE',
]