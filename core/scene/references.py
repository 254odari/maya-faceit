"""
core/scene/references.py

Reference management utilities for Maya Faceit.
"""

import maya.cmds as cmds # type: ignore
from pathlib import Path
from typing import List, Optional, Dict, Tuple

from ..logging.logger import log


class ReferenceUtils:
    """
    Utilities for working with Maya references.
    """

    @staticmethod
    def is_referenced(node: str) -> bool:
        """
        Check if a node is part of a reference.

        Returns:
            True if node is referenced.
        """
        if not cmds.objExists(node):
            return False
        return cmds.referenceQuery(node, isNodeReferenced=True)

    @staticmethod
    def get_reference_node(node: str) -> Optional[str]:
        """
        Get the reference node that contains the given node.

        Returns:
            Reference node name, or None.
        """
        if not cmds.objExists(node):
            return None
        if not ReferenceUtils.is_referenced(node):
            return None
        return cmds.referenceQuery(node, referenceNode=True)

    @staticmethod
    def get_reference_file(reference_node: str) -> Optional[str]:
        """
        Get the file path of a reference node.

        Returns:
            File path as string, or None.
        """
        if not cmds.objExists(reference_node):
            return None
        try:
            return cmds.referenceQuery(reference_node, filename=True)
        except:
            return None

    @staticmethod
    def get_all_references() -> List[Tuple[str, str]]:
        """
        List all references in the scene.

        Returns:
            List of (reference_node, filepath) tuples.
        """
        ref_nodes = cmds.ls(type='reference')
        result = []
        for rn in ref_nodes:
            if rn in ['sharedReferenceNode', 'defaultReferenceNode']:
                continue
            filepath = ReferenceUtils.get_reference_file(rn)
            if filepath:
                result.append((rn, filepath))
        return result

    @staticmethod
    def get_referenced_nodes(reference_node: str) -> List[str]:
        """
        Get all nodes inside a specific reference.

        Returns:
            List of node names.
        """
        if not cmds.objExists(reference_node):
            return []
        return cmds.referenceQuery(reference_node, nodes=True) or []

    @staticmethod
    def reload_reference(reference_node: str) -> bool:
        """
        Reload a reference.

        Returns:
            True if successful.
        """
        if not cmds.objExists(reference_node):
            return False
        try:
            cmds.file(reference_node, reloadReference=True)
            log.info(f"Reloaded reference: {reference_node}")
            return True
        except Exception as e:
            log.error(f"Failed to reload reference {reference_node}: {e}")
            return False

    @staticmethod
    def replace_reference(reference_node: str, new_filepath: str) -> bool:
        """
        Replace a reference with a different file.

        Returns:
            True if successful.
        """
        if not cmds.objExists(reference_node):
            return False
        try:
            cmds.file(new_filepath, loadReference=reference_node)
            log.info(f"Replaced reference {reference_node} with {new_filepath}")
            return True
        except Exception as e:
            log.error(f"Failed to replace reference: {e}")
            return False

    @staticmethod
    def remove_reference(reference_node: str) -> bool:
        """
        Remove a reference from the scene.

        Returns:
            True if successful.
        """
        if not cmds.objExists(reference_node):
            return False
        try:
            cmds.file(removeReference=True, referenceNode=reference_node)
            log.info(f"Removed reference: {reference_node}")
            return True
        except Exception as e:
            log.error(f"Failed to remove reference: {e}")
            return False

    @staticmethod
    def import_reference(reference_node: str) -> bool:
        """
        Import a reference (convert to local nodes).

        Returns:
            True if successful.
        """
        if not cmds.objExists(reference_node):
            return False
        try:
            cmds.file(importReference=True, referenceNode=reference_node)
            log.info(f"Imported reference: {reference_node}")
            return True
        except Exception as e:
            log.error(f"Failed to import reference: {e}")
            return False

    @staticmethod
    def find_missing_references() -> List[str]:
        """
        Find references with missing files.

        Returns:
            List of reference nodes with missing files.
        """
        missing = []
        for rn, fp in ReferenceUtils.get_all_references():
            if not Path(fp).exists():
                missing.append(rn)
        return missing

    @staticmethod
    def is_reference_loaded(reference_node: str) -> bool:
        """
        Check if a reference is currently loaded.

        Returns:
            True if loaded.
        """
        if not cmds.objExists(reference_node):
            return False
        return cmds.referenceQuery(reference_node, isLoaded=True)