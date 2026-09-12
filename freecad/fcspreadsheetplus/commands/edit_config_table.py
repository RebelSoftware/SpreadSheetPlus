# SPDX-License-Identifier: LGPL-2.1-or-later
"""Command: open the configuration table editor."""

from __future__ import annotations

from typing import ClassVar

import FreeCAD as App
import FreeCADGui as Gui

from ..i18n import translate
from ..resources import Resources


class EditConfigTable:
    Name: ClassVar[str] = "FCSpreadSheetPlus_EditConfigTable"

    def GetResources(self) -> dict[str, str]:
        return {
            "Pixmap": Resources.icon("fcspreadsheetplus-master.svg"),
            "MenuText": translate("FCSpreadSheetPlus", "Edit configuration table"),
            "ToolTip": translate(
                "FCSpreadSheetPlus",
                "Edit the selected spreadsheet's configuration table",
            ),
        }

    def Activated(self) -> None:
        from ..master_sheet import MasterSheet
        from ..dialogs.table_editor import TableEditorDialog

        master = None
        for obj in Gui.Selection.getSelection():
            if obj.TypeId == "Spreadsheet::Sheet":
                master = obj
                break
        if master is None:
            App.Console.PrintWarning(
                "FCSpreadSheetPlus: select a MasterSheet spreadsheet first\n"
            )
            return

        dialog = TableEditorDialog(MasterSheet(master), Gui.getMainWindow())
        dialog.exec()

    def IsActive(self) -> bool:
        return App.ActiveDocument is not None and bool(Gui.Selection.getSelection())

    @classmethod
    def Install(cls) -> None:
        if App.GuiUp:
            App.Gui.addCommand(cls.Name, cls())
