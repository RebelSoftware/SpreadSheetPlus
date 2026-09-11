# SPDX-License-Identifier: LGPL-2.1-or-later
"""Command: create a MasterSheet (document-level configuration table)."""

from __future__ import annotations

from typing import ClassVar

import FreeCAD as App

translate = App.Qt.translate

from ..resources import Resources


class CreateMasterSheet:
    Name: ClassVar[str] = "FCSpreadSheetPlus_CreateMasterSheet"

    def GetResources(self) -> dict[str, str]:
        return {
            "Pixmap": Resources.icon("fcspreadsheetplus-master.svg"),
            "MenuText": translate("FCSpreadSheetPlus", "Create MasterSheet"),
            "ToolTip": translate(
                "FCSpreadSheetPlus",
                "Create a document-level configuration table",
            ),
        }

    def Activated(self) -> None:
        doc = App.ActiveDocument
        if doc is None:
            App.Console.PrintWarning("FCSpreadSheetPlus: no active document\n")
            return
        from ..master_sheet import MasterSheet

        MasterSheet.create(doc=doc)
        doc.recompute()

    def IsActive(self) -> bool:
        return App.ActiveDocument is not None

    @classmethod
    def Install(cls) -> None:
        if App.GuiUp:
            App.Gui.addCommand(cls.Name, cls())
