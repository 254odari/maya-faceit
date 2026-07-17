# -*- coding: utf-8 -*-
"""
export/formats/json.py

JSON export for FaceIT-specific data (poses, controllers, blendshapes, etc.)
"""

import json
import maya.cmds as cmds # type: ignore
from ..core.base import BaseExporter
from ..types import ExportResult


class JSONExporter(BaseExporter):
    """JSON format exporter for FaceIT data."""

    def export(self) -> ExportResult:
        result = ExportResult(format=self.settings.format, filepath=self.settings.filepath)

        if not self.settings.filepath:
            result.errors.append("No filepath specified.")
            result.success = False
            return result

        try:
            data = self._collect_data()
            with open(self.settings.filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            result.success = True
            result.objects_exported = len(data.get('objects', []))
        except Exception as e:
            result.errors.append(str(e))
            result.success = False

        return result

    def _collect_data(self) -> dict:
        """Collect FaceIT data from the scene."""
        data = {
            'format': 'faceit_json',
            'version': '1.0',
            'objects': []
        }
        objects = self.settings.objects or cmds.ls(selection=True, long=True)
        for obj in objects:
            obj_data = {
                'name': obj,
                'type': cmds.nodeType(obj),
                'attributes': {}
            }
            # Collect keyable attributes
            attrs = cmds.listAttr(obj, keyable=True) or []
            for attr in attrs:
                full = f"{obj}.{attr}"
                if cmds.objExists(full):
                    try:
                        obj_data['attributes'][attr] = cmds.getAttr(full)
                    except:
                        pass
            # Collect custom attributes
            custom = cmds.listAttr(obj, userDefined=True) or []
            for attr in custom:
                full = f"{obj}.{attr}"
                if cmds.objExists(full):
                    try:
                        obj_data['attributes'][attr] = cmds.getAttr(full)
                    except:
                        pass
            data['objects'].append(obj_data)
        return data