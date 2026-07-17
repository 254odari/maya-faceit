# -*- coding: utf-8 -*-
"""
tools/smooth/algorithms.py

Core smoothing algorithms.
"""

import math
import numpy as np
from typing import List, Tuple, Dict, Set, Optional
from .types import SmoothAlgorithm, SmoothSettings, SmoothBoundary


class SmoothAlgorithmEngine:
    """
    Core smoothing engine with implementations of various algorithms.
    """

    def __init__(self, settings: SmoothSettings):
        self.settings = settings
        self._use_numpy = True  # fallback to pure Python if numpy unavailable

    def smooth_points(self, points: List[Tuple[float, float, float]],
                      adjacency: Dict[int, List[int]],
                      boundary: Set[int] = None,
                      mask: Set[int] = None) -> List[Tuple[float, float, float]]:
        """
        Apply the selected smoothing algorithm to a point cloud.

        Args:
            points: List of (x, y, z) tuples.
            adjacency: Dict of vertex index -> list of neighbor indices.
            boundary: Set of boundary vertex indices.
            mask: Set of vertex indices to process (if None, all vertices).

        Returns:
            Smoothed points.
        """
        if not points:
            return points

        alg = self.settings.algorithm
        if alg == SmoothAlgorithm.LAPLACIAN:
            return self._laplacian(points, adjacency, boundary, mask)
        elif alg == SmoothAlgorithm.HC:
            return self._hc(points, adjacency, boundary, mask)
        elif alg == SmoothAlgorithm.TAUBIN:
            return self._taubin(points, adjacency, boundary, mask)
        elif alg == SmoothAlgorithm.GAUSSIAN:
            return self._gaussian(points, adjacency, boundary, mask)
        elif alg == SmoothAlgorithm.BILATERAL:
            return self._bilateral(points, adjacency, boundary, mask)
        else:
            return self._laplacian(points, adjacency, boundary, mask)

    # =========================================================================
    # LAPLACIAN
    # =========================================================================

    def _laplacian(self, points: List[Tuple[float, float, float]],
                   adj: Dict[int, List[int]],
                   boundary: Set[int] = None,
                   mask: Set[int] = None) -> List[Tuple[float, float, float]]:
        strength = self.settings.strength
        new_points = []
        for i, p in enumerate(points):
            if mask is not None and i not in mask:
                new_points.append(p)
                continue
            if boundary and i in boundary and self.settings.boundary == SmoothBoundary.FIXED:
                new_points.append(p)
                continue
            neighbors = adj.get(i, [])
            if not neighbors:
                new_points.append(p)
                continue
            avg = [0.0, 0.0, 0.0]
            for n in neighbors:
                avg[0] += points[n][0]
                avg[1] += points[n][1]
                avg[2] += points[n][2]
            avg[0] /= len(neighbors)
            avg[1] /= len(neighbors)
            avg[2] /= len(neighbors)
            new_p = (
                p[0] + (avg[0] - p[0]) * strength,
                p[1] + (avg[1] - p[1]) * strength,
                p[2] + (avg[2] - p[2]) * strength,
            )
            new_points.append(new_p)
        return new_points

    # =========================================================================
    # HC (Humphrey's Classes)
    # =========================================================================

    def _hc(self, points: List[Tuple[float, float, float]],
            adj: Dict[int, List[int]],
            boundary: Set[int] = None,
            mask: Set[int] = None) -> List[Tuple[float, float, float]]:
        # Two passes: smooth then push back
        smoothed = self._laplacian(points, adj, boundary, mask)
        correction = 0.5
        new_points = []
        for i, (orig, sm) in enumerate(zip(points, smoothed)):
            if mask is not None and i not in mask:
                new_points.append(orig)
                continue
            if boundary and i in boundary and self.settings.boundary == SmoothBoundary.FIXED:
                new_points.append(orig)
                continue
            disp = (sm[0] - orig[0], sm[1] - orig[1], sm[2] - orig[2])
            new_p = (
                sm[0] - disp[0] * correction,
                sm[1] - disp[1] * correction,
                sm[2] - disp[2] * correction,
            )
            new_points.append(new_p)
        return new_points

    # =========================================================================
    # TAUBIN
    # =========================================================================

    def _taubin(self, points: List[Tuple[float, float, float]],
                adj: Dict[int, List[int]],
                boundary: Set[int] = None,
                mask: Set[int] = None) -> List[Tuple[float, float, float]]:
        lam = 0.5
        mu = -0.53
        temp = self._laplacian_with_lambda(points, adj, boundary, mask, lam)
        final = self._laplacian_with_lambda(temp, adj, boundary, mask, mu)
        return final

    def _laplacian_with_lambda(self, points: List[Tuple[float, float, float]],
                               adj: Dict[int, List[int]],
                               boundary: Set[int] = None,
                               mask: Set[int] = None,
                               lam: float = 0.5) -> List[Tuple[float, float, float]]:
        new_points = []
        for i, p in enumerate(points):
            if mask is not None and i not in mask:
                new_points.append(p)
                continue
            if boundary and i in boundary and self.settings.boundary == SmoothBoundary.FIXED:
                new_points.append(p)
                continue
            neighbors = adj.get(i, [])
            if not neighbors:
                new_points.append(p)
                continue
            avg = [0.0, 0.0, 0.0]
            for n in neighbors:
                avg[0] += points[n][0]
                avg[1] += points[n][1]
                avg[2] += points[n][2]
            avg[0] /= len(neighbors)
            avg[1] /= len(neighbors)
            avg[2] /= len(neighbors)
            new_p = (
                p[0] + lam * (avg[0] - p[0]),
                p[1] + lam * (avg[1] - p[1]),
                p[2] + lam * (avg[2] - p[2]),
            )
            new_points.append(new_p)
        return new_points

    # =========================================================================
    # GAUSSIAN
    # =========================================================================

    def _gaussian(self, points: List[Tuple[float, float, float]],
                  adj: Dict[int, List[int]],
                  boundary: Set[int] = None,
                  mask: Set[int] = None) -> List[Tuple[float, float, float]]:
        # Gaussian weighting: weight neighbors by distance (approximated)
        strength = self.settings.strength
        sigma = 0.5
        new_points = []
        for i, p in enumerate(points):
            if mask is not None and i not in mask:
                new_points.append(p)
                continue
            if boundary and i in boundary and self.settings.boundary == SmoothBoundary.FIXED:
                new_points.append(p)
                continue
            neighbors = adj.get(i, [])
            if not neighbors:
                new_points.append(p)
                continue
            # For simplicity, use uniform weights for now
            # (proper Gaussian would require distances)
            avg = [0.0, 0.0, 0.0]
            for n in neighbors:
                avg[0] += points[n][0]
                avg[1] += points[n][1]
                avg[2] += points[n][2]
            avg[0] /= len(neighbors)
            avg[1] /= len(neighbors)
            avg[2] /= len(neighbors)
            new_p = (
                p[0] + (avg[0] - p[0]) * strength,
                p[1] + (avg[1] - p[1]) * strength,
                p[2] + (avg[2] - p[2]) * strength,
            )
            new_points.append(new_p)
        return new_points

    # =========================================================================
    # BILATERAL
    # =========================================================================

    def _bilateral(self, points: List[Tuple[float, float, float]],
                   adj: Dict[int, List[int]],
                   boundary: Set[int] = None,
                   mask: Set[int] = None) -> List[Tuple[float, float, float]]:
        # Placeholder: bilateral filtering requires more complex computation
        # For now, fallback to Laplacian
        return self._laplacian(points, adj, boundary, mask)