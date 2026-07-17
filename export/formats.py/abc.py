# -*- coding: utf-8 -*-
"""
export/formats/abc.py

Alembic export using Maya's Alembic plugin.
"""

import maya.cmds as cmds # type: ignore
import os
from ..core.base import BaseExporter
from ..types import ExportResult


class ABCExporter(BaseExporter):
    """Alembic format exporter."""

    def export(self) -> ExportResult:
        result = ExportResult(format=self.settings.format, filepath=self.settings.filepath)

        if not self.settings.filepath:
            result.errors.append("No filepath specified.")
            result.success = False
            return result

        # Ensure Alembic plugin is loaded
        if not cmds.pluginInfo('AbcExport', q=True, loaded=True):
            try:
                cmds.loadPlugin('AbcExport')
            except:
                result.errors.append("Alembic plugin could not be loaded.")
                result.success = False
                return result

        try:
            # Use AbcExport command
            options = []
            if self.settings.include_animation:
                options.append("-frameRange {} {}".format(self.settings.start_frame, self.settings.end_frame))
            if self.settings.include_blendshapes:
                options.append("-blendShapes")
            if self.settings.include_skin:
                options.append("-skin")
            options_str = " ".join(options)
            cmds.AbcExport(
                j=f"-selection -f {self.settings.filepath} {options_str}"
            )
            result.success = True
            result.objects_exported = len(self.settings.objects) if self.settings.objects else 0
        except Exception as e:
            result.errors.append(str(e))
            result.success = False

        return result