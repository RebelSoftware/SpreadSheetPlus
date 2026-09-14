# SPDX-License-Identifier: LGPL-2.1-or-later
"""Command: attach a ConfigRef to the selected MasterSheet."""

from __future__ import annotations

from typing import ClassVar

import FreeCAD as App
import FreeCADGui as Gui

from ..i18n import translate
from ..resources import Resources

#: FreeCAD's keys for the *active container* (see Gui/ActiveObjectList.h).
#: Double-clicking a container makes it active and new objects go into it.
ACTIVE_CONTAINER_KEYS = ("pdbody", "part")


def active_container(doc=None):
    """Return the container new objects should go into, or None.

    FreeCAD's convention: double-clicking a Part container or a PartDesign Body
    makes it the active container (bold in the tree) and newly created objects
    are added to it. This looks up the same active objects the core commands do
    and prefers a Body over a Part, as PartDesign does.
    """
    if not App.GuiUp:
        return None
    gui_doc = getattr(Gui, "ActiveDocument", None)
    view = getattr(gui_doc, "ActiveView", None)
    if view is None:
        return None
    for key in ACTIVE_CONTAINER_KEYS:
        try:
            container = view.getActiveObject(key)
        except Exception:
            continue
        if container is None:
            continue
        if doc is not None and container.Document is not doc:
            continue  # never move an object across documents
        return container
    return None


def add_to_active_container(obj, doc=None):
    """Add *obj* to the active container; returns the container or None."""
    container = active_container(doc)
    if container is None:
        return None
    try:
        container.addObject(obj)
    except Exception as exc:
        App.Console.PrintWarning(
            f"SpreadSheetPlus: could not add {obj.Label} to "
            f"{container.Label}: {exc}\n"
        )
        return None
    return container


class CreateConfigRef:
    Name: ClassVar[str] = "SpreadSheetPlus_CreateConfigRef"

    def GetResources(self) -> dict[str, str]:
        return {
            "Pixmap": Resources.icon("spreadsheetplus-config.svg"),
            "MenuText": translate("SpreadSheetPlus", "Attach configuration"),
            "ToolTip": translate(
                "SpreadSheetPlus",
                "Link a ConfigRef to the selected spreadsheet",
            ),
        }

    def Activated(self) -> None:
        doc = App.ActiveDocument
        if doc is None:
            App.Console.PrintWarning("SpreadSheetPlus: no active document\n")
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
                "SpreadSheetPlus: select a MasterSheet spreadsheet first\n"
            )
            return

        configs = MasterSheet(master).configurations()
        if not configs:
            App.Console.PrintWarning(
                "SpreadSheetPlus: the spreadsheet has no configurations\n"
            )
            return

        ref = create_config_ref(doc, master, configs[0])
        # FreeCAD's convention: the new object goes into the active container
        # (an active PartDesign Body or Part container), so a reference created
        # while a body is active belongs to that body straight away.
        container = add_to_active_container(ref, doc)
        doc.recompute()
        if container is not None:
            App.Console.PrintMessage(
                f"Created ConfigRef: {ref.Label} in {container.Label}\n"
            )
        else:
            App.Console.PrintMessage(f"Created ConfigRef: {ref.Label}\n")

    def IsActive(self) -> bool:
        return App.ActiveDocument is not None

    @classmethod
    def Install(cls) -> None:
        if App.GuiUp:
            App.Gui.addCommand(cls.Name, cls())
