# -*- coding: utf-8 -*-
"""
tools.mesh.repair.__init__.py
~~~~~~~~~~~~~~~~~

Mesh repair tools.
"""

from .fixes import MeshFixes, merge_duplicates, fix_non_manifold, fix_lamina, delete_history, auto_repair
from .repair import MeshRepair, repair

__all__ = [
    "MeshFixes",
    "MeshRepair",
    "repair",
    "merge_duplicates",
    "fix_non_manifold",
    "fix_lamina",
    "delete_history",
    "auto_repair",
]