# -*- coding: utf-8 -*-
"""
export/formats/maya_ascii.py

Maya ASCII (.ma) export.
"""

import maya.cmds as cmds # type: ignore
import os
from ..core.base import BaseExporter
from ..types import ExportResult


class MayaASCIIExporter(BaseExporter):
    """Maya ASCII format exporter."""

    def export(self) -> ExportResult:
        result = ExportResult(format=self.settings.format, filepath=self.settings.filepath)

        if not self.settings.filepath:
            result.errors.append("No filepath specified.")
            result.success = False
            return result

        try:
            if self.settings.objects:
                cmds.select(self.settings.objects, replace=True)
                cmds.file(self.settings.filepath, force=True, type='mayaAscii', exportSelected=True)
            else:
                cmds.file(self.settings.filepath, force=True, type='mayaAscii', exportAll=True)
            result.success = True
            result.objects_exported = len(self.settings.objects) if self.settings.objects else 0
        except Exception as e:
            result.errors.append(str(e))
            result.success = False

        return result