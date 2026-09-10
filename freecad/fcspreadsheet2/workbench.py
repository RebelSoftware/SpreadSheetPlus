# SPDX-License-Identifier: LGPL-2.1-or-later
"""FCSpreadSheet2 workbench definition."""

from __future__ import annotations

import FreeCAD as App
import FreeCADGui as Gui

translate = App.Qt.translate

from .resources import Resources
from .commands import CreateSheet


class FCSpreadSheet2Workbench(Gui.Workbench):
    """A spreadsheet workbench similar to FreeCAD's default Spreadsheet workbench."""

    MenuText: str = translate("FCSpreadSheet2", "FC SpreadSheet 2")
    ToolTip: str = translate(
        "FCSpreadSheet2",
        "A spreadsheet workbench similar to the default one",
    )
    Icon: str = Resources.icon("fcspreadsheet2-wb.svg")

    def Initialize(self) -> None:
        App.Console.PrintMessage("FCSpreadSheet2 workbench initialized\n")
        commands = [CreateSheet.Name]
        self.appendToolbar("FC SpreadSheet 2", commands)
        self.appendMenu("FC SpreadSheet 2", commands)

    def Activated(self) -> None:
        pass

    def Deactivated(self) -> None:
        pass

    def ContextMenu(self, recipient: str) -> None:
        self.appendContextMenu("", [CreateSheet.Name])

    @classmethod
    def Install(cls) -> None:
        Gui.addWorkbench(cls)
