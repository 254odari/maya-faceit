# test_utils.py
# Maya Faceit Plugin - Test Utilities
# Converted from Blender to Maya Python 3.11

"""
Test utilities for Faceit Maya plugin.
Provides helper functions for testing.
"""

import maya.cmds as cmds # type: ignore
import maya.api.OpenMaya as om2 # type: ignore
import json
import os
import tempfile
import shutil
from typing import List, Dict, Optional, Any

# Import required modules
from ..core import faceit_utils as futils
from ..core import shape_key_utils as sk_utils
from ..core import vgroup_utils as vg_utils


# ============================================================
# Test Scene Setup
# ============================================================

class TestScene:
    """
    Test scene management class.
    Creates and manages temporary test scenes.
    """
    
    def __init__(self):
        self.original_scene = None
        self.test_scene = None
        self.test_dir = None
        self.objects = []
    
    def setup(self) -> bool:
        """
        Set up a test scene.
        
        Returns:
            True if successful
        """
        # Save current scene
        self.original_scene = cmds.file(query=True, sceneName=True) or ""
        
        # Create temporary directory
        self.test_dir = tempfile.mkdtemp(prefix="faceit_test_")
        
        # Create new scene
        cmds.file(new=True, force=True)
        
        return True
    
    def teardown(self) -> None:
        """
        Clean up the test scene.
        """
        # Close current scene
        cmds.file(new=True, force=True)
        
        # Restore original scene
        if self.original_scene and os.path.exists(self.original_scene):
            cmds.file(self.original_scene, open=True, force=True)
        
        # Clean up temp directory
        if self.test_dir and os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def create_test_mesh(self, name: str = "test_mesh") -> str:
        """
        Create a test mesh.
        
        Args:
            name: Mesh name
            
        Returns:
            Created mesh name
        """
        # Create a simple cube
        mesh = cmds.polyCube(name=name, width=2, height=2, depth=2)[0]
        self.objects.append(mesh)
        return mesh
    
    def create_test_joint(self, name: str = "test_joint", position: List[float] = None) -> str:
        """
        Create a test joint.
        
        Args:
            name: Joint name
            position: Joint position
            
        Returns:
            Created joint name
        """
        if position is None:
            position = [0, 0, 0]
        
        joint = cmds.joint(name=name, position=position)
        self.objects.append(joint)
        return joint
    
    def create_test_armature(self, name: str = "test_armature") -> str:
        """
        Create a test armature with joints.
        
        Args:
            name: Armature name
            
        Returns:
            Created armature name
        """
        # Create root joint
        root = cmds.joint(name=f"{name}_root", position=[0, 0, 0])
        
        # Create child joints
        child1 = cmds.joint(name=f"{name}_child1", position=[0, 2, 0])
        cmds.parent(child1, root)
        
        child2 = cmds.joint(name=f"{name}_child2", position=[0, 4, 0])
        cmds.parent(child2, child1)
        
        armature = cmds.listRelatives(child2, parent=True)[0] if cmds.listRelatives(child2, parent=True) else root
        
        self.objects.append(armature)
        return armature
    
    def create_test_blend_shapes(self, mesh: str, count: int = 3) -> List[str]:
        """
        Create test blend shapes on a mesh.
        
        Args:
            mesh: Mesh name
            count: Number of blend shapes
            
        Returns:
            List of blend shape target names
        """
        if not cmds.objExists(mesh):
            return []
        
        # Create blend shape node
        blend_node = cmds.blendShape(mesh, name=f"{mesh}_blendShape")[0]
        
        targets = []
        for i in range(count):
            target_name = f"test_shape_{i}"
            
            # Create temp mesh for target
            temp_mesh = cmds.duplicate(mesh, name=f"{mesh}_{target_name}_temp")[0]
            
            # Modify vertices slightly
            vertices = cmds.ls(f"{temp_mesh}.vtx[*]", flatten=True)
            for j, vtx in enumerate(vertices[:10]):
                pos = cmds.xform(vtx, query=True, objectSpace=True, translation=True)
                if pos:
                    cmds.xform(vtx, objectSpace=True, translation=[pos[0] + 0.1 * i, pos[1], pos[2]])
            
            # Add as blend shape target
            cmds.blendShape(blend_node, edit=True, target=(mesh, 0, temp_mesh, 1.0))
            
            # Rename target
            weight_attrs = cmds.listAttr(f"{blend_node}.weight", multi=True) or []
            weight_attrs = [a for a in weight_attrs if a.startswith('weight[')]
            if weight_attrs:
                cmds.aliasAttr(target_name, f"{blend_node}.{weight_attrs[-1]}")
            
            targets.append(target_name)
            
            # Clean up
            cmds.delete(temp_mesh)
        
        return targets
    
    def create_test_expression_data(self, count: int = 5) -> Dict:
        """
        Create test expression data.
        
        Args:
            count: Number of expressions
            
        Returns:
            Expression data dictionary
        """
        expressions = []
        
        for i in range(count):
            expr = {
                'name': f"test_expression_{i}",
                'frame': (i + 1) * 10,
                'side': 'N' if i % 2 == 0 else 'L',
                'mirror_name': f"test_expression_{i}_mirror" if i % 2 == 0 else "",
                'procedural': 'NONE'
            }
            expressions.append(expr)
        
        return {'expressions': expressions}


# ============================================================
# Test Data Management
# ============================================================

class TestData:
    """
    Test data management class.
    Handles test data creation and validation.
    """
    
    @staticmethod
    def create_test_landmarks() -> str:
        """
        Create test landmarks.
        
        Returns:
            Landmarks mesh name
        """
        # Create a simple landmarks mesh
        landmarks = cmds.polyCreateFacet(
            name="facial_landmarks",
            point=[
                [-1, 0, 0], [1, 0, 0],
                [-1, 0, 1], [1, 0, 1],
                [0, 0, 2], [0, 1, 0],
                [-0.5, 0.5, 0.5], [0.5, 0.5, 0.5]
            ]
        )[0]
        
        return landmarks
    
    @staticmethod
    def create_test_vertex_groups(mesh: str) -> Dict[str, List[int]]:
        """
        Create test vertex groups on a mesh.
        
        Args:
            mesh: Mesh name
            
        Returns:
            Dictionary of vertex group names to vertex indices
        """
        if not cmds.objExists(mesh):
            return {}
        
        groups = {}
        
        # Get vertex count
        vertex_count = cmds.polyEvaluate(mesh, vertex=True)
        
        # Create main group
        main_vertices = list(range(vertex_count // 2))
        cmds.vertexGroup(mesh, add="faceit_main")
        for vtx in main_vertices:
            cmds.sets(f"{mesh}.vtx[{vtx}]", force=True, add="faceit_main")
        groups['faceit_main'] = main_vertices
        
        # Create eye groups
        eye_vertices = list(range(vertex_count // 4, vertex_count // 2))
        cmds.vertexGroup(mesh, add="faceit_left_eyeball")
        for vtx in eye_vertices:
            cmds.sets(f"{mesh}.vtx[{vtx}]", force=True, add="faceit_left_eyeball")
        groups['faceit_left_eyeball'] = eye_vertices
        
        return groups
    
    @staticmethod
    def validate_faceit_data() -> Dict[str, bool]:
        """
        Validate Faceit data in the scene.
        
        Returns:
            Dictionary of validation results
        """
        results = {
            'core_data_exists': cmds.objExists("faceit_core_data"),
            'has_armature': bool(futils.get_faceit_armature()),
            'has_control_rig': bool(futils.get_faceit_control_armature()),
            'has_landmarks': cmds.objExists("facial_landmarks"),
            'has_faceit_objects': bool(futils.get_faceit_objects_list()),
        }
        
        # Check expression data
        if cmds.objExists("faceit_core_data"):
            if cmds.attributeQuery("expression_names", node="faceit_core_data", exists=True):
                names_str = cmds.getAttr("faceit_core_data.expression_names") or ""
                results['has_expressions'] = bool(names_str)
        
        return results


# ============================================================
# Test Assertions
# ============================================================

class TestAssertions:
    """
    Test assertion utilities.
    """
    
    @staticmethod
    def assert_obj_exists(obj_name: str, message: str = None) -> bool:
        """
        Assert that an object exists.
        
        Args:
            obj_name: Object name
            message: Error message
            
        Returns:
            True if assertion passes
            
        Raises:
            AssertionError: If object doesn't exist
        """
        if not cmds.objExists(obj_name):
            raise AssertionError(message or f"Object '{obj_name}' does not exist")
        return True
    
    @staticmethod
    def assert_obj_type(obj_name: str, expected_type: str, message: str = None) -> bool:
        """
        Assert that an object has the expected type.
        
        Args:
            obj_name: Object name
            expected_type: Expected type
            message: Error message
            
        Returns:
            True if assertion passes
            
        Raises:
            AssertionError: If object type doesn't match
        """
        if not cmds.objExists(obj_name):
            raise AssertionError(f"Object '{obj_name}' does not exist")
        
        actual_type = cmds.nodeType(obj_name)
        if actual_type != expected_type:
            raise AssertionError(message or f"Object '{obj_name}' is '{actual_type}', expected '{expected_type}'")
        return True
    
    @staticmethod
    def assert_has_shape_keys(obj_name: str, message: str = None) -> bool:
        """
        Assert that an object has shape keys.
        
        Args:
            obj_name: Object name
            message: Error message
            
        Returns:
            True if assertion passes
            
        Raises:
            AssertionError: If object doesn't have shape keys
        """
        if not cmds.objExists(obj_name):
            raise AssertionError(f"Object '{obj_name}' does not exist")
        
        if not sk_utils.has_shape_keys(obj_name):
            raise AssertionError(message or f"Object '{obj_name}' has no shape keys")
        return True
    
    @staticmethod
    def assert_vertex_group_exists(obj_name: str, group_name: str, message: str = None) -> bool:
        """
        Assert that an object has a vertex group.
        
        Args:
            obj_name: Object name
            group_name: Group name
            message: Error message
            
        Returns:
            True if assertion passes
            
        Raises:
            AssertionError: If vertex group doesn't exist
        """
        if not cmds.objExists(obj_name):
            raise AssertionError(f"Object '{obj_name}' does not exist")
        
        if group_name not in vg_utils.get_vertex_groups(obj_name):
            raise AssertionError(message or f"Vertex group '{group_name}' not found on '{obj_name}'")
        return True
    
    @staticmethod
    def assert_equal(actual: Any, expected: Any, message: str = None) -> bool:
        """
        Assert that two values are equal.
        
        Args:
            actual: Actual value
            expected: Expected value
            message: Error message
            
        Returns:
            True if assertion passes
            
        Raises:
            AssertionError: If values are not equal
        """
        if actual != expected:
            raise AssertionError(message or f"Expected {expected}, got {actual}")
        return True


# ============================================================
# Test Runner
# ============================================================

class TestRunner:
    """
    Test runner for Faceit tests.
    """
    
    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.results = []
    
    def run_test(self, test_func, *args, **kwargs) -> bool:
        """
        Run a single test.
        
        Args:
            test_func: Test function
            *args: Arguments
            **kwargs: Keyword arguments
            
        Returns:
            True if test passes
        """
        try:
            result = test_func(*args, **kwargs)
            self.tests_passed += 1
            self.results.append({
                'name': test_func.__name__,
                'passed': True,
                'result': result
            })
            return True
        except Exception as e:
            self.tests_failed += 1
            self.results.append({
                'name': test_func.__name__,
                'passed': False,
                'error': str(e)
            })
            cmds.warning(f"Test '{test_func.__name__}' failed: {str(e)}")
            return False
    
    def run_suite(self, test_suite: List) -> Dict:
        """
        Run a test suite.
        
        Args:
            test_suite: List of test functions
            
        Returns:
            Test results dictionary
        """
        self.tests_passed = 0
        self.tests_failed = 0
        self.results = []
        
        for test_func in test_suite:
            self.run_test(test_func)
        
        return {
            'total': len(test_suite),
            'passed': self.tests_passed,
            'failed': self.tests_failed,
            'results': self.results
        }
    
    def print_results(self) -> None:
        """
        Print test results.
        """
        print("=" * 50)
        print("Test Results")
        print("=" * 50)
        print(f"Total: {len(self.results)}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_failed}")
        print("-" * 50)
        
        for result in self.results:
            status = "✓" if result['passed'] else "✗"
            print(f"{status} {result['name']}")
            if not result['passed']:
                print(f"  Error: {result.get('error', 'Unknown error')}")
        
        print("=" * 50)