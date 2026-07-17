# -*- coding: utf-8 -*-
"""
tools.mesh.core.cache
~~~~~~~~~~~~~~~~~~~~~

Mesh cache with topology fingerprinting.
"""

import json
import hashlib
import os
from pathlib import Path
from typing import Dict, Optional, Any
import maya.cmds as cmds # type: ignore
from ..settings import MeshSettings

class MeshCache:
    """Persistent cache for mesh data."""
    def __init__(self, settings: MeshSettings):
        self.settings = settings
        self._cache: Dict[str, Dict] = {}
        if settings.cache_enabled and settings.cache_directory:
            self.cache_dir = Path(settings.cache_directory)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.cache_dir = None

    def get(self, mesh: str) -> Optional[Dict]:
        """Retrieve cached data for mesh."""
        key = self._compute_key(mesh)
        if key in self._cache:
            return self._cache[key]
        if self.cache_dir:
            path = self.cache_dir / f"{key}.json"
            if path.exists():
                with open(path, 'r') as f:
                    data = json.load(f)
                self._cache[key] = data
                return data
        return None

    def set(self, mesh: str, data: Dict):
        """Store cached data for mesh."""
        key = self._compute_key(mesh)
        self._cache[key] = data
        if self.cache_dir:
            path = self.cache_dir / f"{key}.json"
            with open(path, 'w') as f:
                json.dump(data, f, indent=2, default=str)

    def invalidate(self, mesh: str):
        """Remove cached data for mesh."""
        key = self._compute_key(mesh)
        if key in self._cache:
            del self._cache[key]
        if self.cache_dir:
            path = self.cache_dir / f"{key}.json"
            if path.exists():
                path.unlink()

    def _compute_key(self, mesh: str) -> str:
        """Compute a unique key (topology hash) for a mesh."""
        # Use vertex and face counts, plus bounding box for uniqueness
        vtx = cmds.polyEvaluate(mesh, vertex=True)
        faces = cmds.polyEvaluate(mesh, face=True)
        bbox = cmds.exactWorldBoundingBox(mesh)
        data = f"{mesh}_{vtx}_{faces}_{bbox}"
        return hashlib.md5(data.encode()).hexdigest()