# -*- coding: utf-8 -*-
"""
export/formats/usd.py

USD export using Maya's USD plugin.
"""

import maya.cmds as cmds # type: ignore
import os
from ..core.base import BaseExporter
from ..types import ExportResult


class USDExporter(BaseExporter):
    """USD format exporter."""

    def export(self) -> ExportResult:
        result = ExportResult(format=self.settings.format, filepath=self.settings.filepath)

        if not self.settings.filepath:
            result.errors.append("No filepath specified.")
            result.success = False
            return result

        # Ensure USD plugin is loaded
        if not cmds.pluginInfo('mayaUsdPlugin', q=True, loaded=True):
            try:
                cmds.loadPlugin('mayaUsdPlugin')
            except:
                result.errors.append("USD plugin could not be loaded.")
                result.success = False
                return result

        try:
            # Use Maya's USD export
            cmds.mayaUSDExport(
                file=self.settings.filepath,
                selection=len(self.settings.objects) > 0,
                defaultMeshScheme='catmullClark',
                exportColorSets=True,
                exportUVs=True,
                exportDisplayColor=True
            )
            result.success = True
            result.objects_exported = len(self.settings.objects) if self.settings.objects else 0
        except Exception as e:
            result.errors.append(str(e))
            result.success = False

        return result