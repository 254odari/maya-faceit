# Architecture Overview

FaceIT is built as a layered, modular system that separates UI, business logic, and data access. The architecture is designed for scalability, testability, and maintainability.

## High‑Level Layers

1. **UI Layer**  
   - PySide2-based dockable workspace (main window, panels, pages, dialogs).  
   - Themes, custom widgets, and controllers.

2. **Controller Layer**  
   - Mediates between UI and core services.  
   - Handles commands, undo/redo, and validation.

3. **Service Layer**  
   - Core blendshape operations (creation, combination, transfer, etc.).  
   - ARKit mapping, mocap integration, optimization.

4. **Data Layer**  
   - Models (dataclasses) for projects, rigs, blendshapes, ARKit, etc.  
   - Serialization/deserialization for project files.

5. **Maya Integration**  
   - Maya Python API (cmds, pymel) for scene manipulation.  
   - Wrappers for blendshape nodes, mesh operations, and animation.

---

## Component Diagram

---

## Key Design Patterns

- **Facade** – `BlendshapeManager` centralizes operations.
- **Observer** – Event system for UI updates (creation, deletion, mirroring).
- **Strategy** – Multiple combination modes, correspondence methods.
- **Command** – Undo/Redo support (planned).
- **MVC** – Strict separation of models, views, and controllers.

---

## Data Flow

1. User action (e.g., “Create Target”) triggers a controller method.
2. Controller validates input, calls the appropriate service.
3. Service performs the operation (e.g., creates a blendshape node).
4. Result is stored in the model and propagated to the UI via events.
5. UI updates panels, statistics, and the Maya viewport.

This ensures a responsive, decoupled system that can be extended with new features without breaking existing ones.