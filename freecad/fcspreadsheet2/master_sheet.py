# SPDX-License-Identifier: LGPL-2.1-or-later
"""MasterSheet: a document-level configuration table.

A MasterSheet is a plain `Spreadsheet::Sheet` placed at the document root. This
module provides a thin wrapper exposing the configuration-table API (built on
`table.Table`). The sheet itself is the single source of truth.
"""

from __future__ import annotations

import FreeCAD as App

from .table import Table


class MasterSheet:
    """Wrapper around a Spreadsheet::Sheet holding one configuration table."""

    def __init__(self, sheet) -> None:
        self.sheet = sheet
        self.table = Table(sheet)

    @classmethod
    def create(cls, doc=None, name: str = "MasterSheet", title: str = "") -> "MasterSheet":
        doc = doc or App.ActiveDocument
        if doc is None:
            raise ValueError("FCSpreadSheet2: no active document")
        sheet = doc.addObject("Spreadsheet::Sheet", name)
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
