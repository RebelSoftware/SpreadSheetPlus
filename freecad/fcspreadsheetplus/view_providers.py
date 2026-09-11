# SPDX-License-Identifier: LGPL-2.1-or-later
"""ViewProviders for FCSpreadSheetPlus objects."""

from __future__ import annotations

from .resources import Resources


class ConfigRefViewProvider:
    """ViewProvider for the ConfigRef FeaturePython object."""

    def __init__(self, vobj) -> None:
        vobj.Proxy = self

    def getIcon(self) -> str:
        return Resources.icon("fcspreadsheetplus-config.svg")

    def attach(self, vobj) -> None:
        self.Object = vobj.Object

    def claimChildren(self):
        return []

    def onDelete(self, feature, subelements) -> bool:
        return True

    def __getstate__(self):
        return None

    def __setstate__(self, state) -> None:
        return None
