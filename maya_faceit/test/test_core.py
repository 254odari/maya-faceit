# test_core.py
# Maya Faceit Plugin - Core Tests
# Converted from Blender to Maya Python 3.11

"""
Core tests for Faceit Maya plugin.
Tests core functionality.
"""

import maya.cmds as cmds # type: ignore
import maya.api.OpenMaya as om2 # type: ignore
from .test_utils import TestScene, TestData, TestAssertions, TestRunner

# Import required modules
from ..core import faceit_utils as futils
from ..core import shape_key_utils as sk_utils
from ..core import vgroup_utils as vg_utils


# ============================================================
# Test Functions
# ============================================================

def test_core_data_initialization():
    """
    Test core data initialization.
    """
    # Check if core data exists
    if not cmds.objExists("faceit_core_data"):
        # Create core data
        cmds.createNode("transform", name="faceit_core_data")
        
        # Add attributes
        cmds.addAttr("faceit_core_data", ln="version", dt="string")
        cmds.addAttr("faceit_core_data", ln="expression_names", dt="string")
        cmds.addAttr("faceit_core_data", ln="expression_frames", dt="string")
        cmds.addAttr("faceit_core_data", ln="expression_sides", dt="string")
        cmds.addAttr("faceit_core_data", ln="expression_procedural", dt="string")
        cmds.addAttr("faceit_core_data", ln="current_index", attributeType="long", min=0, defaultValue=0)
    
    TestAssertions.assert_obj_exists("faceit_core_data")
    
    # Check attributes
    attrs = cmds.listAttr("faceit_core_data", userDefined=True) or []
    expected_attrs = ['version', 'expression_names', 'expression_frames', 'expression_sides', 'expression_procedural', 'current_index']
    for attr in expected_attrs:
        if attr not in attrs:
            raise AssertionError(f"Attribute '{attr}' not found on faceit_core_data")
    
    return True


def test_faceit_objects_registration():
    """
    Test Faceit objects registration.
    """
    # Create test scene
    test_scene = TestScene()
    test_scene.setup()
    
    try:
        # Create test mesh
        mesh = test_scene.create_test_mesh("test_mesh")
        
        # Create core data
        if not cmds.objExists("faceit_core_data"):
            cmds.createNode("transform", name="faceit_core_data")
            cmds.addAttr("faceit_core_data", ln="faceit_objects", dt="string")
        
        # Register object
        current = cmds.getAttr("faceit_core_data.faceit_objects") or ""
        objects = current.split(',') if current else []
        if mesh not in objects:
            objects.append(mesh)
        cmds.setAttr("faceit_core_data.faceit_objects", ",".join(objects), type="string")
        
        # Verify registration
        current = cmds.getAttr("faceit_core_data.faceit_objects") or ""
        objects = current.split(',') if current else []
        TestAssertions.assert_equal(mesh in objects, True)
        
    finally:
        test_scene.teardown()
    
    return True


def test_shape_key_creation():
    """
    Test shape key creation.
    """
    test_scene = TestScene()
    test_scene.setup()
    
    try:
        # Create test mesh
        mesh = test_scene.create_test_mesh("test_mesh")
        
        # Create blend shapes
        targets = test_scene.create_test_blend_shapes(mesh, 3)
        
        # Verify blend shapes
        TestAssertions.assert_has_shape_keys(mesh)
        
        blend_node = sk_utils.get_blend_shape_node(mesh)
        TestAssertions.assert_obj_exists(blend_node)
        
        # Check targets
        existing_targets = sk_utils.get_blend_shape_targets(mesh)
        for target in targets:
            TestAssertions.assert_equal(target in existing_targets, True)
        
    finally:
        test_scene.teardown()
    
    return True


def test_vertex_group_operations():
    """
    Test vertex group operations.
    """
    test_scene = TestScene()
    test_scene.setup()
    
    try:
        # Create test mesh
        mesh = test_scene.create_test_mesh("test_mesh")
        
        # Create vertex groups
        groups = TestData.create_test_vertex_groups(mesh)
        
        # Verify vertex groups
        for group_name in groups.keys():
            TestAssertions.assert_vertex_group_exists(mesh, group_name)
        
    finally:
        test_scene.teardown()
    
    return True


def test_expression_data_storage():
    """
    Test expression data storage.
    """
    test_scene = TestScene()
    test_scene.setup()
    
    try:
        # Create core data
        if not cmds.objExists("faceit_core_data"):
            cmds.createNode("transform", name="faceit_core_data")
            cmds.addAttr("faceit_core_data", ln="expression_names", dt="string")
            cmds.addAttr("faceit_core_data", ln="expression_frames", dt="string")
            cmds.addAttr("faceit_core_data", ln="expression_sides", dt="string")
            cmds.addAttr("faceit_core_data", ln="expression_procedural", dt="string")
            cmds.addAttr("faceit_core_data", ln="current_index", attributeType="long", min=0, defaultValue=0)
        
        # Create test expression data
        expr_data = TestScene().create_test_expression_data(3)
        expressions = expr_data['expressions']
        
        # Store expressions
        names = [e['name'] for e in expressions]
        frames = [e['frame'] for e in expressions]
        sides = [e['side'] for e in expressions]
        procedural = [e.get('procedural', 'NONE') for e in expressions]
        
        cmds.setAttr("faceit_core_data.expression_names", ",".join(names), type="string")
        cmds.setAttr("faceit_core_data.expression_frames", ",".join(str(f) for f in frames), type="string")
        cmds.setAttr("faceit_core_data.expression_sides", ",".join(sides), type="string")
        cmds.setAttr("faceit_core_data.expression_procedural", ",".join(procedural), type="string")
        cmds.setAttr("faceit_core_data.current_index", 0)
        
        # Verify storage
        stored_names = cmds.getAttr("faceit_core_data.expression_names") or ""
        stored_names = stored_names.split(',') if stored_names else []
        
        for name in names:
            TestAssertions.assert_equal(name in stored_names, True)
        
    finally:
        test_scene.teardown()
    
    return True


# ============================================================
# Test Suite
# ============================================================

def run_core_tests():
    """
    Run all core tests.
    
    Returns:
        Test results
    """
    test_runner = TestRunner()
    
    test_suite = [
        test_core_data_initialization,
        test_faceit_objects_registration,
        test_shape_key_creation,
        test_vertex_group_operations,
        test_expression_data_storage,
    ]
    
    results = test_runner.run_suite(test_suite)
    test_runner.print_results()
    
    return results


if __name__ == "__main__":
    run_core_tests()