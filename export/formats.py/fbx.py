# -*- coding: utf-8 -*-
"""
export/formats/fbx.py

FBX export implementation using Maya's FBX plugin.
"""

import maya.cmds as cmds # type: ignore
import maya.mel as mel # type: ignore
import os
from ..core.base import BaseExporter
from ..types import ExportResult


class FBXExporter(BaseExporter):
    """FBX format exporter."""

    def export(self) -> ExportResult:
        result = ExportResult(format=self.settings.format, filepath=self.settings.filepath)

        # Validate
        if not self.settings.filepath:
            result.errors.append("No filepath specified.")
            result.success = False
            return result

        # Ensure FBX plugin is loaded
        if not cmds.pluginInfo('fbxmaya', q=True, loaded=True):
            try:
                cmds.loadPlugin('fbxmaya')
            except:
                result.errors.append("FBX plugin could not be loaded.")
                result.success = False
                return result

        # Prepare export options
        options = []
        if self.settings.include_animation:
            options.append("animation")
        if self.settings.include_blendshapes:
            options.append("blendShapes")
        if self.settings.include_skin:
            options.append("skinning")
        if self.settings.optimize:
            options.append("optimize")

        # Use Maya's FBXExport command
        try:
            # Set basic options
            mel.eval('FBXExport -f "{}" -s'.format(self.settings.filepath.replace("\\", "/")))
            # For full control, we'd use cmds.FBXExport...
            # We'll use the simpler file export
            cmds.select(self.settings.objects or [])
            cmds.file(self.settings.filepath, force=True, options="", type="FBX export", exportSelected=len(self.settings.objects) > 0)
            result.success = True
            result.objects_exported = len(self.settings.objects) if self.settings.objects else 0
        except Exception as e:
            result.errors.append(str(e))
            result.success = False

        return result