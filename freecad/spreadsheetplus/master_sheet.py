# SPDX-License-Identifier: LGPL-2.1-or-later
"""MasterSheet: a document-level configuration table.

A MasterSheet is a plain `Spreadsheet::Sheet` placed at the document root. This
module provides a thin wrapper exposing the configuration-table API (built on
`table.Table`). The sheet itself is the single source of truth.

A master is *shared*, never copied: `keep_shared()` marks the sheet so FreeCAD
leaves it out of the copy it makes for a copy-on-change part variant.
"""

from __future__ import annotations

import FreeCAD as App

from .table import Table

#: FreeCAD's copy-on-change control map. FreeCAD's `LinkBaseExtension`
#: (`getOnChangeCopyObjects()`) reads this `App::PropertyMap` off every object it
#: is about to copy and drops those whose entry says ``COPY_CONTROL_EXCLUDE`` -
#: the storage behind `setOnChangeCopyObject(obj, Exclude | ApplyAll)`, which is
#: C++ only. The map itself is a plain dynamic property, so Python can write it.
COPY_CONTROL_PROPERTY = "_CopyOnChangeControl"

#: The property group that map is shown in (it is hidden, so this is cosmetic).
COPY_CONTROL_GROUP = "MasterSheet"

#: The map value that keeps an object out of a copy-on-change copy.
COPY_CONTROL_EXCLUDE = "-"


def keep_shared(sheet) -> bool:
    """Stop FreeCAD copying *sheet* into a copy-on-change variant.

    A variant of a part is a copy of that part *and of everything it depends on*,
    and a `ConfigRef` depends on its master sheet - so without this marker FreeCAD
    copies the table along, re-points the copy's `Master` at that copy, and the
    variant quietly reads a snapshot: later edits at the master never reach it.
    That is exactly the coupling this workbench exists to remove, so every master
    sheet is marked as shared.

    Returns True when the sheet carries the marker (also when it already did, so
    this is safe to call on every recompute, and migrates sheets written before
    the marker existed). It never raises: a sheet that cannot be marked still
    works, it is just copied along with the part.
    """
    try:
        if not hasattr(sheet, COPY_CONTROL_PROPERTY):
            sheet.addProperty(
                "App::PropertyMap",
                COPY_CONTROL_PROPERTY,
                COPY_CONTROL_GROUP,
                "Keep this master sheet out of copy-on-change copies",
                hidden=True,
            )
        control = getattr(sheet, COPY_CONTROL_PROPERTY)
        if control.get("*") == COPY_CONTROL_EXCLUDE:
            return True
        # Assigning a PropertyMap replaces the whole map, so keep the keys that
        # are already there (FreeCAD writes per-link keys of its own).
        control = dict(control)
        control["*"] = COPY_CONTROL_EXCLUDE
        setattr(sheet, COPY_CONTROL_PROPERTY, control)
        return True
    except Exception as exc:  # noqa: BLE001 - never break a part over this
        App.Console.PrintWarning(
            f"SpreadSheetPlus: could not mark "
            f"{getattr(sheet, 'Label', sheet)!r} as a shared master sheet: {exc}\n"
        )
        return False


class MasterSheet:
    """Wrapper around a Spreadsheet::Sheet holding one configuration table."""

    def __init__(self, sheet) -> None:
        self.sheet = sheet
        self.table = Table(sheet)

    @classmethod
    def create(cls, doc=None, name: str = "MasterSheet", title: str = "") -> "MasterSheet":
        doc = doc or App.ActiveDocument
        if doc is None:
            raise ValueError("SpreadSheetPlus: no active document")
        sheet = doc.addObject("Spreadsheet::Sheet", name)
        keep_shared(sheet)
        wrapper = cls(sheet)
        if title:
            wrapper.table.set_title(title)
        return wrapper

    # -- delegated table API --------------------------------------------
    @property
    def title(self) -> str:
        return self.table.title

    def set_title(self, text: str) -> None:
        self.table.set_title(text)

    def parameters(self) -> list[str]:
        return self.table.parameters()

    def configurations(self) -> list[str]:
        return self.table.configurations()

    def get_value(self, config: str, param: str) -> str:
        return self.table.get_value(config, param)

    def set_value(self, config: str, param: str, value) -> None:
        self.table.set_value(config, param, value)

    def get_row(self, config: str) -> dict[str, str]:
        return self.table.get_row(config)

    def add_configuration(self, name: str) -> None:
        self.table.add_configuration(name)

    def remove_configuration(self, name: str) -> None:
        self.table.remove_configuration(name)

    def add_parameter(self, name: str) -> None:
        self.table.add_parameter(name)

    def remove_parameter(self, name: str) -> None:
        self.table.remove_parameter(name)

    def validate(self) -> list[str]:
        return self.table.validate()
