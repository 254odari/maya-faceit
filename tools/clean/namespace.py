# -*- coding: utf-8 -*-
"""
tools/clean/namespace.py

Namespace cleanup.
"""

import maya.cmds as cmds # type: ignore
from .types import NamespaceCleanup


class NamespaceCleaner:
    """
    Clean up namespaces: remove empty namespaces, merge, flatten.
    """

    def __init__(self, settings):
        self.settings = settings

    def cleanup(self) -> NamespaceCleanup:
        """Run namespace cleanup."""
        result = NamespaceCleanup()

        if not self.settings.clean_namespace:
            return result

        namespaces = cmds.namespaceInfo(listOnlyNamespaces=True, recurse=True) or []
        # Filter out default namespaces
        default = [':', 'UI', 'shared']
        namespaces = [ns for ns in namespaces if ns not in default]

        for ns in namespaces:
            if self._is_referenced(ns):
                continue
            # Check if namespace has any contents
            contents = cmds.namespaceInfo(ns, listNamespace=True) or []
            if not contents:
                try:
                    cmds.namespace(removeNamespace=ns, mergeNamespaceWithRoot=True)
                    result.removed_namespaces += 1
                except:
                    pass
            elif self.settings.merge_namespaces:
                # Merge contents into root
                try:
                    cmds.namespace(moveNamespace=ns, mergeNamespaceWithRoot=True)
                    result.merged_namespaces += 1
                except:
                    pass

        return result

    def _is_referenced(self, node):
        # Namespaces are not typically referenced; we'll skip
        return False