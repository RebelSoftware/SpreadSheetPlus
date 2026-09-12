# SPDX-License-Identifier: LGPL-2.1-or-later
"""Command: create a new spreadsheet sheet."""

from __future__ import annotations

from typing import ClassVar

import FreeCAD as App

from ..i18n import translate
from ..resources import Resources


class CreateSheet:
    """Create a new Spreadsheet::Sheet in the active document."""

    Name: ClassVar[str] = "FCSpreadSheetPlus_CreateSheet"

    def GetResources(self) -> dict[str, str]:
        return {
            "Pixmap": Resources.icon("fcspreadsheetplus-create.svg"),
            "MenuText": translate("FCSpreadSheetPlus", "Create spreadsheet"),
            "ToolTip": translate(
                "FCSpreadSheetPlus",
                "Create a new spreadsheet sheet",
            ),
        }

    def Activated(self) -> None:
        doc = App.ActiveDocument
        if doc is None:
            App.Console.PrintWarning(
                "FCSpreadSheetPlus: no active document, cannot create a spreadsheet\n"
            )
            return
        from ..sheet import Sheet

        Sheet.create(doc=doc)
        doc.recompute()

    def IsActive(self) -> bool:
        return App.ActiveDocument is not None

    @classmethod
    def Install(cls) -> None:
        if App.GuiUp:
            App.Gui.addCommand(cls.Name, cls())
