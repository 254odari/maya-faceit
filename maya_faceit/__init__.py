# __init__.py
# Maya Faceit Plugin - Main Module
# Version: 1.0.0

"""
Faceit for Maya - Facial Rigging and Animation Toolkit
Copyright (c) 2024

This is the main module for the Faceit Maya plugin.
All modules are imported and initialized from here.
"""

__version__ = "1.0.0"
__author__ = "Faceit Team"

import maya.cmds as cmds
import maya.api.OpenMaya as om2
import sys
import os
import importlib
import inspect

# ============================================================
# Plugin Information
# ============================================================

PLUGIN_NAME = "faceit_maya"
PLUGIN_VERSION = "1.0.0"
PLUGIN_VENDOR = "Faceit Team"
PLUGIN_DESCRIPTION = "Facial Rigging and Animation Toolkit for Maya"

# List of required modules in registration order
REQUIRED_MODULES = [
    'core',
    'properties',
    'setup',
    'landmarks',
    'rigging',
    'bind',
    'retargeting',
    'retarget_fbx',
    'ctrl_rig',
    'mocap',
    'shape_keys',
    'bake',
    'finalize',
    'panels',
]

# Optional modules (loaded if available)
OPTIONAL_MODULES = [
    'test',
]


# ============================================================
# Module Path Detection
# ============================================================

def get_plugin_path():
    """
    Get the plugin directory path.
    In Maya plugins, __file__ is not always available.
    """
    # Method 1: Try to get from current module
    try:
        module_path = inspect.getfile(inspect.currentframe())
        return os.path.dirname(os.path.abspath(module_path))
    except:
        pass
    
    # Method 2: Try to get from Maya's plugin path
    try:
        plugin_info = cmds.pluginInfo(PLUGIN_NAME, query=True, path=True)
        if plugin_info:
            return os.path.dirname(plugin_info)
    except:
        pass
    
    # Method 3: Try to get from sys.modules
    try:
        if __name__ in sys.modules:
            module = sys.modules[__name__]
            if hasattr(module, '__file__') and module.__file__:
                return os.path.dirname(module.__file__)
    except:
        pass
    
    # Method 4: Use Maya's scripts directory
    try:
        scripts_dir = cmds.internalVar(userScriptDir=True)
        if scripts_dir:
            return scripts_dir
    except:
        pass
    
    # Method 5: Use current working directory
    return os.getcwd()


def add_plugin_to_path():
    """
    Add the plugin directory to Python path if not already there.
    """
    plugin_path = get_plugin_path()
    if plugin_path and plugin_path not in sys.path:
        sys.path.insert(0, plugin_path)
    return plugin_path


# ============================================================
# Maya Plugin Functions
# ============================================================

def maya_useNewMayapy():
    """
    Required for Maya to use new PySide2/Qt6.
    Maya 2026 uses PySide6/Qt6.
    """
    return True


def initializePlugin(obj):
    """
    Called when the plugin is loaded in Maya.
    
    Args:
        obj: Plugin object (MObject)
    """
    print(f"Faceit for Maya v{__version__} loading...")
    print("=" * 60)
    
    try:
        # Add plugin to Python path
        plugin_path = add_plugin_to_path()
        print(f"Plugin path: {plugin_path}")
        
        # Initialize all modules
        _initialize_modules()
        
        # Register plugin components
        _register_plugin_components(obj)
        
        # Create UI elements
        _create_ui_elements()
        
        # Register callbacks
        _register_callbacks()
        
        print("=" * 60)
        print(f"Faceit for Maya v{__version__} loaded successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"ERROR loading Faceit plugin: {str(e)}")
        import traceback
        traceback.print_exc()


def uninitializePlugin(obj):
    """
    Called when the plugin is unloaded from Maya.
    
    Args:
        obj: Plugin object (MObject)
    """
    print("Faceit for Maya unloading...")
    print("=" * 60)
    
    try:
        # Unregister callbacks
        _unregister_callbacks()
        
        # Clean up UI elements
        _cleanup_ui_elements(obj)
        
        # Uninitialize all modules
        _uninitialize_modules()
        
        print("=" * 60)
        print("Faceit for Maya unloaded successfully")
        print("=" * 60)
        
    except Exception as e:
        print(f"ERROR unloading Faceit plugin: {str(e)}")
        import traceback
        traceback.print_exc()


# ============================================================
# Module Initialization Functions
# ============================================================

def _initialize_modules():
    """
    Initialize all Faceit modules.
    """
    print("Initializing Faceit modules...")
    
    # Add plugin to path
    plugin_path = add_plugin_to_path()
    
    # Initialize core module first (dependency for others)
    try:
        from . import core
        core.initialize_core()
        print("  Core module initialized")
    except ImportError as e:
        print(f"  Failed to import core: {str(e)}")
    except Exception as e:
        print(f"  Failed to initialize core: {str(e)}")
    
    # Initialize required modules
    for module_name in REQUIRED_MODULES:
        if module_name != 'core':
            try:
                module = importlib.import_module(f".{module_name}", package=__name__)
                if hasattr(module, 'initialize_module'):
                    module.initialize_module()
                print(f"  {module_name.capitalize()} module initialized")
            except ImportError as e:
                print(f"  Failed to import {module_name}: {str(e)}")
            except Exception as e:
                print(f"  Failed to initialize {module_name}: {str(e)}")
    
    # Initialize optional modules
    for module_name in OPTIONAL_MODULES:
        try:
            module = importlib.import_module(f".{module_name}", package=__name__)
            if hasattr(module, 'initialize_module'):
                module.initialize_module()
            print(f"  {module_name.capitalize()} module initialized (optional)")
        except ImportError:
            pass
        except Exception as e:
            print(f"  Failed to initialize optional module {module_name}: {str(e)}")
    
    # Initialize auto-load system
    try:
        from . import auto_load
        auto_load.init()
        auto_load.register()
        print("  Auto-load system initialized")
    except ImportError:
        print("  Auto-load system not available")
    except Exception as e:
        print(f"  Failed to initialize auto-load: {str(e)}")


def _uninitialize_modules():
    """
    Uninitialize all Faceit modules.
    """
    print("Uninitializing Faceit modules...")
    
    # Uninitialize auto-load first
    try:
        from . import auto_load
        auto_load.unregister()
        print("  Auto-load system uninitialized")
    except ImportError:
        pass
    except Exception as e:
        print(f"  Failed to uninitialize auto-load: {str(e)}")
    
    # Uninitialize optional modules
    for module_name in reversed(OPTIONAL_MODULES):
        try:
            module = importlib.import_module(f".{module_name}", package=__name__)
            if hasattr(module, 'uninitialize_module'):
                module.uninitialize_module()
            print(f"  {module_name.capitalize()} module uninitialized (optional)")
        except ImportError:
            pass
        except Exception as e:
            print(f"  Failed to uninitialize optional module {module_name}: {str(e)}")
    
    # Uninitialize required modules in reverse order
    for module_name in reversed(REQUIRED_MODULES):
        if module_name != 'core':
            try:
                module = importlib.import_module(f".{module_name}", package=__name__)
                if hasattr(module, 'uninitialize_module'):
                    module.uninitialize_module()
                print(f"  {module_name.capitalize()} module uninitialized")
            except ImportError as e:
                print(f"  Failed to unimport {module_name}: {str(e)}")
            except Exception as e:
                print(f"  Failed to uninitialize {module_name}: {str(e)}")
    
    # Uninitialize core last
    try:
        from . import core
        core.uninitialize_core()
        print("  Core module uninitialized")
    except ImportError:
        pass
    except Exception as e:
        print(f"  Failed to uninitialize core: {str(e)}")


# ============================================================
# Plugin Registration Functions
# ============================================================

def _register_plugin_components(obj):
    """
    Register plugin components with Maya.
    
    Args:
        obj: Plugin object (MObject)
    """
    print("Registering plugin components...")
    
    # Register commands
    _register_commands()
    
    # Register shelf buttons
    _create_shelf_buttons()
    
    # Register menus
    _create_menus()


def _register_commands():
    """
    Register Maya commands for Faceit operations.
    """
    pass


def _create_shelf_buttons():
    """
    Create Faceit buttons in the current shelf.
    """
    if cmds.about(batch=True):
        return
    try:
        import maya.mel as mel
        
        current_shelf = mel.eval('$tmp = $gShelfTopLevel')
        if not current_shelf:
            return
        
        shelf_tabs = cmds.tabLayout(current_shelf, query=True, childArray=True)
        if not shelf_tabs:
            return
        
        shelf = shelf_tabs[0]
        
        existing = cmds.shelfLayout(shelf, query=True, childArray=True) or []
        for item in existing:
            if cmds.shelfButton(item, query=True, label=True) == "Faceit":
                return
        
        plugin_path = get_plugin_path()
        
        cmd = f"""
import sys
import os
plugin_path = r'{plugin_path}'
if plugin_path not in sys.path:
    sys.path.insert(0, plugin_path)
try:
    from maya_faceit.panels import show_faceit_window
    show_faceit_window()
except Exception as e:
    print('Faceit panels not available:', str(e))
"""
        
        cmds.shelfButton(
            parent=shelf,
            annotation="Open Faceit for Maya",
            label="Faceit",
            command=cmd,
            image="commandButton.png",
            imageOverlayLabel="F",
            sourceType="python"
        )
        print("  Shelf button created")
        
    except Exception as e:
        print(f"  Failed to create shelf button: {str(e)}")


def _create_menus():
    """
    Create Faceit menus in Maya.
    """
    try:
        if cmds.menu("faceitMenu", exists=True, parent="MayaWindow"):
            return
        
        cmds.menu("faceitMenu", label="Faceit", parent="MayaWindow")
        
        cmds.menuItem(
            parent="faceitMenu",
            label="Open Faceit",
            command=f'''
import sys
import os
plugin_path = r'{get_plugin_path()}'
if plugin_path not in sys.path:
    sys.path.insert(0, plugin_path)
try:
    from maya_faceit.panels import show_faceit_window
    show_faceit_window()
except Exception as e:
    print('Error opening Faceit:', str(e))
'''
        )
        
        cmds.menuItem(parent="faceitMenu", divider=True)
        
        # Setup submenu
        cmds.menuItem(parent="faceitMenu", label="Setup", subMenu=True)
        cmds.menuItem(parent="faceitMenu|Setup", label="Register Objects", command='print("Registering objects...")')
        cmds.menuItem(parent="faceitMenu|Setup", label="Assign Vertex Groups", command='print("Assigning vertex groups...")')
        
        # Rigging submenu
        cmds.menuItem(parent="faceitMenu", label="Rigging", subMenu=True)
        cmds.menuItem(parent="faceitMenu|Rigging", label="Generate Landmarks", command='print("Generating landmarks...")')
        cmds.menuItem(parent="faceitMenu|Rigging", label="Generate Rig", command='print("Generating rig...")')
        cmds.menuItem(parent="faceitMenu|Rigging", label="Smart Bind", command='print("Smart binding...")')
        
        # Expressions submenu
        cmds.menuItem(parent="faceitMenu", label="Expressions", subMenu=True)
        cmds.menuItem(parent="faceitMenu|Expressions", label="Load ARKit", command='print("Loading ARKit expressions...")')
        cmds.menuItem(parent="faceitMenu|Expressions", label="Load A2F", command='print("Loading Audio2Face expressions...")')
        
        # Mocap submenu
        cmds.menuItem(parent="faceitMenu", label="Mocap", subMenu=True)
        cmds.menuItem(parent="faceitMenu|Mocap", label="Import FaceCap", command='print("Importing FaceCap...")')
        cmds.menuItem(parent="faceitMenu|Mocap", label="Import Epic", command='print("Importing Epic...")')
        cmds.menuItem(parent="faceitMenu|Mocap", label="Import A2F", command='print("Importing A2F...")')
        cmds.menuItem(parent="faceitMenu|Mocap", divider=True)
        cmds.menuItem(parent="faceitMenu|Mocap", label="Start OSC", command='print("Starting OSC receiver...")')
        cmds.menuItem(parent="faceitMenu|Mocap", label="Stop OSC", command='print("Stopping OSC receiver...")')
        
        # Help submenu
        cmds.menuItem(parent="faceitMenu", label="Help", subMenu=True)
        cmds.menuItem(parent="faceitMenu|Help", label="Documentation", command='import webbrowser; webbrowser.open("https://faceit-doc.readthedocs.io/")')
        cmds.menuItem(parent="faceitMenu|Help", label="About Faceit", command=f'print("Faceit for Maya v{__version__}")')
        
        print("  Menus created")
        
    except Exception as e:
        print(f"  Failed to create menus: {str(e)}")


# ============================================================
# UI Functions
# ============================================================

def _create_ui_elements():
    """
    Create Faceit UI elements.
    """
    print("Creating UI elements...")
    if cmds.about(batch=True):
        print("  Skipped UI panels (batch mode)")
        return
    try:
        from . import panels
        if hasattr(panels, 'register_panels'):
            panels.register_panels()
        print("  UI panels registered")
    except ImportError:
        print("  Panels module not available")
    except Exception as e:
        print(f"  Failed to create UI panels: {str(e)}")


def _cleanup_ui_elements(obj):
    """
    Clean up UI elements.
    
    Args:
        obj: Plugin object (MObject)
    """
    try:
        from . import panels
        if hasattr(panels, 'unregister_panels'):
            panels.unregister_panels()
    except:
        pass
    
    _remove_shelf_buttons()


def _remove_shelf_buttons():
    """
    Remove Faceit shelf buttons.
    """
    if cmds.about(batch=True):
        return
    try:
        import maya.mel as mel
        
        current_shelf = mel.eval('$tmp = $gShelfTopLevel')
        if not current_shelf:
            return
        
        shelf_tabs = cmds.tabLayout(current_shelf, query=True, childArray=True)
        if not shelf_tabs:
            return
        
        shelf = shelf_tabs[0]
        existing = cmds.shelfLayout(shelf, query=True, childArray=True) or []
        
        for item in existing:
            if cmds.shelfButton(item, query=True, label=True) == "Faceit":
                cmds.deleteUI(item)
                break
                
    except:
        pass


# ============================================================
# Callback Functions
# ============================================================

def _register_callbacks():
    """
    Register Maya callbacks.
    """
    print("Registering callbacks...")
    
    try:
        from .core import faceit_callback
        if hasattr(faceit_callback, 'register_faceit_callbacks'):
            faceit_callback.register_faceit_callbacks()
        print("  Callbacks registered")
    except ImportError:
        print("  Callback module not available")
    except Exception as e:
        print(f"  Failed to register callbacks: {str(e)}")


def _unregister_callbacks():
    """
    Unregister Maya callbacks.
    """
    print("Unregistering callbacks...")
    
    try:
        from .core import faceit_callback
        if hasattr(faceit_callback, 'unregister_faceit_callbacks'):
            faceit_callback.unregister_faceit_callbacks()
        print("  Callbacks unregistered")
    except:
        pass


# ============================================================
# Utility Functions
# ============================================================

def reload_plugin():
    """
    Reload the Faceit plugin.
    """
    print("Reloading Faceit plugin...")
    
    plugin_path = get_plugin_path()
    
    try:
        cmds.unloadPlugin(PLUGIN_NAME)
    except:
        pass
    
    modules_to_reload = [__name__] + [f"{__name__}.{m}" for m in REQUIRED_MODULES + ['core']]
    for module_name in modules_to_reload:
        if module_name in sys.modules:
            del sys.modules[module_name]
    
    try:
        cmds.loadPlugin(os.path.join(plugin_path, f"{PLUGIN_NAME}.py"))
        print("  Plugin reloaded")
    except Exception as e:
        print(f"  Failed to reload plugin: {str(e)}")


def get_plugin_version():
    """Get the plugin version."""
    return __version__


def get_faceit_data_node():
    """Get the Faceit core data node."""
    if cmds.objExists("faceit_core_data"):
        return "faceit_core_data"
    return None


def ensure_faceit_data_node():
    """Ensure the Faceit core data node exists."""
    if not cmds.objExists("faceit_core_data"):
        cmds.createNode("transform", name="faceit_core_data")
        _add_core_attributes()
    return "faceit_core_data"


def _add_core_attributes():
    """Add all core attributes to the data node."""
    attrs = [
        ("version", "string", __version__),
        ("expression_names", "string", ""),
        ("expression_frames", "string", ""),
        ("expression_sides", "string", ""),
        ("expression_procedural", "string", ""),
        ("current_index", "long", 0),
        ("armature", "string", ""),
        ("control_rig", "string", ""),
        ("faceit_objects", "string", ""),
        ("shapes_generated", "bool", False),
        ("pending_updates", "long", 0),
        ("head_target", "string", ""),
        ("head_action", "string", ""),
        ("corrective_data", "string", ""),
        ("current_object_index", "long", 0),
        ("body_armature", "string", ""),
        ("body_armature_head_bone", "string", ""),
        ("use_eye_pivots", "bool", False),
        ("anime_ref_eyebone_l", "string", ""),
        ("anime_ref_eyebone_r", "string", ""),
        ("use_rigify_armature", "bool", False),
        ("is_rigify_armature", "bool", False),
        ("asymmetric", "bool", False),
        ("show_locator_empties", "bool", False),
        ("mocap_action", "string", ""),
        ("osc_address", "string", "0.0.0.0"),
        ("osc_port", "long", 9001),
        ("osc_receiver_enabled", "bool", False),
        ("osc_animate_shapes", "bool", True),
        ("osc_animate_head_rotation", "bool", True),
        ("osc_animate_head_location", "bool", False),
        ("osc_rotation_units", "long", 0),
        ("osc_use_region_filter", "bool", False),
        ("osc_flip_animation", "bool", False),
        ("auto_disconnect_ctrl_rig", "bool", True),
        ("draw_handler_name", "string", ""),
        ("show_landmarks_ctrl_rig", "bool", False),
        ("control_armature", "string", ""),
        ("crig_targets", "string", ""),
        ("crig_targets_index", "long", 0),
        ("crig_objects", "string", ""),
        ("crig_objects_index", "long", 0),
        ("crig_face_regions", "string", ""),
        ("workspace_data", "string", ""),
        ("expression_init_expand_ui", "bool", True),
        ("pin_panels", "string", ""),
        ("fbx_retarget_mapping", "string", ""),
        ("shape_key_slider_min", "float", 0.0),
        ("shape_key_slider_max", "float", 1.0),
        ("weights_restorable", "bool", False),
        ("expressions_restorable", "bool", False),
        ("corrective_sk_restorable", "bool", False),
        ("subscribed", "bool", False),
        ("face_index", "long", 0),
        ("show_warnings", "bool", False),
        ("vertex_groups", "string", ""),
        ("arkit_retarget_shapes", "string", ""),
        ("arkit_retarget_shapes_index", "long", 0),
        ("a2f_retarget_shapes", "string", ""),
        ("a2f_retarget_shapes_index", "long", 0),
        ("face_regions", "string", ""),
        ("display_retarget_list", "long", 0),
        ("retargeting_naming_scheme", "long", 0),
        ("face_cap_mocap_settings", "string", ""),
        ("epic_mocap_settings", "string", ""),
        ("a2f_mocap_settings", "string", ""),
        ("head_target_object", "string", ""),
        ("head_sub_target", "string", ""),
        ("use_head_location_offset", "bool", True),
    ]
    
    for attr_name, attr_type, default_value in attrs:
        if not cmds.attributeQuery(attr_name, node="faceit_core_data", exists=True):
            cmds.addAttr("faceit_core_data", ln=attr_name, attributeType=attr_type)
            try:
                if attr_type == "string":
                    cmds.setAttr(f"faceit_core_data.{attr_name}", default_value, type="string")
                else:
                    cmds.setAttr(f"faceit_core_data.{attr_name}", default_value)
            except:
                pass


# ============================================================
# Module Exports
# ============================================================

__all__ = [
    '__version__',
    'PLUGIN_NAME',
    'PLUGIN_VERSION',
    'PLUGIN_VENDOR',
    'PLUGIN_DESCRIPTION',
    'initializePlugin',
    'uninitializePlugin',
    'maya_useNewMayapy',
    'get_plugin_version',
    'get_plugin_path',
    'reload_plugin',
    'get_faceit_data_node',
    'ensure_faceit_data_node',
    'REQUIRED_MODULES',
    'OPTIONAL_MODULES',
]