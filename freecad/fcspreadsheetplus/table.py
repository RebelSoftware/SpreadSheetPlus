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

from functools import lru_cache

from FreeCAD import Units

CONFIG_COLUMN = 0        # column A
FIRST_PARAM_COLUMN = 1   # column B
TITLE_ROW = 0            # spreadsheet row 1
HEADER_ROW = 1           # spreadsheet row 2
DATA_START_ROW = 2       # spreadsheet row 3

# Data-cell kinds returned by parse_value().
EMPTY = "empty"
STRING = "string"
NUMBER = "number"
QUANTITY = "quantity"
EXPRESSION = "expression"

_UNITLESS = Units.Unit()


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


def parse_value(raw: str):
    """Parse a raw data-cell string into ``(kind, value)``.

    FreeCAD's ``Sheet.getContents`` returns ``"80"`` for a number, ``"'text"``
    for a string literal, ``"=80 mm"`` for a quantity literal (stored as an
    expression), and ``"=A1*2"`` / ``"=pi"`` for formulas and constants.

    ``kind`` is one of ``EMPTY``, ``STRING``, ``NUMBER``, ``QUANTITY``,
    ``EXPRESSION``. ``value`` is the typed value (``int`` / ``float`` / ``str``
    / ``Units.Quantity``), or ``None`` for empty cells.
    """
    if raw == "":
        return (EMPTY, None)
    if raw.startswith("'"):
        return (STRING, raw[1:])
    if raw.startswith("="):
        text = raw[1:]
        # Quantity literals start with a digit/sign/decimal point; formulas and
        # constants ("=A1*2", "=pi") do not. The latter cannot be evaluated
        # here, so they are reported as expressions.
        if not text or text[0] not in "0123456789+-.":
            return (EXPRESSION, text)
        return _parse_quantity(text, EXPRESSION)
    return _parse_quantity(raw, STRING)


def _parse_quantity(text: str, fallback_kind: str):
    """Parse ``text`` as a number or quantity; fall back to *fallback_kind*."""
    try:
        quantity = Units.Quantity(text)
    except (ValueError, TypeError):
        return (fallback_kind, text)
    if quantity.Unit == _UNITLESS:
        value = quantity.Value
        return (NUMBER, int(value) if float(value).is_integer() else value)
    return (QUANTITY, quantity)


class TableSnapshot:
    """Immutable parsed view of a configuration table.

    Produced and cached by ``Table.snapshot()``. The result is shared between
    callers, so it must not be mutated.
    """

    __slots__ = ("params", "configs", "_cells")

    def __init__(self, params, configs, cells) -> None:
        self.params = tuple(params)
        self.configs = tuple(configs)
        self._cells = cells  # {(config, param): (kind, value)}

    def cell(self, config: str, param: str):
        """Parsed ``(kind, value)`` for one data cell."""
        return self._cells[(config, param)]

    def column(self, param: str) -> list:
        """Parsed ``(kind, value)`` cells for every configuration of a parameter."""
        return [self._cells[(config, param)] for config in self.configs]


@lru_cache(maxsize=64)
def _parse_snapshot(key):
    """Parse raw cell contents into a TableSnapshot (memoized by content)."""
    param_names, config_names, raw = key
    cells = {}
    idx = 0
    for config in config_names:
        for param in param_names:
            cells[(config, param)] = parse_value(raw[idx])
            idx += 1
    return TableSnapshot(param_names, config_names, cells)


class Table:
    """Read/write access to a configuration table stored on a Spreadsheet::Sheet."""

    def __init__(self, sheet) -> None:
        self.sheet = sheet

    # -- raw cell access -------------------------------------------------
    def _raw(self, col: int, row: int) -> str:
        return self.sheet.getContents(cell_address(col, row))

    def _cell(self, col: int, row: int) -> str:
        raw = self._raw(col, row)
        # FreeCAD marks string cells with a leading apostrophe when read back
        # via getContents (numbers are returned bare). Strip it for clean text.
        return raw[1:] if raw.startswith("'") else raw

    def _set_cell(self, col: int, row: int, value) -> None:
        self.sheet.set(cell_address(col, row), str(value))
        # Recompute so the sheet creates per-cell display properties. Until
        # then FreeCAD's view shows the raw content (with the leading
        # apostrophe marker on strings).
        self.sheet.recompute()

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

    # -- snapshot --------------------------------------------------------
    def _schema_maps(self):
        """``(name, column)`` pairs for parameters and ``(name, row)`` for configs."""
        params = []
        col = FIRST_PARAM_COLUMN
        while self._cell(col, HEADER_ROW):
            params.append((self._cell(col, HEADER_ROW), col))
            col += 1
        configs = []
        row = DATA_START_ROW
        while self._cell(CONFIG_COLUMN, row):
            configs.append((self._cell(CONFIG_COLUMN, row), row))
            row += 1
        return params, configs

    def snapshot(self) -> TableSnapshot:
        """Parse the whole table once, memoized by raw cell content.

        The parsed result depends only on the raw cell contents, so equal
        content — e.g. the same master read by several ConfigRefs, or a
        recompute where nothing changed — is parsed once and reused.
        """
        params, configs = self._schema_maps()
        param_names = tuple(name for name, _ in params)
        config_names = tuple(name for name, _ in configs)
        raw = tuple(
            self._raw(col, row)
            for _, row in configs
            for _, col in params
        )
        return _parse_snapshot((param_names, config_names, raw))

    def get_data(self, config: str, param: str):
        """Parsed ``(kind, value)`` for one data cell (see parse_value)."""
        raw = self._raw(self._param_col(param), self._config_row(config))
        return parse_value(raw)

    def get_column(self, param: str) -> list:
        """Parsed ``(kind, value)`` cells for every configuration of a parameter."""
        col = self._param_col(param)
        cells = []
        row = DATA_START_ROW
        while self._cell(CONFIG_COLUMN, row):
            cells.append(parse_value(self._raw(col, row)))
            row += 1
        return cells

    def get_value(self, config: str, param: str) -> str:
        """Display string of a data cell (numbers/quantities as plain text)."""
        kind, value = self.get_data(config, param)
        if kind == EMPTY:
            return ""
        if kind == STRING:
            return value
        if kind == NUMBER:
            return str(value)
        if kind == QUANTITY:
            return value.UserString
        return "=" + value  # EXPRESSION: keep the leading '=' marker

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
        self.sheet.recompute()

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
        self.sheet.recompute()

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
