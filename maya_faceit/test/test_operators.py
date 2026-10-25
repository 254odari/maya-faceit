# test_operators.py
# Maya Faceit Plugin - Operators Tests
# Converted from Blender to Maya Python 3.11

"""
Operators tests for Faceit Maya plugin.
Tests operator functionality.
"""

import maya.cmds as cmds # type: ignore
from .test_utils import TestScene, TestData, TestAssertions, TestRunner

# Import required modules
from ..core import faceit_utils as futils
from ..core import shape_key_utils as sk_utils
from ..core import vgroup_utils as vg_utils


# ============================================================
# Test Functions
# ============================================================

def test_generate_landmarks():
    """
    Test landmarks generation.
    """
    test_scene = TestScene()
    test_scene.setup()
    
    try:
        # Create test mesh
        mesh = test_scene.create_test_mesh("test_mesh")
        
        # Create landmarks
        landmarks = TestData.create_test_landmarks()
        
        # Verify landmarks
        TestAssertions.assert_obj_exists("facial_landmarks")
        
        # Check vertex count
        vertex_count = cmds.polyEvaluate(landmarks, vertex=True)
        TestAssertions.assert_equal(vertex_count > 0, True)
        
    finally:
        test_scene.teardown()
    
    return True


def test_generate_rig():
    """
    Test rig generation.
    """
    test_scene = TestScene()
    test_scene.setup()
    
    try:
        # Create test mesh
        mesh = test_scene.create_test_mesh("test_mesh")
        
        # Create vertex groups
        TestData.create_test_vertex_groups(mesh)
        
        # Create landmarks
        landmarks = TestData.create_test_landmarks()
        
        # Create core data
        if not cmds.objExists("faceit_core_data"):
            cmds.createNode("transform", name="faceit_core_data")
            cmds.addAttr("faceit_core_data", ln="armature", dt="string")
            cmds.addAttr("faceit_core_data", ln="faceit_objects", dt="string")
        
        # Register object
        cmds.setAttr("faceit_core_data.faceit_objects", mesh, type="string")
        
        # Create rig
        rig = cmds.joint(name="FaceitRig", position=[0, 0, 0])
        cmds.setAttr("faceit_core_data.armature", rig, type="string")
        
        # Verify rig
        TestAssertions.assert_obj_exists("FaceitRig")
        
        # Check if armature is set
        armature = cmds.getAttr("faceit_core_data.armature") or ""
        TestAssertions.assert_equal(armature, "FaceitRig")
        
    finally:
        test_scene.teardown()
    
    return True


def test_bind_weights():
    """
    Test weight binding.
    """
    test_scene = TestScene()
    test_scene.setup()
    
    try:
        # Create test mesh
        mesh = test_scene.create_test_mesh("test_mesh")
        
        # Create vertex groups
        TestData.create_test_vertex_groups(mesh)
        
        # Create armature
        armature = test_scene.create_test_armature("test_armature")
        
        # Bind mesh to armature
        cmds.select(mesh, armature)
        
        # Create skin cluster
        skin_cluster = cmds.skinCluster(
            armature,
            mesh,
            toSelectedBones=True,
            skinMethod=0,
            normalizeWeights=1
        )[0]
        
        # Verify skin cluster
        TestAssertions.assert_obj_exists(skin_cluster)
        
        # Check influences
        influences = cmds.skinCluster(skin_cluster, query=True, influence=True) or []
        TestAssertions.assert_equal(len(influences) > 0, True)
        
    finally:
        test_scene.teardown()
    
    return True


def test_expression_animation():
    """
    Test expression animation.
    """
    test_scene = TestScene()
    test_scene.setup()
    
    try:
        # Create test mesh
        mesh = test_scene.create_test_mesh("test_mesh")
        
        # Create blend shapes
        targets = test_scene.create_test_blend_shapes(mesh, 3)
        
        # Create expression data
        expr_data = TestScene().create_test_expression_data(3)
        expressions = expr_data['expressions']
        
        # Create action
        action = cmds.createNode("animCurveUA", name="test_action")
        blend_node = sk_utils.get_blend_shape_node(mesh)
        
        if blend_node:
            cmds.addAttr(blend_node, ln="currentAction", dt="string")
            cmds.setAttr(f"{blend_node}.currentAction", action, type="string")
            
            # Add keyframes for each expression
            for i, expr in enumerate(expressions):
                frame = expr['frame']
                target = targets[i] if i < len(targets) else None
                
                if target and cmds.attributeQuery(target, node=blend_node, exists=True):
                    cmds.setKeyframe(blend_node, attribute=target, t=frame - 9, v=0)
                    cmds.setKeyframe(blend_node, attribute=target, t=frame, v=1)
                    cmds.setKeyframe(blend_node, attribute=target, t=frame + 1, v=0)
        
        # Verify animation
        cmds.currentTime(10)
        
        # Check if action is set
        current_action = cmds.getAttr(f"{blend_node}.currentAction") or ""
        TestAssertions.assert_equal(current_action, "test_action")
        
    finally:
        test_scene.teardown()
    
    return True


def test_corrective_shape_keys():
    """
    Test corrective shape keys.
    """
    test_scene = TestScene()
    test_scene.setup()
    
    try:
        # Create test mesh
        mesh = test_scene.create_test_mesh("test_mesh")
        
        # Create blend shapes
        targets = test_scene.create_test_blend_shapes(mesh, 3)
        
        # Create corrective shape key
        blend_node = sk_utils.get_blend_shape_node(mesh)
        
        if blend_node:
            # Create corrective target
            corr_name = "faceit_cc_test"
            
            # Create temp mesh for correction
            temp_mesh = cmds.duplicate(mesh, name=f"{mesh}_corr_temp")[0]
            
            # Modify vertices
            vertices = cmds.ls(f"{temp_mesh}.vtx[*]", flatten=True)
            for vtx in vertices[:5]:
                pos = cmds.xform(vtx, query=True, objectSpace=True, translation=True)
                if pos:
                    cmds.xform(vtx, objectSpace=True, translation=[pos[0] + 0.05, pos[1], pos[2]])
            
            # Add as blend shape target
            cmds.blendShape(blend_node, edit=True, target=(mesh, 0, temp_mesh, 1.0))
            
            # Rename target
            weight_attrs = cmds.listAttr(f"{blend_node}.weight", multi=True) or []
            weight_attrs = [a for a in weight_attrs if a.startswith('weight[')]
            if weight_attrs:
                cmds.aliasAttr(corr_name, f"{blend_node}.{weight_attrs[-1]}")
            
            cmds.delete(temp_mesh)
            
            # Verify corrective shape key
            TestAssertions.assert_equal(
                cmds.attributeQuery(corr_name, node=blend_node, exists=True),
                True
            )
        
    finally:
        test_scene.teardown()
    
    return True


# ============================================================
# Test Suite
# ============================================================

def run_operators_tests():
    """
    Run all operators tests.
    
    Returns:
        Test results
    """
    test_runner = TestRunner()
    
    test_suite = [
        test_generate_landmarks,
        test_generate_rig,
        test_bind_weights,
        test_expression_animation,
        test_corrective_shape_keys,
    ]
    
    results = test_runner.run_suite(test_suite)
    test_runner.print_results()
    
    return results


if __name__ == "__main__":
    run_operators_tests()