# SPDX-License-Identifier: LGPL-2.1-or-later
"""SpreadSheetPlus workbench definition."""

from __future__ import annotations

import FreeCAD as App
import FreeCADGui as Gui

from .i18n import translate
from .resources import Resources
from .commands import (
    CreateSheet,
    CreateMasterSheet,
    CreateConfigRef,
    EditConfigTable,
    SwitchConfiguration,
)


class SpreadSheetPlusWorkbench(Gui.Workbench):
    """A spreadsheet workbench similar to FreeCAD's default Spreadsheet workbench."""

    MenuText: str = translate("SpreadSheetPlus", "SpreadSheet Plus")
    ToolTip: str = translate(
        "SpreadSheetPlus",
        "A spreadsheet workbench similar to the default one",
    )
    Icon: str = Resources.icon("spreadsheetplus-wb.svg")

    def Initialize(self) -> None:
        App.Console.PrintMessage("SpreadSheetPlus workbench initialized\n")
        commands = [
            CreateMasterSheet.Name,
            CreateConfigRef.Name,
            EditConfigTable.Name,
            SwitchConfiguration.Name,
            CreateSheet.Name,
        ]
        self.appendToolbar(translate("SpreadSheetPlus", "SpreadSheet Plus"), commands)
        self.appendMenu(translate("SpreadSheetPlus", "SpreadSheet Plus"), commands)

    def Activated(self) -> None:
        pass

    def Deactivated(self) -> None:
        pass

    def ContextMenu(self, recipient: str) -> None:
        self.appendContextMenu("", [EditConfigTable.Name, CreateConfigRef.Name])

    @classmethod
    def Install(cls) -> None:
        Gui.addWorkbench(cls)
