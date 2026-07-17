# -*- coding: utf-8 -*-
"""
maya_faceit.utils.geometry
~~~~~~~~~~~~~~~~~~~~~~~~~~

General geometry utilities.
"""

from typing import Tuple, List, Optional, math
from .math import MathUtils


class GeometryUtils:
    """Utilities for geometric calculations."""

    @staticmethod
    def line_intersection(p1: Tuple[float, float, float],
                          p2: Tuple[float, float, float],
                          p3: Tuple[float, float, float],
                          p4: Tuple[float, float, float]) -> Optional[Tuple[float, float, float]]:
        """Find intersection of two lines (or closest point if skew)."""
        # Not fully implemented; returns None
        return None

    @staticmethod
    def point_on_plane(point: Tuple[float, float, float],
                       plane_point: Tuple[float, float, float],
                       plane_normal: Tuple[float, float, float]) -> float:
        """Get signed distance from a point to a plane."""
        nx, ny, nz = plane_normal
        px, py, pz = plane_point
        qx, qy, qz = point
        return nx*(qx-px) + ny*(qy-py) + nz*(qz-pz)

    @staticmethod
    def project_point_on_plane(point: Tuple[float, float, float],
                               plane_point: Tuple[float, float, float],
                               plane_normal: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """Project a point onto a plane."""
        d = GeometryUtils.point_on_plane(point, plane_point, plane_normal)
        nx, ny, nz = plane_normal
        return (point[0] - d*nx, point[1] - d*ny, point[2] - d*nz)

    @staticmethod
    def distance_point_to_plane(point: Tuple[float, float, float],
                                plane_point: Tuple[float, float, float],
                                plane_normal: Tuple[float, float, float]) -> float:
        """Absolute distance from point to plane."""
        return abs(GeometryUtils.point_on_plane(point, plane_point, plane_normal))

    @staticmethod
    def closest_point_on_line(p: Tuple[float, float, float],
                              a: Tuple[float, float, float],
                              b: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """Closest point on line AB to point P."""
        ax, ay, az = a
        bx, by, bz = b
        px, py, pz = p
        # Vector AB
        vx, vy, vz = bx-ax, by-ay, bz-az
        # Vector AP
        wx, wy, wz = px-ax, py-ay, pz-az
        t = (wx*vx + wy*vy + wz*vz) / (vx*vx + vy*vy + vz*vz + 1e-12)
        t = max(0, min(1, t))
        return (ax + t*vx, ay + t*vy, az + t*vz)

    @staticmethod
    def distance_point_to_line(p: Tuple[float, float, float],
                               a: Tuple[float, float, float],
                               b: Tuple[float, float, float]) -> float:
        """Distance from point to line."""
        closest = GeometryUtils.closest_point_on_line(p, a, b)
        return MathUtils.distance(p, closest)

    @staticmethod
    def triangle_area(p1: Tuple[float, float, float],
                      p2: Tuple[float, float, float],
                      p3: Tuple[float, float, float]) -> float:
        """Area of a triangle."""
        v1 = (p2[0]-p1[0], p2[1]-p1[1], p2[2]-p1[2])
        v2 = (p3[0]-p1[0], p3[1]-p1[1], p3[2]-p1[2])
        cross = MathUtils.cross(v1, v2)
        return 0.5 * math.sqrt(cross[0]**2 + cross[1]**2 + cross[2]**2)

    @staticmethod
    def triangle_normal(p1: Tuple[float, float, float],
                        p2: Tuple[float, float, float],
                        p3: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """Normal of a triangle."""
        v1 = (p2[0]-p1[0], p2[1]-p1[1], p2[2]-p1[2])
        v2 = (p3[0]-p1[0], p3[1]-p1[1], p3[2]-p1[2])
        return MathUtils.normalize(MathUtils.cross(v1, v2))

    @staticmethod
    def polygon_centroid(points: List[Tuple[float, float, float]]) -> Tuple[float, float, float]:
        """Centroid of a polygon (assuming planar)."""
        return MathUtils.centroid(points)