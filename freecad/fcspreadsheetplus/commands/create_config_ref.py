# SPDX-License-Identifier: LGPL-2.1-or-later
"""Command: attach a ConfigRef to the selected MasterSheet."""

from __future__ import annotations

from typing import ClassVar

import FreeCAD as App
import FreeCADGui as Gui

from ..i18n import translate
from ..resources import Resources


class CreateConfigRef:
    Name: ClassVar[str] = "FCSpreadSheetPlus_CreateConfigRef"

    def GetResources(self) -> dict[str, str]:
        return {
            "Pixmap": Resources.icon("fcspreadsheetplus-config.svg"),
            "MenuText": translate("FCSpreadSheetPlus", "Attach configuration"),
            "ToolTip": translate(
                "FCSpreadSheetPlus",
                "Link a ConfigRef to the selected spreadsheet",
            ),
        }

    def Activated(self) -> None:
        doc = App.ActiveDocument
        if doc is None:
            App.Console.PrintWarning("FCSpreadSheetPlus: no active document\n")
            return

        from ..master_sheet import MasterSheet
        from ..config_ref import create as create_config_ref

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

        configs = MasterSheet(master).configurations()
        if not configs:
            App.Console.PrintWarning(
                "FCSpreadSheetPlus: the spreadsheet has no configurations\n"
            )
            return

        ref = create_config_ref(doc, master, configs[0])
        doc.recompute()
        App.Console.PrintMessage(f"Created ConfigRef: {ref.Label}\n")

    def IsActive(self) -> bool:
        return App.ActiveDocument is not None

    @classmethod
    def Install(cls) -> None:
        if App.GuiUp:
            App.Gui.addCommand(cls.Name, cls())
