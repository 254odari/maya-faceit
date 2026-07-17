# Data Flow & State Management

FaceIT uses a unidirectional data flow inspired by Redux (but simplified). State is held in the models, and controllers dispatch actions that modify state and trigger UI updates.

## State Model

- `ProjectModel` – Top‑level container (name, path, rig, blendshapes, ARKit mapping).
- `RigModel` – Joints, controllers, prefix, template.
- `BlendshapeModel` – List of targets, weights, locks.
- `ARKitModel` – Channel‑target mapping, coverage.
- `MocapModel` – Device connection, recording status.
- `PickerModel` – Expression items (name → weight dict).

## Actions

Examples:
- `CREATE_TARGET(name, mesh)`
- `SET_WEIGHT(target, weight)`
- `MIRROR_TARGET(source, direction)`
- `OPTIMIZE_ALL()`
- `EXPORT(format, path)`

## Flow

For operations that modify the Maya scene, the service directly calls Maya commands and then updates the model accordingly.

## Undo/Redo

Undo is implemented using Maya’s native undo system (`cmds.undoInfo`). Each major operation is wrapped in a chunk, allowing the user to undo/redo through Maya’s history.

## Project Persistence

Projects are saved as JSON files containing:
- Project metadata (name, path, template, FPS).
- Rig configuration (joints, controllers).
- Blendshape target names and metadata (no vertex data, only references).
- ARKit mapping.
- Mocap settings.

Actual mesh data is stored inside the Maya scene; the project file only references it by name.

This keeps the project file lightweight and ensures compatibility with version control.
For operations that modify the Maya scene, the service directly calls Maya commands and then updates the model accordingly.

## Undo/Redo

Undo is implemented using Maya’s native undo system (`cmds.undoInfo`). Each major operation is wrapped in a chunk, allowing the user to undo/redo through Maya’s history.

## Project Persistence

Projects are saved as JSON files containing:
- Project metadata (name, path, template, FPS).
- Rig configuration (joints, controllers).
- Blendshape target names and metadata (no vertex data, only references).
- ARKit mapping.
- Mocap settings.

Actual mesh data is stored inside the Maya scene; the project file only references it by name.

This keeps the project file lightweight and ensures compatibility with version control.