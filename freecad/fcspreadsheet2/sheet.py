# SPDX-License-Identifier: LGPL-2.1-or-later
"""Data model: a thin wrapper around FreeCAD's built-in Spreadsheet::Sheet.

Reusing the built-in Spreadsheet object gives us the full calculation engine
(expressions, aliases, units) for free, while this wrapper keeps a clean,
headless-safe API for the workbench's commands and scripts.
"""

from __future__ import annotations

import FreeCAD as App

DEFAULT_NAME = "Spreadsheet"


class Sheet:
    """Convenience wrapper around a ``Spreadsheet::Sheet`` document object."""

    def __init__(self, obj: App.DocumentObject) -> None:
        self.obj = obj

    # -- creation ---------------------------------------------------------
    @classmethod
    def create(cls, doc=None, name: str | None = None) -> "Sheet":
        """Create a new Spreadsheet::Sheet in *doc* (default: active document)."""
        doc = doc or App.ActiveDocument
        if doc is None:
            raise ValueError("FCSpreadSheet2: no active document")
        obj = doc.addObject("Spreadsheet::Sheet", name or DEFAULT_NAME)
        return cls(obj)

    # -- cell access ------------------------------------------------------
    def set(self, address: str, value) -> None:
        """Set the raw content of a cell (e.g. ``set("A1", 42)``)."""
        self.obj.set(address, str(value))

    def get(self, address: str) -> str:
        """Return the raw content of a cell as a string.

        Uses ``getContents`` (raw content) rather than ``get`` (evaluated
        content) so that it works for any address regardless of whether the
        cell is exposed as a property.
        """
        return self.obj.getContents(address)

    def get_contents(self) -> dict:
        """Return all non-empty cells as ``{address: content}``."""
        return {
            address: self.obj.getContents(address)
            for address in self.obj.getNonEmptyCells()
        }

    def clear(self, address: str) -> None:
        """Clear the content of a single cell."""
        self.obj.clear(address)

    def clear_all(self) -> None:
        """Clear all cells in the spreadsheet."""
        self.obj.clearAll()

    # -- aliases ----------------------------------------------------------
    def set_alias(self, address: str, alias: str) -> None:
        """Bind an alias name to a cell (used by other objects/expressions)."""
        self.obj.setAlias(address, alias)

    def get_alias(self, address: str) -> str:
        """Return the alias bound to a cell (empty string if none)."""
        return self.obj.getAlias(address)

    def get_cell_from_alias(self, alias: str) -> str:
        """Return the cell address bound to an alias (empty string if none)."""
        return self.obj.getCellFromAlias(alias)
