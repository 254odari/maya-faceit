
---

## `docs/api/blendshape_creator.md` (example module)

```markdown
# blendshape_creator

**Module:** `maya_faceit.blendshapes.blendshape_creator`

## Class: `BlendShapeCreator`

Main class for creating blendshape targets and nodes.

### Methods

#### `create_node(name, mesh, **kwargs) -> str`
Create a new `blendShape` node on the given mesh.

**Parameters:**
- `name` (str) – Name for the node.
- `mesh` (str) – Name of the base mesh.
- `**kwargs` – Additional attributes (e.g., `origin`, `weight`).

**Returns:** (str) The name of the created node.

#### `create_target(node, target) -> CreationResult`
Add a target to an existing blendshape node.

**Parameters:**
- `node` (str) – Name of the blendshape node.
- `target` (BlendShapeTarget) – Target definition (name, mesh, weight).

**Returns:** `CreationResult` with success, errors, and warnings.

#### `create_target_from_delta(node, delta, name, **kwargs) -> CreationResult`
Create a target from a `BlendshapeDelta` object.

---

## Class: `BlendShapeTarget`

Data class representing a target.

Attributes:
- `name` (str)
- `mesh` (str) – The target mesh (or `None` if using delta).
- `weight` (float) – Initial weight.
- `enabled` (bool)
- `metadata` (dict)

---

## Class: `CreationResult`

Result object from creation operations.

Attributes:
- `success` (bool)
- `target_name` (str)
- `errors` (list[str])
- `warnings` (list[str])
- `details` (dict)

---

## Example

```python
from maya_faceit.blendshapes import BlendShapeCreator, BlendShapeTarget

creator = BlendShapeCreator()
node = creator.create_node("my_bshape", "head_geo")
target = BlendShapeTarget(name="Smile", mesh="smile_target_geo")
result = creator.create_target(node, target)
if result.success:
    print(f"Target {result.target_name} created.")