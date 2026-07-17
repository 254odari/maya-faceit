"""
tools/mesh/repair/repair.py

MeshRepair - Automated repair operations for common mesh issues.
Works in conjunction with MeshValidator.
"""

from __future__ import annotations

import maya.cmds as cmds # type: ignore
from typing import List, Optional

from ..types import MeshSelection, MeshReport, MeshIssue
from ..core.editor import MeshEditor
from ..validation.validator import validator


class MeshRepair:
    """
    Automated mesh repair system.
    """

    def __init__(self):
        self.editor = MeshEditor()

    # =====================================================================
    # HIGH-LEVEL REPAIR
    # =====================================================================

    def run_full_repair(self, mesh: Optional[MeshSelection] = None) -> int:
        """Run all available repair operations and return number of fixes applied."""
        if not mesh:
            mesh = self.editor.get_active_shape()

        repaired_count = 0

        repaired_count += self.merge_duplicates(mesh)
        repaired_count += self.remove_lamina_faces(mesh)
        repaired_count += self.delete_isolated_vertices(mesh)
        repaired_count += self.close_holes(mesh)
        repaired_count += self.fix_normals(mesh)
        repaired_count += self.cleanup(mesh)

        return repaired_count

    def cleanup(self, mesh: Optional[MeshSelection] = None) -> int:
        """Standard Maya cleanup with safe settings."""
        if not mesh:
            mesh = self.editor.get_active_shape()

        cmds.polyClean(mesh,
                       cleanVertices=True,
                       cleanEdges=True,
                       cleanFaces=True,
                       cleanUVs=True)

        self.editor.delete_history(mesh)
        return 1  # Consider this one major cleanup operation

    # =====================================================================
    # SPECIFIC REPAIR FUNCTIONS
    # =====================================================================

    def merge_duplicates(self, mesh: str, distance: float = 0.0001) -> int:
        """Merge vertices that are very close to each other."""
        try:
            count_before = cmds.polyEvaluate(mesh, vertex=True)
            cmds.polyMergeVertex(mesh, distance=distance, constructionHistory=False)
            count_after = cmds.polyEvaluate(mesh, vertex=True)
            return count_before - count_after
        except:
            return 0

    def remove_lamina_faces(self, mesh: str) -> int:
        """Remove lamina (duplicate/overlapping) faces."""
        try:
            lamina = cmds.polyInfo(mesh, laminaFaces=True) or []
            if lamina:
                # Extract face IDs and delete them
                face_ids = [int(x.split()[-1]) for x in lamina if x.startswith("FACE")]
                if face_ids:
                    cmds.delete([f"{mesh}.f[{fid}]" for fid in face_ids])
                    return len(face_ids)
            return 0
        except:
            return 0

    def delete_isolated_vertices(self, mesh: str) -> int:
        """Remove vertices not connected to any geometry."""
        try:
            isolated = cmds.polyInfo(mesh, isolatedVertices=True) or []
            if isolated:
                vert_ids = [int(x.split()[-1]) for x in isolated if "VERTEX" in x]
                if vert_ids:
                    cmds.delete([f"{mesh}.vtx[{vid}]" for vid in vert_ids])
                    return len(vert_ids)
            return 0
        except:
            return 0

    def close_holes(self, mesh: str) -> int:
        """Fill holes in the mesh."""
        try:
            border_count_before = len(cmds.polyInfo(mesh, borderEdges=True) or [])
            cmds.polyCloseBorder(mesh, bridge=True)
            border_count_after = len(cmds.polyInfo(mesh, borderEdges=True) or [])
            return max(0, (border_count_before - border_count_after) // 2)
        except:
            return 0

    def fix_normals(self, mesh: str) -> int:
        """Fix normals (unlock + consistent direction)."""
        try:
            cmds.polyNormal(mesh, normalMode=2, userNormalMode=0, constructionHistory=False)  # Conform
            cmds.polySoftEdge(mesh, angle=180)  # Soften all
            return 1
        except:
            return 0

    def remove_non_manifold(self, mesh: str) -> int:
        """Attempt to repair non-manifold geometry."""
        # This is complex - often requires manual intervention
        # For now, we just merge close vertices as a first step
        return self.merge_duplicates(mesh, distance=0.001)

    def optimize(self, mesh: Optional[MeshSelection] = None) -> int:
        """Light optimization pass."""
        if not mesh:
            mesh = self.editor.get_active_shape()
        
        self.editor.delete_history(mesh)
        self.merge_duplicates(mesh, distance=0.0005)
        return 1

    # =====================================================================
    # BATCH REPAIR
    # =====================================================================

    def batch_repair(self, meshes: List[str]) -> dict:
        """Repair multiple meshes and return summary."""
        results = {}
        total_repaired = 0

        for mesh in meshes:
            count = self.run_full_repair(mesh)
            total_repaired += count
            results[mesh] = count

        return {
            "total_meshes": len(meshes),
            "total_repaired": total_repaired,
            "per_mesh": results
        }


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

repair = MeshRepair()

__all__ = ["MeshRepair", "repair"]