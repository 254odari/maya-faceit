# -*- coding: utf-8 -*-
"""
tools/symmetry/cache.py

Persistent cache for symmetry maps.
"""

import json
import hashlib
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any
import maya.cmds as cmds # type: ignore
from .types import (
    SymmetryMap, SymmetryPlane, VertexPair, ControllerPair,
    JointPair, BlendshapePair, SymmetrySettings, SymmetryAxis
)


class SymmetryCache:
    """
    Persistent cache for symmetry maps.
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        if cache_dir is None:
            cache_dir = Path(os.path.expanduser("~/.faceit/symmetry_cache"))
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def save_map(self, map_data: SymmetryMap, identifier: str) -> bool:
        filename = f"{identifier}_{map_data.checksum}.json"
        filepath = self.cache_dir / filename
        try:
            data = self._map_to_dict(map_data)
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            return True
        except Exception as e:
            return False

    def load_map(self, identifier: str, mesh: str) -> Optional[SymmetryMap]:
        checksum = self._compute_mesh_checksum(mesh)
        if not checksum:
            return None
        filepath = self.cache_dir / f"{identifier}_{checksum}.json"
        if not filepath.exists():
            return None
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            return self._dict_to_map(data)
        except Exception:
            return None

    def _compute_mesh_checksum(self, mesh: str) -> str:
        if not cmds.objExists(mesh):
            return ""
        vcount = cmds.polyEvaluate(mesh, vertex=True)
        fcount = cmds.polyEvaluate(mesh, face=True)
        bbox = cmds.exactWorldBoundingBox(mesh)
        data = f"{vcount}_{fcount}_{bbox}"
        return hashlib.md5(data.encode()).hexdigest()

    def _map_to_dict(self, map_data: SymmetryMap) -> Dict[str, Any]:
        result = {
            "mesh": map_data.mesh,
            "vertex_count": map_data.vertex_count,
            "symmetric_vertex_count": map_data.symmetric_vertex_count,
            "asymmetric_vertex_count": map_data.asymmetric_vertex_count,
            "created": map_data.created,
            "checksum": map_data.checksum,
            "settings": {
                "axis": map_data.settings.axis.value,
                "tolerance": map_data.settings.tolerance,
            },
            "plane": None,
            "vertices": [],
            "controllers": [],
            "joints": [],
            "blendshapes": [],
        }
        if map_data.plane:
            result["plane"] = {
                "axis": map_data.plane.axis.value,
                "center": map_data.plane.center,
                "normal": map_data.plane.normal,
                "confidence": map_data.plane.confidence,
            }
        for vp in map_data.vertices:
            result["vertices"].append((vp.vertex1, vp.vertex2, vp.distance, vp.confidence))
        for cp in map_data.controllers:
            result["controllers"].append((cp.source, cp.target, cp.confidence))
        for jp in map_data.joints:
            result["joints"].append((jp.source, jp.target, jp.confidence))
        for bp in map_data.blendshapes:
            result["blendshapes"].append((bp.source, bp.target, bp.confidence))
        return result

    def _dict_to_map(self, data: Dict[str, Any]) -> SymmetryMap:
        settings = SymmetrySettings(
            axis=SymmetryAxis(data["settings"]["axis"]),
            tolerance=data["settings"]["tolerance"],
        )
        plane = None
        if data.get("plane"):
            plane = SymmetryPlane(
                axis=SymmetryAxis(data["plane"]["axis"]),
                center=tuple(data["plane"]["center"]),
                normal=tuple(data["plane"]["normal"]),
                confidence=data["plane"]["confidence"],
            )
        vertices = [VertexPair(v[0], v[1], v[2], v[3]) for v in data.get("vertices", [])]
        controllers = [ControllerPair(c[0], c[1], confidence=c[2]) for c in data.get("controllers", [])]
        joints = [JointPair(j[0], j[1], confidence=j[2]) for j in data.get("joints", [])]
        blendshapes = [BlendshapePair(b[0], b[1], confidence=b[2]) for b in data.get("blendshapes", [])]
        return SymmetryMap(
            mesh=data.get("mesh", ""),
            vertices=vertices,
            controllers=controllers,
            joints=joints,
            blendshapes=blendshapes,
            vertex_count=data.get("vertex_count", 0),
            symmetric_vertex_count=data.get("symmetric_vertex_count", 0),
            asymmetric_vertex_count=data.get("asymmetric_vertex_count", 0),
            plane=plane,
            settings=settings,
            created=data.get("created", time.ctime()),
            checksum=data.get("checksum", ""),
        )