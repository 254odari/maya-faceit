# FaceIT for Maya

A work-in-progress port of [FaceIt](https://faceit-doc.readthedocs.io/) (Blender facial
rigging add-on) to Autodesk Maya 2026.

The original add-on is GPL-3.0-or-later, so this port is too (see `LICENSE`).

## Status: baseline

This branch is a **baseline repair**, not a finished tool:

- The package imports cleanly into Maya 2026 (116 modules) and loads/unloads as a
  plugin in headless mode; 120 operators and 6 scene callbacks register.
- Expression libraries and retarget presets are present under `maya_faceit/resources/`.
- `FaceitRig.ma`, `FaceitControlRig.ma` and `FaceitLandmarks.ma` are stubs or absent;
  the rigging/binding stages are not usable until they are rebuilt from the Blender
  assets (this requires Blender, which is not part of this baseline).
- Operator/UI behaviour has not been validated against the Blender original.

The previous 215k-line generated scaffold was removed from this branch; it remains
on `main` for reference.

## Layout

```
faceit_maya.py        Maya plugin entry point (initializePlugin / uninitializePlugin)
faceit_maya.mod       Maya module descriptor (the file Maya actually discovers)
module.json           Module metadata
maya_faceit/
  core/               ARKit shape data, scene data, mesh/vgroup/modifier utilities
  properties/         Scene property definitions
  setup/              Object registration and group assignment
  landmarks/          Landmark placement
  rigging/            Rig generation and joining
  bind/               Binding the face mesh to the rig
  ctrl_rig/           Control rig generation, drivers, custom sliders
  shape_keys/         Shape key and corrective shape authoring
  expressions/        (reserved)
  animate/            Expression animation
  mocap/              FaceCap / iFacialMocap / LiveLinkFace / OSC receivers
  retargeting/        ARKit retarget list
  retarget_fbx/       FBX retarget presets
  bake/               Bake shape keys and modifiers
  finalize/           Finalize rig
  panels/             UI
  resources/          .face expression libraries, retarget presets
```

## Install

1. Add the repository directory itself to `MAYA_MODULE_PATH` (for example in
   `Documents/maya/2026/Maya.env`):

   ```
   MAYA_MODULE_PATH += /path/to/maya-faceit
   ```

   Alternatively, copy `faceit_maya.mod` into `Documents/maya/modules/` and change
   the path on the `+` line to the repository location.

2. Restart Maya and load the plugin:

```python
import maya.cmds as cmds
cmds.loadPlugin("faceit_maya.py")
```

Or for development, without installing as a module:

```python
import sys
sys.path.insert(0, "/path/to/maya-faceit")
import maya_faceit
maya_faceit.initializePlugin(None)
```

## Known limitations

- `FaceitRig.ma` is a placeholder; rigging/binding stages are not usable yet.
- Blender-specific concepts (shape keys, modifiers, drivers) were remapped to Maya
  blendShapes and utility nodes only at the API level; behaviour is unverified.
- The original `.face` expression files describe poses for a Rigify rig, which has
  no Maya equivalent. They are kept as data until the Maya rig defines matching
  control names.
