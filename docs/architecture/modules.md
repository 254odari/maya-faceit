# Module Breakdown

## Core Modules

| Module | Responsibility |
|--------|----------------|
| `blendshape_creator` | Create blendshape targets and nodes. |
| `blendshape_combiner` | Combine multiple deltas (add, average, max, etc.). |
| `blendshape_delta` | Compute and store vertex deltas. |
| `blendshape_driver` | Connect blendshapes to controllers, joints, ARKit. |
| `blendshape_generator` | Procedural generation (ARKit, visemes, emotions). |
| `blendshape_pose` | Manage poses and expression libraries. |
| `blendshape_correctives` | Generate corrective shapes. |
| `blendshape_inbetweens` | Handle intermediate inbetween targets. |
| `blendshape_mirror` | Mirror shapes across symmetry planes. |
| `blendshape_normalize` | Normalize weights, deltas, and poses. |
| `blendshape_optimizer` | Runtime optimization (compression, pruning). |
| `blendshape_validator` | Validate meshes, weights, and rigs. |
| `blendshape_transfer` | Transfer shapes between meshes. |
| `blendshape_exporter` | Export to FBX, USD, Alembic, etc. |
| `blendshape_library` | Asset library management. |
| `blendshape_manager` | Orchestrates all operations (facade). |
| `blendshape_builder` | Assemble complete rig systems. |
| `arkit_mapper` | ARKit channel ↔ blendshape mapping. |

## UI Modules

| Module | Responsibility |
|--------|----------------|
| `ui.application` | Main window, dock manager, workspace. |
| `ui.pages` | Workspace pages (Rig, Blendshapes, etc.). |
| `ui.panels` | Dockable panels (Inspector, Log, etc.). |
| `ui.dialogs` | Modal dialogs (Preferences, Export, etc.). |
| `ui.widgets` | Reusable Qt widgets (Tree, Slider, Canvas, etc.). |
| `ui.models` | Data models (Project, Rig, Blendshape, etc.). |
| `ui.controllers` | Controllers bridging UI and core. |
| `ui.themes` | Color palettes, icons, stylesheets. |

## Utility Modules

| Module | Responsibility |
|--------|----------------|
| `blendshape_utils` | Common math, naming, mesh operations. |
| `symmetry` | Symmetry engine for mirroring and correction. |

---

## Dependencies

- **Maya Python API** – `maya.cmds`, `pymel`
- **Qt** – `PySide2` (or `PyQt5`)
- **NumPy** – optional for high‑performance math
- **SciPy** – optional for KD‑tree nearest neighbor
- **JSON** – for project serialization