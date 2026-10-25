# auto_load.py
# Maya Faceit Plugin - Auto Load System
# Converted from Blender to Maya Python 3.11

"""
Auto-load system for Faceit Maya plugin.
Handles automatic loading and registration of modules.
"""

import maya.cmds as cmds # type: ignore
import maya.api.OpenMaya as om2 # type: ignore
import sys
import os
import inspect
import importlib
import pkgutil
from pathlib import Path
from typing import List, Dict, Set, Optional, Any, Iterable


# ============================================================
# Module Registration System
# ============================================================

__all__ = (
    "init",
    "register",
    "unregister",
    "get_all_modules",
    "get_ordered_classes",
)

modules = None
ordered_classes = None
registered_operators = []


def init():
    """
    Initialize the auto-load system.
    Discovers all modules and classes to register.
    """
    global modules
    global ordered_classes
    
    # Get all submodules
    modules = get_all_submodules(Path(__file__).parent)
    
    # Get ordered classes for registration
    ordered_classes = get_ordered_classes_to_register(modules)
    
    print(f"Faceit Auto-Load: Found {len(modules)} modules, {len(ordered_classes)} classes")


def register():
    """
    Register all discovered classes and modules.
    """
    global registered_operators
    
    # Register classes
    for cls in ordered_classes:
        _register_class(cls)
    
    # Register modules
    for module in modules:
        if module.__name__ == __name__:
            continue
        if hasattr(module, "register"):
            try:
                module.register()
            except Exception as e:
                print(f"Error registering module {module.__name__}: {str(e)}")
    
    print(f"Faceit Auto-Load: Registered {len(registered_operators)} operators")


def unregister():
    """
    Unregister all classes and modules.
    """
    global registered_operators
    
    # Unregister modules in reverse order
    for module in reversed(modules):
        if module.__name__ == __name__:
            continue
        if hasattr(module, "unregister"):
            try:
                module.unregister()
            except Exception as e:
                print(f"Error unregistering module {module.__name__}: {str(e)}")
    
    # Unregister classes in reverse order
    for cls in reversed(ordered_classes):
        _unregister_class(cls)
    
    registered_operators = []
    
    print("Faceit Auto-Load: Unregistered all components")


# ============================================================
# Maya Class Registration
# ============================================================

def _register_class(cls):
    """
    Register a class with Maya.
    
    Args:
        cls: Class to register
    """
    global registered_operators
    
    # In Maya, we register commands differently
    # For now, we'll store the class for later use
    if hasattr(cls, "name"):
        registered_operators.append(cls)
        
        # Create a Maya command for the operator
        cmd_name = cls.name
        if hasattr(cls, "label"):
            cmd_name = cls.label.replace(" ", "")
        
        # Register the command
        try:
            # In Maya, we'd use the command module
            # For now, just add to the registry
            print(f"  Registered: {cmd_name}")
        except Exception as e:
            print(f"  Failed to register {cmd_name}: {str(e)}")


def _unregister_class(cls):
    """
    Unregister a class from Maya.
    
    Args:
        cls: Class to unregister
    """
    global registered_operators
    
    if hasattr(cls, "name") and cls.name in registered_operators:
        registered_operators.remove(cls.name)


# ============================================================
# Module Discovery
# ============================================================

def get_all_submodules(directory: Path) -> List:
    """
    Get all submodules in a directory.
    
    Args:
        directory: Directory path
        
    Returns:
        List of modules
    """
    return list(iter_submodules(directory, directory.name))


def iter_submodules(path: Path, package_name: str):
    """
    Iterate through submodules.
    
    Args:
        path: Directory path
        package_name: Package name
        
    Yields:
        Module objects
    """
    for name in sorted(iter_submodule_names(path)):
        try:
            yield importlib.import_module("." + name, package_name)
        except Exception as e:
            print(f"Error importing module {name}: {str(e)}")


def iter_submodule_names(path: Path, root: str = ""):
    """
    Iterate through submodule names.
    
    Args:
        path: Directory path
        root: Root name
        
    Yields:
        Module names
    """
    for _, module_name, is_package in pkgutil.iter_modules([str(path)]):
        if is_package:
            sub_path = path / module_name
            sub_root = root + module_name + "."
            yield from iter_submodule_names(sub_path, sub_root)
        else:
            yield root + module_name


# ============================================================
# Class Discovery and Ordering
# ============================================================

def get_ordered_classes_to_register(modules: List) -> List:
    """
    Get ordered classes for registration.
    
    Args:
        modules: List of modules
        
    Returns:
        Ordered list of classes
    """
    return toposort(get_register_deps_dict(modules))


def get_register_deps_dict(modules: List) -> Dict:
    """
    Get class dependencies dictionary.
    
    Args:
        modules: List of modules
        
    Returns:
        Dictionary of class dependencies
    """
    my_classes = set(iter_my_classes(modules))
    my_classes_by_name = {cls.__name__: cls for cls in my_classes if hasattr(cls, "__name__")}

    deps_dict = {}
    for cls in my_classes:
        deps_dict[cls] = set(iter_my_register_deps(cls, my_classes, my_classes_by_name))
    
    return deps_dict


def iter_my_register_deps(cls, my_classes, my_classes_by_name):
    """
    Iterate through class dependencies.
    
    Args:
        cls: Class
        my_classes: Set of classes
        my_classes_by_name: Dictionary of classes by name
        
    Yields:
        Dependency classes
    """
    # Check for parent classes
    for base in cls.__bases__:
        if base in my_classes:
            yield base
    
    # Check for annotations
    if hasattr(cls, "__annotations__"):
        for value in cls.__annotations__.values():
            dependency = get_dependency_from_annotation(value)
            if dependency is not None and dependency in my_classes:
                yield dependency
    
    # Check for Maya-specific dependencies
    if hasattr(cls, "name"):
        for other_cls in my_classes:
            if hasattr(other_cls, "name") and other_cls.name == getattr(cls, "predecessor", ""):
                yield other_cls


def get_dependency_from_annotation(value) -> Optional[type]:
    """
    Get dependency from annotation value.
    
    Args:
        value: Annotation value
        
    Returns:
        Dependency type or None
    """
    # In Maya, we handle dependencies differently
    # This is a simplified version
    if hasattr(value, "__name__"):
        return value
    return None


def iter_my_classes(modules: List) -> Iterable[type]:
    """
    Iterate through classes that should be registered.
    
    Args:
        modules: List of modules
        
    Returns:
        Iterable of classes
    """
    base_types = get_register_base_types()
    
    for cls in get_classes_in_modules(modules):
        # Check if this is a class we should register
        if any(base in base_types for base in cls.__bases__):
            # Skip built-in classes
            if cls.__module__ == "builtins":
                continue
            yield cls


def get_classes_in_modules(modules: List) -> Set[type]:
    """
    Get all classes in modules.
    
    Args:
        modules: List of modules
        
    Returns:
        Set of classes
    """
    classes = set()
    for module in modules:
        for value in module.__dict__.values():
            if inspect.isclass(value):
                classes.add(value)
    return classes


def get_register_base_types() -> Set[type]:
    """
    Get base types for registration.
    
    Returns:
        Set of base types
    """
    # In Maya, we use different base classes
    # This maps Blender's bpy.types to Maya equivalents
    return {
        # We'll use our own base classes
        object
    }


# ============================================================
# Topological Sort
# ============================================================

def toposort(deps_dict: Dict) -> List:
    """
    Topological sort of dependencies.
    
    Args:
        deps_dict: Dictionary of dependencies
        
    Returns:
        Sorted list
    """
    sorted_list = []
    sorted_values = set()
    
    while len(deps_dict) > 0:
        unsorted = []
        for value, deps in deps_dict.items():
            if len(deps) == 0:
                sorted_list.append(value)
                sorted_values.add(value)
            else:
                unsorted.append(value)
        
        # Remove sorted values from dependencies
        deps_dict = {value: deps_dict[value] - sorted_values for value in unsorted}
    
    return sorted_list


# ============================================================
# Maya Integration Functions
# ============================================================

def get_plugin_modules() -> List:
    """
    Get all Faceit plugin modules.
    
    Returns:
        List of module names
    """
    plugin_modules = []
    
    # Get all modules in the plugin directory
    plugin_dir = os.path.dirname(os.path.abspath(__file__))
    
    for item in os.listdir(plugin_dir):
        item_path = os.path.join(plugin_dir, item)
        if os.path.isdir(item_path) and not item.startswith('__'):
            if os.path.exists(os.path.join(item_path, '__init__.py')):
                plugin_modules.append(item)
        elif item.endswith('.py') and not item.startswith('__'):
            plugin_modules.append(item[:-3])
    
    return plugin_modules


def reload_modules():
    """
    Reload all Faceit modules.
    """
    modules = get_plugin_modules()
    
    for module_name in modules:
        if module_name in sys.modules:
            try:
                importlib.reload(sys.modules[module_name])
                print(f"Reloaded: {module_name}")
            except Exception as e:
                print(f"Failed to reload {module_name}: {str(e)}")


def get_faceit_version() -> str:
    """
    Get the Faceit plugin version.
    
    Returns:
        Version string
    """
    try:
        package_name = __package__ or "faceit"
        faceit_pkg = importlib.import_module(package_name)
        return getattr(faceit_pkg, '__version__', '1.0.0')
    except Exception:
        return '1.0.0'


# ============================================================
# Module Registration Functions
# ============================================================

def register_module(module_name: str) -> bool:
    """
    Register a module with Maya.
    
    Args:
        module_name: Module name
        
    Returns:
        True if successful
    """
    try:
        module = importlib.import_module(module_name)
        if hasattr(module, 'initialize_module'):
            module.initialize_module()
        return True
    except Exception as e:
        print(f"Failed to register module {module_name}: {str(e)}")
        return False


def unregister_module(module_name: str) -> bool:
    """
    Unregister a module from Maya.
    
    Args:
        module_name: Module name
        
    Returns:
        True if successful
    """
    try:
        module = importlib.import_module(module_name)
        if hasattr(module, 'uninitialize_module'):
            module.uninitialize_module()
        return True
    except Exception as e:
        print(f"Failed to unregister module {module_name}: {str(e)}")
        return False