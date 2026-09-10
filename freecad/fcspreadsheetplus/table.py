# SPDX-License-Identifier: LGPL-2.1-or-later
"""Configuration table model for FCSpreadSheetPlus.

One spreadsheet holds exactly one configuration table, so no marker is needed.
Layout (see PLAN.md)::

    Row 1  : free text (title / notes); A1 is the optional title
    Row 2  : parameter names in columns B, C, ...  (A2 is a cosmetic header)
    Col A  : configuration names in rows 3, 4, ...
    B3..   : values, one per (configuration, parameter)

Rows and columns are kept contiguous: adding appends, removing deletes the row
or column, so the "read until empty" scan stays correct.
"""

from __future__ import annotations

CONFIG_COLUMN = 0        # column A
FIRST_PARAM_COLUMN = 1   # column B
TITLE_ROW = 0            # spreadsheet row 1
HEADER_ROW = 1           # spreadsheet row 2
DATA_START_ROW = 2       # spreadsheet row 3


def column_name(index: int) -> str:
    """Spreadsheet column label for a 0-based index (0 -> 'A', 26 -> 'AA')."""
    label = ""
    n = index + 1
    while n:
        n, rem = divmod(n - 1, 26)
        label = chr(ord("A") + rem) + label
    return label


def cell_address(col: int, row: int) -> str:
    """A1-style address for 0-based column and row indices."""
    return f"{column_name(col)}{row + 1}"


class Table:
    """Read/write access to a configuration table stored on a Spreadsheet::Sheet."""

    def __init__(self, sheet) -> None:
        self.sheet = sheet

    # -- raw cell access -------------------------------------------------
    def _cell(self, col: int, row: int) -> str:
        raw = self.sheet.getContents(cell_address(col, row))
        # FreeCAD marks string cells with a leading apostrophe when read back
        # via getContents (numbers are returned bare). Strip it for clean text.
        return raw[1:] if raw.startswith("'") else raw

    def _set_cell(self, col: int, row: int, value) -> None:
        self.sheet.set(cell_address(col, row), str(value))

    # -- schema ----------------------------------------------------------
    @property
    def title(self) -> str:
        """Free-text title stored in A1."""
        return self._cell(CONFIG_COLUMN, TITLE_ROW)

    def set_title(self, text: str) -> None:
        self._set_cell(CONFIG_COLUMN, TITLE_ROW, text)

    def parameters(self) -> list[str]:
        """Parameter (column) names, read rightwards from B2."""
        names = []
        col = FIRST_PARAM_COLUMN
        while self._cell(col, HEADER_ROW):
            names.append(self._cell(col, HEADER_ROW))
            col += 1
        return names

    def configurations(self) -> list[str]:
        """Configuration (row) names, read downwards from A3."""
        names = []
        row = DATA_START_ROW
        while self._cell(CONFIG_COLUMN, row):
            names.append(self._cell(CONFIG_COLUMN, row))
            row += 1
        return names

    # -- lookups ---------------------------------------------------------
    def _config_row(self, config: str) -> int:
        row = DATA_START_ROW
        while True:
            name = self._cell(CONFIG_COLUMN, row)
            if not name:
                raise KeyError(f"unknown configuration: {config!r}")
            if name == config:
                return row
            row += 1

    def _param_col(self, param: str) -> int:
        col = FIRST_PARAM_COLUMN
        while True:
            name = self._cell(col, HEADER_ROW)
            if not name:
                raise KeyError(f"unknown parameter: {param!r}")
            if name == param:
                return col
            col += 1

    def get_value(self, config: str, param: str) -> str:
        """Raw (string) value of a cell."""
        return self._cell(self._param_col(param), self._config_row(config))

    def set_value(self, config: str, param: str, value) -> None:
        self._set_cell(self._param_col(param), self._config_row(config), value)

    def get_row(self, config: str) -> dict[str, str]:
        """All ``{parameter: value}`` pairs for one configuration."""
        row = self._config_row(config)
        return {p: self._cell(self._param_col(p), row) for p in self.parameters()}

    def get_all(self) -> dict[str, dict[str, str]]:
        """The whole table as ``{configuration: {parameter: value}}``."""
        return {c: self.get_row(c) for c in self.configurations()}

    # -- editing ---------------------------------------------------------
    def add_configuration(self, name: str) -> None:
        if not name:
            raise ValueError("configuration name must not be empty")
        if name in self.configurations():
            raise ValueError(f"configuration already exists: {name!r}")
        row = DATA_START_ROW
        while self._cell(CONFIG_COLUMN, row):
            row += 1
        self._set_cell(CONFIG_COLUMN, row, name)

    def remove_configuration(self, name: str) -> None:
        row = self._config_row(name)
        self.sheet.removeRows(str(row + 1), 1)

    def add_parameter(self, name: str) -> None:
        if not name:
            raise ValueError("parameter name must not be empty")
        if name in self.parameters():
            raise ValueError(f"parameter already exists: {name!r}")
        col = FIRST_PARAM_COLUMN
        while self._cell(col, HEADER_ROW):
            col += 1
        self._set_cell(col, HEADER_ROW, name)

    def remove_parameter(self, name: str) -> None:
        col = self._param_col(name)
        self.sheet.removeColumns(column_name(col), 1)

    # -- validation ------------------------------------------------------
    def validate(self) -> list[str]:
        """Return a list of human-readable problems (empty means OK)."""
        problems = []
        params = self.parameters()
        configs = self.configurations()
        if len(params) != len(set(params)):
            problems.append("duplicate parameter names")
        if len(configs) != len(set(configs)):
            problems.append("duplicate configuration names")
        for param in params:
            if not param.isidentifier():
                problems.append(f"parameter name is not a valid identifier: {param!r}")
        return problems
