# SPDX-License-Identifier: LGPL-2.1-or-later
"""FCSpreadSheetPlus workbench definition."""

from __future__ import annotations

import FreeCAD as App
import FreeCADGui as Gui

translate = App.Qt.translate

from .resources import Resources
from .commands import (
    CreateSheet,
    CreateMasterSheet,
    CreateConfigRef,
    EditConfigTable,
    SwitchConfiguration,
)


class FCSpreadSheetPlusWorkbench(Gui.Workbench):
    """A spreadsheet workbench similar to FreeCAD's default Spreadsheet workbench."""

    MenuText: str = translate("FCSpreadSheetPlus", "FC SpreadSheet Plus")
    ToolTip: str = translate(
        "FCSpreadSheetPlus",
        "A spreadsheet workbench similar to the default one",
    )
    Icon: str = Resources.icon("fcspreadsheetplus-wb.svg")

    def Initialize(self) -> None:
        App.Console.PrintMessage("FCSpreadSheetPlus workbench initialized\n")
        commands = [
            CreateMasterSheet.Name,
            CreateConfigRef.Name,
            EditConfigTable.Name,
            SwitchConfiguration.Name,
            CreateSheet.Name,
        ]
        self.appendToolbar("FC SpreadSheet Plus", commands)
        self.appendMenu("FC SpreadSheet Plus", commands)

    def Activated(self) -> None:
        pass

    def Deactivated(self) -> None:
        pass

    def ContextMenu(self, recipient: str) -> None:
        self.appendContextMenu("", [EditConfigTable.Name, CreateConfigRef.Name])

    @classmethod
    def Install(cls) -> None:
        Gui.addWorkbench(cls)
