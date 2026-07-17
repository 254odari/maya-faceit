# API Reference

This section covers the public Python API of FaceIT.  
All core modules are documented with classes, methods, and usage examples.

## Core Packages

- [`blendshape_creator`](./blendshape_creator.md) – Create and configure targets.
- [`blendshape_combiner`](./blendshape_combiner.md) – Combine deltas.
- [`blendshape_delta`](./blendshape_delta.md) – Vertex delta operations.
- [`blendshape_driver`](./blendshape_driver.md) – Driving blendshapes from controllers.
- [`blendshape_generator`](./blendshape_generator.md) – Procedural generation.
- [`blendshape_pose`](./blendshape_pose.md) – Pose and expression management.
- [`blendshape_correctives`](./blendshape_correctives.md) – Corrective shapes.
- [`blendshape_inbetweens`](./blendshape_inbetweens.md) – Inbetween targets.
- [`blendshape_mirror`](./blendshape_mirror.md) – Mirror shapes.
- [`blendshape_normalize`](./blendshape_normalize.md) – Normalization utilities.
- [`blendshape_optimizer`](./blendshape_optimizer.md) – Performance optimization.
- [`blendshape_validator`](./blendshape_validator.md) – Validation.
- [`blendshape_transfer`](./blendshape_transfer.md) – Transfer between meshes.
- [`blendshape_exporter`](./blendshape_exporter.md) – Export to various formats.
- [`blendshape_library`](./blendshape_library.md) – Asset library.
- [`blendshape_manager`](./blendshape_manager.md) – Main orchestrator.
- [`blendshape_builder`](./blendshape_builder.md) – Build complete rigs.
- [`arkit_mapper`](./arkit_mapper.md) – ARKit mapping.
- [`blendshape_utils`](./blendshape_utils.md) – Shared utilities.

## UI API

- `ui.application` – Main window and workspace.
- `ui.controllers` – Controllers.
- `ui.models` – Data models.
- `ui.pages`, `ui.panels`, `ui.widgets` – UI components.

---

## Quick Example

```python
from maya_faceit.blendshapes import BlendshapeManager, BlendshapeCombination

manager = BlendshapeManager()
manager.scan_scene()

# Create a combined target
comb = BlendshapeCombination(
    name="Happy",
    sources=["Smile", "CheekRaise", "EyeSquint"],
    weights=[1.0, 0.5, 0.3]
)
result = manager.create_combined_target(comb, "head_geo")
print(result.success)