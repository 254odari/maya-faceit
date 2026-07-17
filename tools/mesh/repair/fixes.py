# -*- coding: utf-8 -*-
"""
tools.mesh.repair.fixes
~~~~~~~~~~~~~~~~~~~~~~~

Individual mesh repair functions.

Each function focuses on fixing a specific mesh issue while preserving
as much of the original geometry as possible.
"""

import maya.cmds as cmds # type: ignore
import maya.api.OpenMaya as om2 # type: ignore
from typing import List, Optional, Tuple, Set,Dict, Any


class MeshFixes:
    """
    Collection of static methods for individual mesh repairs.
    """

    # =====================================================================
    # TOPOLOGY REPAIRS
    # =====================================================================

    @staticmethod
    def merge_duplicate_vertices(mesh: str, tolerance: float = 0.001) -> bool:
        """
        Merge vertices that are within the specified tolerance.

        Args:
            mesh: Name of the mesh
            tolerance: Maximum distance for vertices to be considered duplicates

        Returns:
            True if successful
        """
        if not cmds.objExists(mesh):
            return False
        try:
            # Select all vertices and merge
            cmds.select(f"{mesh}.vtx[*]", replace=True)
            cmds.polyMergeVertex(mesh, d=tolerance, am=True, ch=False)
            # Also try polyMergeVertex with a slightly larger tolerance for safety
            cmds.polyMergeVertex(mesh, d=tolerance * 0.5, am=True, ch=False)
            return True
        except Exception as e:
            print(f"Failed to merge duplicate vertices: {e}")
            return False

    @staticmethod
    def fix_non_manifold_edges(mesh: str) -> bool:
        """
        Attempt to fix non-manifold edges by separating faces or deleting
        problematic geometry.

        Uses multiple strategies:
        1. Try to select non-manifold edges and separate them
        2. If that fails, attempt to clean via polyChipOff

        Args:
            mesh: Name of the mesh

        Returns:
            True if successful
        """
        if not cmds.objExists(mesh):
            return False

        try:
            # Strategy 1: Select and separate non-manifold edges
            non_manifold = cmds.polyInfo(mesh, nonManifoldEdges=True) or []
            if non_manifold:
                # Try polyChipOff with non-manifold option
                cmds.polyChipOff(mesh, nm=True, ch=False)
                return True
            return False
        except Exception as e:
            print(f"Failed to fix non-manifold edges: {e}")
            return False

    @staticmethod
    def fix_lamina_faces(mesh: str) -> bool:
        """
        Remove lamina faces (faces that share the same vertices).

        Uses polyChipOff with the lamina face option.

        Args:
            mesh: Name of the mesh

        Returns:
            True if successful
        """
        if not cmds.objExists(mesh):
            return False

        try:
            # Use polyChipOff to remove lamina faces
            cmds.polyChipOff(mesh, lm=True, ch=False)
            return True
        except Exception as e:
            print(f"Failed to fix lamina faces: {e}")
            return False

    @staticmethod
    def delete_history(mesh: str, preserve_deformers: bool = True) -> bool:
        """
        Delete construction history from the mesh.

        Args:
            mesh: Name of the mesh
            preserve_deformers: If True, only delete non-deformer history

        Returns:
            True if successful
        """
        if not cmds.objExists(mesh):
            return False

        try:
            if preserve_deformers:
                cmds.delete(mesh, ch=True, nonDeformerHistory=True)
            else:
                cmds.delete(mesh, ch=True)
            return True
        except Exception as e:
            print(f"Failed to delete history: {e}")
            return False

    @staticmethod
    def remove_isolated_vertices(mesh: str) -> bool:
        """
        Remove vertices that are not connected to any face.

        Args:
            mesh: Name of the mesh

        Returns:
            True if successful
        """
        if not cmds.objExists(mesh):
            return False

        try:
            # Select isolated vertices
            isolated = cmds.polyInfo(mesh, isolatedVertices=True) or []
            if isolated:
                # Parse vertex indices from the output
                vert_indices = []
                for line in isolated:
                    # Lines look like: "Vertex 123 is isolated"
                    parts = line.split()
                    if len(parts) >= 2 and parts[0] == "Vertex":
                        try:
                            idx = int(parts[1])
                            vert_indices.append(idx)
                        except ValueError:
                            pass
                if vert_indices:
                    # Select and delete isolated vertices
                    cmds.select([f"{mesh}.vtx[{i}]" for i in vert_indices], replace=True)
                    cmds.delete()
                    return True
            return False
        except Exception as e:
            print(f"Failed to remove isolated vertices: {e}")
            return False

    @staticmethod
    def close_open_borders(mesh: str) -> bool:
        """
        Close open borders by creating faces between border edges.

        Uses polyCloseBorder to automatically close holes.

        Args:
            mesh: Name of the mesh

        Returns:
            True if successful
        """
        if not cmds.objExists(mesh):
            return False

        try:
            # Select the mesh and close borders
            cmds.select(mesh, replace=True)
            cmds.polyCloseBorder(mesh, ch=False)
            return True
        except Exception as e:
            print(f"Failed to close open borders: {e}")
            return False

    @staticmethod
    def triangulate_ngons(mesh: str, max_sides: int = 4) -> int:
        """
        Triangulate faces with more than max_sides vertices.

        Args:
            mesh: Name of the mesh
            max_sides: Maximum number of sides before triangulation

        Returns:
            Number of faces triangulated
        """
        if not cmds.objExists(mesh):
            return 0

        try:
            # Find faces with too many sides
            ngon_faces = []
            face_count = cmds.polyEvaluate(mesh, face=True)
            for i in range(face_count):
                try:
                    sides = cmds.polyEvaluate(mesh, faceVertexCount=i)
                    if sides > max_sides:
                        ngon_faces.append(i)
                except:
                    pass

            if ngon_faces:
                # Select and triangulate those faces
                cmds.select([f"{mesh}.f[{i}]" for i in ngon_faces], replace=True)
                cmds.polyTriangulate(mesh, ch=False)
                return len(ngon_faces)
            return 0
        except Exception as e:
            print(f"Failed to triangulate ngons: {e}")
            return 0

    @staticmethod
    def remove_zero_area_faces(mesh: str, tolerance: float = 1e-6) -> int:
        """
        Remove faces with area below tolerance.

        Args:
            mesh: Name of the mesh
            tolerance: Minimum face area

        Returns:
            Number of faces removed
        """
        if not cmds.objExists(mesh):
            return 0

        try:
            # Use OpenMaya for accurate area calculation
            sel = om2.MSelectionList()
            sel.add(mesh)
            dag = sel.getDagPath(0)
            fn_mesh = om2.MFnMesh(dag)

            zero_faces = []
            for i in range(fn_mesh.numPolygons()):
                area = fn_mesh.getPolygonArea(i, om2.MSpace.kWorld)
                if area < tolerance:
                    zero_faces.append(i)

            if zero_faces:
                cmds.select([f"{mesh}.f[{i}]" for i in zero_faces], replace=True)
                cmds.delete()
                return len(zero_faces)
            return 0
        except Exception as e:
            print(f"Failed to remove zero-area faces: {e}")
            return 0

    @staticmethod
    def fix_inverted_normals(mesh: str) -> bool:
        """
        Unify normals to face outward.

        Args:
            mesh: Name of the mesh

        Returns:
            True if successful
        """
        if not cmds.objExists(mesh):
            return False

        try:
            cmds.select(mesh, replace=True)
            cmds.polyNormal(mesh, normalMode=0, userNormalMode=0, ch=False)
            return True
        except Exception as e:
            print(f"Failed to fix inverted normals: {e}")
            return False

    @staticmethod
    def clean_uvs(mesh: str) -> bool:
        """
        Clean up UVs by removing unused UVs and fixing overlapping issues.

        Args:
            mesh: Name of the mesh

        Returns:
            True if successful
        """
        if not cmds.objExists(mesh):
            return False

        try:
            # Get shape
            shape = cmds.listRelatives(mesh, shapes=True)[0]

            # Remove unused UVs
            cmds.polyUVSet(shape, removeUnused=True)

            # Try to fix overlaps using polyMapSewMove
            cmds.polyMapSewMove(shape, ch=False)

            return True
        except Exception as e:
            print(f"Failed to clean UVs: {e}")
            return False

    @staticmethod
    def soften_edges(mesh: str, angle: float = 30.0) -> bool:
        """
        Soften normals by setting a soft angle.

        Args:
            mesh: Name of the mesh
            angle: Angle threshold for softening

        Returns:
            True if successful
        """
        if not cmds.objExists(mesh):
            return False

        try:
            cmds.polySoftNormals(mesh, angle=angle)
            return True
        except Exception as e:
            print(f"Failed to soften edges: {e}")
            return False

    @staticmethod
    def harden_edges(mesh: str, edges: Optional[List[int]] = None) -> bool:
        """
        Harden edges (set crease to 1).

        Args:
            mesh: Name of the mesh
            edges: List of edge indices to harden (None = all edges)

        Returns:
            True if successful
        """
        if not cmds.objExists(mesh):
            return False

        try:
            if edges is not None and edges:
                cmds.polySetEdgeCrease(mesh, e=edges, v=1, ch=False)
            else:
                # Select all edges and harden
                cmds.polySetEdgeCrease(mesh, v=1, ch=False)
            return True
        except Exception as e:
            print(f"Failed to harden edges: {e}")
            return False

    @staticmethod
    def auto_repair_all(mesh: str, verbose: bool = False) -> Dict[str, Any]:
        """
        Run all automatic repairs on a mesh.

        Args:
            mesh: Name of the mesh
            verbose: If True, print progress

        Returns:
            Dictionary with repair results
        """
        results = {
            'merged_duplicates': False,
            'fixed_non_manifold': False,
            'fixed_lamina': False,
            'deleted_history': False,
            'removed_isolated': False,
            'closed_borders': False,
            'triangulated_ngons': 0,
            'removed_zero_area': 0,
            'fixed_normals': False,
            'cleaned_uvs': False,
            'softened_edges': False
        }

        if not cmds.objExists(mesh):
            return results

        # Sequential repairs
        results['merged_duplicates'] = MeshFixes.merge_duplicate_vertices(mesh)
        if verbose:
            print("Merged duplicates")

        results['fixed_non_manifold'] = MeshFixes.fix_non_manifold_edges(mesh)
        if verbose:
            print("Fixed non-manifold edges")

        results['fixed_lamina'] = MeshFixes.fix_lamina_faces(mesh)
        if verbose:
            print("Fixed lamina faces")

        results['removed_isolated'] = MeshFixes.remove_isolated_vertices(mesh)
        if verbose:
            print("Removed isolated vertices")

        results['closed_borders'] = MeshFixes.close_open_borders(mesh)
        if verbose:
            print("Closed open borders")

        results['triangulated_ngons'] = MeshFixes.triangulate_ngons(mesh, 4)
        if verbose:
            print(f"Triangulated {results['triangulated_ngons']} ngons")

        results['removed_zero_area'] = MeshFixes.remove_zero_area_faces(mesh)
        if verbose:
            print(f"Removed {results['removed_zero_area']} zero-area faces")

        results['fixed_normals'] = MeshFixes.fix_inverted_normals(mesh)
        if verbose:
            print("Fixed normals")

        results['cleaned_uvs'] = MeshFixes.clean_uvs(mesh)
        if verbose:
            print("Cleaned UVs")

        results['softened_edges'] = MeshFixes.soften_edges(mesh, 30.0)
        if verbose:
            print("Softened edges")

        # Final history cleanup
        results['deleted_history'] = MeshFixes.delete_history(mesh, preserve_deformers=True)
        if verbose:
            print("Deleted history")

        return results

    @staticmethod
    def freeze_transforms(mesh: str) -> bool:
        """
        Freeze transforms (set translate, rotate, scale to identity).

        Args:
            mesh: Name of the mesh

        Returns:
            True if successful
        """
        if not cmds.objExists(mesh):
            return False

        try:
            cmds.makeIdentity(mesh, apply=True, t=1, r=1, s=1, n=0)
            return True
        except Exception as e:
            print(f"Failed to freeze transforms: {e}")
            return False


# -----------------------------------------------------------------------------
# Convenience functions
# -----------------------------------------------------------------------------

def merge_duplicates(mesh: str, tolerance: float = 0.001) -> bool:
    """Convenience wrapper for merge_duplicate_vertices."""
    return MeshFixes.merge_duplicate_vertices(mesh, tolerance)

def fix_non_manifold(mesh: str) -> bool:
    """Convenience wrapper for fix_non_manifold_edges."""
    return MeshFixes.fix_non_manifold_edges(mesh)

def fix_lamina(mesh: str) -> bool:
    """Convenience wrapper for fix_lamina_faces."""
    return MeshFixes.fix_lamina_faces(mesh)

def delete_history(mesh: str, preserve_deformers: bool = True) -> bool:
    """Convenience wrapper for delete_history."""
    return MeshFixes.delete_history(mesh, preserve_deformers)

def auto_repair(mesh: str, verbose: bool = False) -> Dict[str, Any]:
    """Convenience wrapper for auto_repair_all."""
    return MeshFixes.auto_repair_all(mesh, verbose)


__all__ = [
    "MeshFixes",
    "merge_duplicates",
    "fix_non_manifold",
    "fix_lamina",
    "delete_history",
    "auto_repair",
]