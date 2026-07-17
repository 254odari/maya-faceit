# -*- coding: utf-8 -*-
"""
tools/relax/engine.py

Core relaxation algorithms.
"""

import math
import numpy as np
from typing import List, Tuple, Dict, Set, Optional
from .types import RelaxSettings, RelaxAlgorithm


class RelaxEngine:
    """
    Core relaxation engine.
    Provides low-level relaxation algorithms on point arrays.
    """

    def __init__(self, settings: RelaxSettings):
        self.settings = settings
        self._use_numpy = settings and getattr(settings, 'use_numpy', True) and np is not None

    def relax_points(self, points: List[Tuple[float, float, float]],
                     adjacency: Dict[int, List[int]],
                     boundary: Set[int] = None) -> List[Tuple[float, float, float]]:
        """
        Apply relaxation to a list of points using adjacency info.
        Returns relaxed points.
        """
        if not points:
            return points

        # Choose algorithm
        if self.settings.algorithm == RelaxAlgorithm.LAPLACIAN:
            return self._laplacian_relax(points, adjacency, boundary)
        elif self.settings.algorithm == RelaxAlgorithm.HC:
            return self._hc_relax(points, adjacency, boundary)
        elif self.settings.algorithm == RelaxAlgorithm.TAUBIN:
            return self._taubin_relax(points, adjacency, boundary)
        else:
            return points

    # -------------------------------------------------------------------------
    # Laplacian Relaxation
    # -------------------------------------------------------------------------
    def _laplacian_relax(self, points: List[Tuple[float, float, float]],
                         adjacency: Dict[int, List[int]],
                         boundary: Set[int] = None) -> List[Tuple[float, float, float]]:
        """
        Simple Laplacian smoothing: move each vertex toward the average of its neighbors.
        """
        strength = self.settings.strength
        new_points = []
        for i, p in enumerate(points):
            if boundary and i in boundary:
                if self.settings.preserve_border:
                    new_points.append(p)
                    continue
            neighbors = adjacency.get(i, [])
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

    # -------------------------------------------------------------------------
    # HC (Humphrey's Classes) Relaxation
    # -------------------------------------------------------------------------
    def _hc_relax(self, points: List[Tuple[float, float, float]],
                  adjacency: Dict[int, List[int]],
                  boundary: Set[int] = None) -> List[Tuple[float, float, float]]:
        """
        HC algorithm: Laplacian smoothing with push-pull to preserve volume.
        Uses two passes: smoothing then correction.
        """
        # First pass: Laplacian smooth
        smoothed = self._laplacian_relax(points, adjacency, boundary)
        correction = 0.5
        new_points = []
        for i, (orig, sm) in enumerate(zip(points, smoothed)):
            if boundary and i in boundary and self.settings.preserve_border:
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

    # -------------------------------------------------------------------------
    # Taubin Relaxation
    # -------------------------------------------------------------------------
    def _taubin_relax(self, points: List[Tuple[float, float, float]],
                      adjacency: Dict[int, List[int]],
                      boundary: Set[int] = None) -> List[Tuple[float, float, float]]:
        """
        Taubin smoothing: two-step smoothing with positive and negative lambda.
        """
        lam = 0.5
        mu = -0.53
        temp_points = self._laplacian_with_lambda(points, adjacency, boundary, lam)
        final_points = self._laplacian_with_lambda(temp_points, adjacency, boundary, mu)
        return final_points

    def _laplacian_with_lambda(self, points: List[Tuple[float, float, float]],
                               adjacency: Dict[int, List[int]],
                               boundary: Set[int] = None,
                               lam: float = 0.5) -> List[Tuple[float, float, float]]:
        """
        Laplacian step with lambda parameter.
        """
        new_points = []
        for i, p in enumerate(points):
            if boundary and i in boundary and self.settings.preserve_border:
                new_points.append(p)
                continue
            neighbors = adjacency.get(i, [])
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