# Faceit for Maya 2026

**Facial Rigging and Animation Toolkit for Autodesk Maya 2026**

![Faceit for Maya](https://img.shields.io/badge/Maya-2026-blue)
![Version](https://img.shields.io/badge/version-1.0.0-green)
![Python](https://img.shields.io/badge/python-3.10+-yellow)
![License](https://img.shields.io/badge/license-MIT-orange)

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [System Requirements](#system-requirements)
- [Installation Guide](#installation-guide)
  - [Directory Structure for Maya 2026](#directory-structure-for-maya-2026)
  - [Method 1: Module Installation (Recommended)](#method-1-module-installation-recommended)
  - [Method 2: Manual Installation](#method-2-manual-installation)
  - [Method 3: Quick Install Script](#method-3-quick-install-script)
- [Loading the Plugin](#loading-the-plugin)
- [Post-Installation Setup](#post-installation-setup)
- [Troubleshooting](#troubleshooting)
- [Uninstallation](#uninstallation)
- [Development](#development)
- [Support](#support)
- [License](#license)

---

## 📖 Overview

Faceit for Maya is a comprehensive facial rigging and animation toolkit that brings the power of facial motion capture and expression creation to Autodesk Maya 2026. Originally developed for Blender, this is a complete conversion to Maya's Python API.

### Key Features

- **Facial Rig Generation**: Automatically create a facial rig from character geometry
- **Expression Management**: Create, edit, and manage facial expressions (ARKit, Audio2Face, etc.)
- **Shape Key Baking**: Bake expressions to blend shapes for production-ready assets
- **Motion Capture Integration**: Import from FaceCap, Epic Live Link Face, and Audio2Face
- **Live OSC Support**: Real-time facial animation via OSC protocol
- **Control Rig**: Generated control rig with custom slider system
- **Corrective Shape Keys**: Sculpt and apply corrective shapes for natural expressions
- **FBX Retargeting**: Retarget animation from FBX files to character shapes
- **Vertex Group Assignment**: Easy assignment of facial parts (eyes, teeth, tongue, etc.)

---

## 💻 System Requirements

| Requirement | Specification |
|-------------|---------------|
| **Maya Version** | Autodesk Maya 2026 |
| **Python Version** | Python 3.10+ (included with Maya 2026) |
| **Qt Version** | PySide6 (Qt6, included with Maya 2026) |
| **Operating System** | Windows 10/11, macOS 12+, Linux |
| **RAM** | 8GB minimum, 16GB+ recommended |
| **GPU** | OpenGL 4.0+ compatible |
| **Disk Space** | 500MB for plugin + resources |

---

## 📂 Installation Guide

### Directory Structure for Maya 2026
C:\Program Files\Common Files\Autodesk Shared\Modules\maya\2026\faceit\
├── module.json
├── scripts\
│   ├── faceit_maya.py
│   └── maya_faceit\
│       ├── __init__.py
│       ├── auto_load.py
│       ├── core\
│       ├── ctrl_rig\
│       ├── landmarks\
│       ├── finalize\
│       ├── bind\
│       ├── bake\
│       ├── mocap\
│       ├── panels\
│       ├── properties\
│       ├── retarget_fbx\
│       ├── retargeting\
│       ├── rigging\
│       ├── shape_keys\
│       ├── setup\
│       └── test\
└── resources\
    ├── expressions\
    ├── retarget_presets\
    ├── FaceitRig.ma
    ├── FaceitControlRig.ma
    └── FaceitLandmarks.ma

### Module Paths by Operating System

| OS | User Path | System Path |
|----|-----------|-------------|
| **Windows** | `C:\Users\[username]\Documents\maya\2026\modules\` | `C:\Program Files\Common Files\Autodesk Shared\Modules\maya\2026\` |
| **macOS** | `~/Library/Preferences/Autodesk/maya/2026/modules/` | `/Library/Application Support/Autodesk/Modules/maya/2026/` |
| **Linux** | `~/maya/2026/modules/` | `/opt/Autodesk/maya/2026/modules/` |

---

### Method 1: Module Installation (Recommended)

#### Step 1: Create the Module Directory

**Windows:**
```cmd
mkdir "C:\Program Files\Common Files\Autodesk Shared\Modules\maya\2026\faceit"
mkdir "C:\Program Files\Common Files\Autodesk Shared\Modules\maya\2026\faceit\scripts"
mkdir "C:\Program Files\Common Files\Autodesk Shared\Modules\maya\2026\faceit\resources"
Step 2: Create module.json
json
{
    "ModuleName": "Faceit for Maya",
    "ModuleVersion": "1.0.0",
    "Description": "Facial Rigging and Animation Toolkit for Maya 2026",
    "Authors": ["Faceit Team"],
    "Copyright": "Copyright (c) 2024",
    "License": "MIT",
    "URL": "https://faceit-doc.readthedocs.io/",
    "Platforms": ["Windows", "macOS", "Linux"],
    "MayaVersions": ["2026"],
    "Modules": [
        {
            "Type": "Python",
            "Path": "scripts/maya_faceit"
        }
    ],
    "Environment": {
        "PYTHONPATH": [
            "scripts"
        ],
        "MAYA_SCRIPT_PATH": [
            "scripts"
        ],
        "MAYA_PLUG_IN_PATH": [
            "plugins"
        ]
    },
    "Load": [
        "faceit_maya.py"
    ],
    "Required": {
        "Maya": "2026"
    }
}
Step 3: Copy Plugin Files
Copy the maya_faceit folder to scripts/:

bash
cp -r maya_faceit /path/to/maya/2026/modules/faceit/scripts/
Copy the resources folder:

bash
cp -r resources /path/to/maya/2026/modules/faceit/
Step 4: Create Entry Point
Create scripts/faceit_maya.py:

python
# faceit_maya.py
# Maya Faceit Plugin - Entry Point for Maya 2026

import maya.cmds as cmds
import sys
import os

def maya_useNewMayapy():
    return True

def initializePlugin(obj):
    plugin_path = os.path.dirname(os.path.abspath(__file__))
    if plugin_path not in sys.path:
        sys.path.insert(0, plugin_path)
    
    try:
        from maya_faceit import initializePlugin as init
        init(obj)
    except Exception as e:
        print(f"Faceit initialization error: {str(e)}")

def uninitializePlugin(obj):
    try:
        from maya_faceit import uninitializePlugin as uninit
        uninit(obj)
    except Exception as e:
        print(f"Faceit uninitialization error: {str(e)}")
Method 2: Manual Installation
Step 1: Locate Maya's Scripts Directory
Run this in Maya's Script Editor:

python
import maya.cmds as cmds
print(cmds.internalVar(userScriptDir=True))
Step 2: Create the Plugin Structure
bash
cd ~/Documents/maya/2026/scripts/
mkdir -p maya_faceit
cd maya_faceit
# Create all subdirectories...
Step 3: Copy All Plugin Files
Copy all the converted Python files into their respective directories as shown in the Directory Structure.

Step 4: Create the Plugin File
Create faceit_maya.py:

python
# faceit_maya.py
import sys
import os

plugin_dir = os.path.dirname(os.path.abspath(__file__))
if plugin_dir not in sys.path:
    sys.path.insert(0, plugin_dir)

from maya_faceit import initializePlugin, uninitializePlugin, maya_useNewMayapy
Method 3: Quick Install Script
Save this as install_faceit.py and run it:

python
# install_faceit.py
# Maya 2026 Quick Install Script

import os
import sys
import shutil
import json

def get_maya_2026_paths():
    """Get Maya 2026 paths based on OS."""
    import platform
    
    system = platform.system()
    
    if system == "Windows":
        user_scripts = os.path.expanduser("~/Documents/maya/2026/scripts")
        user_modules = os.path.expanduser("~/Documents/maya/2026/modules")
        system_modules = r"C:\Program Files\Common Files\Autodesk Shared\Modules\maya\2026"
    elif system == "Darwin":
        user_scripts = os.path.expanduser("~/Library/Preferences/Autodesk/maya/2026/scripts")
        user_modules = os.path.expanduser("~/Library/Preferences/Autodesk/maya/2026/modules")
        system_modules = "/Library/Application Support/Autodesk/Modules/maya/2026"
    else:  # Linux
        user_scripts = os.path.expanduser("~/maya/2026/scripts")
        user_modules = os.path.expanduser("~/maya/2026/modules")
        system_modules = "/opt/Autodesk/maya/2026/modules"
    
    return {
        'user_scripts': user_scripts,
        'user_modules': user_modules,
        'system_modules': system_modules,
        'system': system
    }

def install_faceit_maya2026(source_dir, use_system=False):
    """Install Faceit for Maya 2026."""
    paths = get_maya_2026_paths()
    
    # Choose installation location
    if use_system:
        install_dir = paths['system_modules']
        print(f"Installing to system location: {install_dir}")
    else:
        install_dir = paths['user_modules']
        print(f"Installing to user location: {install_dir}")
    
    # Create directories
    faceit_dir = os.path.join(install_dir, "faceit")
    scripts_dir = os.path.join(faceit_dir, "scripts")
    resources_dir = os.path.join(faceit_dir, "resources")
    
    os.makedirs(scripts_dir, exist_ok=True)
    os.makedirs(resources_dir, exist_ok=True)
    
    # Copy plugin files
    source_scripts = os.path.join(source_dir, "maya_faceit")
    if os.path.exists(source_scripts):
        target_scripts = os.path.join(scripts_dir, "maya_faceit")
        if os.path.exists(target_scripts):
            shutil.rmtree(target_scripts)
        shutil.copytree(source_scripts, target_scripts)
        print(f"✓ Copied plugin files to {target_scripts}")
    
    # Copy resources
    source_resources = os.path.join(source_dir, "resources")
    if os.path.exists(source_resources):
        target_resources = os.path.join(resources_dir, "resources")
        if os.path.exists(target_resources):
            shutil.rmtree(target_resources)
        shutil.copytree(source_resources, target_resources)
        print(f"✓ Copied resources to {target_resources}")
    
    # Create module.json
    module_json = {
        "ModuleName": "Faceit for Maya",
        "ModuleVersion": "1.0.0",
        "Description": "Facial Rigging and Animation Toolkit for Maya 2026",
        "Authors": ["Faceit Team"],
        "Copyright": "Copyright (c) 2024",
        "License": "MIT",
        "URL": "https://faceit-doc.readthedocs.io/",
        "Platforms": ["Windows", "macOS", "Linux"],
        "MayaVersions": ["2026"],
        "Modules": [
            {"Type": "Python", "Path": "scripts/maya_faceit"}
        ],
        "Environment": {
            "PYTHONPATH": ["scripts"],
            "MAYA_SCRIPT_PATH": ["scripts"]
        },
        "Load": ["faceit_maya.py"],
        "Required": {"Maya": "2026"}
    }
    
    module_path = os.path.join(faceit_dir, "module.json")
    with open(module_path, 'w') as f:
        json.dump(module_json, f, indent=4)
    print(f"✓ Created module.json at {module_path}")
    
    # Create plugin entry point
    plugin_entry = os.path.join(scripts_dir, "faceit_maya.py")
    with open(plugin_entry, 'w') as f:
        f.write("""
# faceit_maya.py
# Maya Faceit Plugin - Entry Point for Maya 2026

import maya.cmds as cmds
import sys
import os

def maya_useNewMayapy():
    return True

def initializePlugin(obj):
    plugin_path = os.path.dirname(os.path.abspath(__file__))
    if plugin_path not in sys.path:
        sys.path.insert(0, plugin_path)
    
    try:
        from maya_faceit import initializePlugin as init
        init(obj)
    except Exception as e:
        print(f"Faceit initialization error: {str(e)}")

def uninitializePlugin(obj):
    try:
        from maya_faceit import uninitializePlugin as uninit
        uninit(obj)
    except Exception as e:
        print(f"Faceit uninitialization error: {str(e)}")
""")
    print(f"✓ Created plugin entry at {plugin_entry}")
    
    print("\n" + "=" * 60)
    print("Faceit for Maya 2026 Installation Complete!")
    print("=" * 60)
    print(f"Installation directory: {faceit_dir}")
    print("\nTo load the plugin in Maya:")
    print("1. Restart Maya")
    print("2. Go to Windows > Settings/Preferences > Plug-in Manager")
    print("3. Find 'faceit_maya.py' and check 'Loaded'")
    print("\nOr use in Script Editor:")
    print("cmds.loadPlugin('faceit_maya.py')")
    print("=" * 60)

if __name__ == "__main__":
    source_dir = os.path.dirname(os.path.abspath(__file__))
    install_faceit_maya2026(source_dir, use_system=False)
🚀 Loading the Plugin
Method 1: Plug-in Manager (GUI)
Open Maya 2026

Go to Windows > Settings/Preferences > Plug-in Manager

Click Browse and navigate to faceit_maya.py

Check Loaded to load the plugin

Check Auto Load to load automatically on startup

Method 2: Script Editor (Python)
python
import maya.cmds as cmds
cmds.loadPlugin("faceit_maya.py")
Method 3: Command Line
bash
maya2026 -command "loadPlugin faceit_maya.py"
Method 4: Startup Script
Create userSetup.py in your Maya scripts directory:

python
# ~/Documents/maya/2026/scripts/userSetup.py
import maya.cmds as cmds
try:
    cmds.loadPlugin("faceit_maya.py")
except:
    pass
🔧 Post-Installation Setup
Verify Installation
Run this in Maya's Script Editor:

python
import maya.cmds as cmds
import importlib

# Check if plugin is loaded
if cmds.pluginInfo("faceit_maya.py", query=True, loaded=True):
    print("✓ Faceit plugin is loaded")
else:
    print("✗ Faceit plugin is not loaded")

# Check modules
try:
    import maya_faceit.core
    print("✓ Core module available")
except ImportError:
    print("✗ Core module not available")

# Check version
import maya_faceit
print(f"Faceit version: {maya_faceit.__version__}")
First Time Setup
Open the Faceit Panel

The Faceit panel should appear in the sidebar (UI > Faceit)

Or use the shelf button if created

Register Your Character

Select your character mesh(es)

Go to Setup tab

Click "Register Objects"

Assign Vertex Groups

Assign faceit_main (mandatory)

Assign other groups (eyes, teeth, tongue, etc.)

Generate Landmarks

Go to Rigging tab

Click "Generate Landmarks"

Follow the on-screen instructions

Generate Rig

Click "Generate Faceit Rig"

The rig will be created and matched to your character

Bind Weights

Click "Smart Bind"

Wait for the binding process to complete

Load Expressions

Go to Expressions tab

Click "Load Faceit Expressions"

Select ARKit or other expression set

Bake Shape Keys

Go to Bake tab

Click "Bake Shape Keys"

Your expressions are now baked to blend shapes!

❓ Troubleshooting
Common Issues and Solutions
"Module not found" Error
Solution: Add the plugin path to sys.path

python
import sys
import os
plugin_path = os.path.dirname(os.path.abspath(__file__))
if plugin_path not in sys.path:
    sys.path.insert(0, plugin_path)
"No module named 'maya_faceit'"
Solution: Check directory structure and ensure all files are in the correct location

python
import os
print(os.listdir(os.path.dirname(os.path.abspath(__file__))))
UI panels not showing
Solution 1: Reload the plugin

python
cmds.unloadPlugin("faceit_maya.py")
cmds.loadPlugin("faceit_maya.py")
Solution 2: Refresh the UI

python
import maya.mel as mel
mel.eval('source updateUI;')
"faceit_maya.py" not found in Plug-in Manager
Solution:

Click Browse in Plug-in Manager

Navigate to the scripts directory

Select faceit_maya.py

Error: 'faceit_core_data' not found
Solution: Initialize the plugin properly

python
import maya_faceit.core
maya_faceit.core.ensure_faceit_data_node()
Permissions Error on macOS/Linux
Solution: Set proper permissions

bash
chmod -R 755 /path/to/faceit/
chmod 755 /path/to/faceit/scripts/faceit_maya.py
Qt Version Conflicts
Solution: Maya 2026 uses PySide6 (Qt6). Ensure any custom code uses Qt6:

python
from PySide6 import QtWidgets, QtCore, QtGui
# Not PySide2!
Maya 2026 Specific Notes
PySide6/Qt6: All UI code should use PySide6

Python 3.10+: Maya 2026 uses Python 3.10 or 3.11

Module System: Maya 2026 uses module.json for module registration

API Changes: Some API functions may have been deprecated

🗑️ Uninstallation
Method 1: Remove Module Files
Windows:

cmd
rmdir /s "C:\Program Files\Common Files\Autodesk Shared\Modules\maya\2026\faceit"
macOS/Linux:

bash
rm -rf "/Library/Application Support/Autodesk/Modules/maya/2026/faceit"
Method 2: Using Python
python
import os
import shutil
import maya.cmds as cmds

# Unload the plugin
cmds.unloadPlugin("faceit_maya.py")

# Remove files
scripts_dir = cmds.internalVar(userScriptDir=True)
plugin_dir = os.path.join(scripts_dir, "maya_faceit")
plugin_file = os.path.join(scripts_dir, "faceit_maya.py")

if os.path.exists(plugin_dir):
    shutil.rmtree(plugin_dir)
    print("✓ Plugin files removed")

if os.path.exists(plugin_file):
    os.remove(plugin_file)
    print("✓ Plugin entry removed")
🔬 Development
Reloading During Development
python
import maya_faceit
maya_faceit.reload_plugin()
Running Tests
python
from maya_faceit.test import run_all_tests
run_all_tests()
Debug Mode
python
import maya_faceit
maya_faceit.DEBUG = True
Creating a Development Environment
python
# Set up development environment
import maya_faceit
maya_faceit.setup_development()
📚 Documentation
User Guide: https://faceit-doc.readthedocs.io/

API Reference: https://faceit-api.readthedocs.io/

Video Tutorials: https://www.youtube.com/c/Faceit

🤝 Contributing
Contributions are welcome! Please see our Contributing Guide for details.

Development Workflow
Fork the repository

Create a feature branch

Make your changes

Run tests

Submit a pull request

📄 License
This project is licensed under the MIT License - see the LICENSE file for details.

🙏 Acknowledgments
Original Blender Faceit plugin by the Faceit team

ARKit expression data from Apple

Audio2Face data from NVIDIA

Community contributors

📞 Contact & Support
Issues: GitHub Issues

Discussions: GitHub Discussions

Discord: Faceit Community Discord

📊 Version History
Version	Date	Changes
1.0.0	2024-01-15	Initial release for Maya 2026
0.9.0	2024-12-01	Beta release
Built with ❤️ for the Maya community

text

---

## Quick Reference Card

### Common Maya 2026 Commands

```python
# Load Plugin
cmds.loadPlugin("faceit_maya.py")

# Unload Plugin
cmds.unloadPlugin("faceit_maya.py")

# Check Plugin Status
cmds.pluginInfo("faceit_maya.py", query=True, loaded=True)

# Get Plugin Path
import maya_faceit
print(maya_faceit.__file__)

# Reload Plugin
import maya_faceit
maya_faceit.reload_plugin()

# Get Version
import maya_faceit
print(maya_faceit.__version__)
File Locations
Item	Path
User Scripts	~/Documents/maya/2026/scripts/
User Modules	~/Documents/maya/2026/modules/
System Modules	/Library/Application Support/Autodesk/Modules/maya/2026/
Module JSON	faceit/module.json
Plugin Entry	faceit/scripts/faceit_maya.py
Plugin Code	faceit/scripts/maya_faceit/
Resources	faceit/resources/
