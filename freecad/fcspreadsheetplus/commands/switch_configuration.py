# SPDX-License-Identifier: LGPL-2.1-or-later
"""Command: switch a ConfigRef's selected configuration row."""

from __future__ import annotations

from typing import ClassVar

import FreeCAD as App
import FreeCADGui as Gui

translate = App.Qt.translate

from ..resources import Resources


class SwitchConfiguration:
    Name: ClassVar[str] = "FCSpreadSheetPlus_SwitchConfiguration"

    def GetResources(self) -> dict[str, str]:
        return {
            "Pixmap": Resources.icon("fcspreadsheetplus-config.svg"),
            "MenuText": translate("FCSpreadSheetPlus", "Switch configuration"),
            "ToolTip": translate(
                "FCSpreadSheetPlus",
                "Change the selected ConfigRef's configuration row",
            ),
        }

    def Activated(self) -> None:
        doc = App.ActiveDocument
        if doc is None:
            App.Console.PrintWarning("FCSpreadSheetPlus: no active document\n")
            return

        from ..config_ref import ConfigRef
        from ..master_sheet import MasterSheet

        ref = None
        for obj in Gui.Selection.getSelection():
            if isinstance(obj.Proxy, ConfigRef):
                ref = obj
                break
        if ref is None:
            App.Console.PrintWarning("FCSpreadSheetPlus: select a ConfigRef first\n")
            return
        if ref.Master is None:
            App.Console.PrintWarning(
                "FCSpreadSheetPlus: the ConfigRef has no linked MasterSheet\n"
            )
            return

        from ..dialogs.select_configuration import SelectConfigurationDialog

        configs = MasterSheet(ref.Master).configurations()
        dialog = SelectConfigurationDialog(configs, ref.Configuration, Gui.getMainWindow())
        if dialog.exec():
            choice = dialog.selected()
            if choice:
                ref.Configuration = choice
                doc.recompute()

    def IsActive(self) -> bool:
        return App.ActiveDocument is not None

    @classmethod
    def Install(cls) -> None:
        if App.GuiUp:
            App.Gui.addCommand(cls.Name, cls())
