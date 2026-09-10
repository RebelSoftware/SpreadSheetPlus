# API reference

## `freecad.fcspreadsheet2.table`

One spreadsheet = one configuration table. All cell access uses the fixed layout
described in [usage.md](usage.md).

### `column_name(index)` → `str`

Spreadsheet column label for a 0-based index (`0` → `"A"`, `26` → `"AA"`).

### `cell_address(col, row)` → `str`

A1-style address for 0-based indices, e.g. `cell_address(1, 2)` → `"B3"`.

### `class Table(sheet)`

Wraps a `Spreadsheet::Sheet` with named-table access.

| Member | Description |
| :--- | :--- |
| `title` | property — free-text title stored in `A1` |
| `set_title(text)` | write the title |
| `parameters()` → `list[str]` | parameter names from row 2 |
| `configurations()` → `list[str]` | configuration names from column A |
| `get_value(config, param)` → `str` | raw cell content |
| `set_value(config, param, value)` | write a cell (`str(value)`) |
| `get_row(config)` → `dict[str, str]` | all parameters for one configuration |
| `get_all()` → `dict[str, dict[str, str]]` | the whole table |
| `add_configuration(name)` | append a configuration row |
| `remove_configuration(name)` | delete a configuration row (shifts up) |
| `add_parameter(name)` | append a parameter column |
| `remove_parameter(name)` | delete a parameter column (shifts left) |
| `validate()` → `list[str]` | human-readable problems (empty = OK) |

## `freecad.fcspreadsheet2.master_sheet`

### `class MasterSheet(sheet)`

High-level wrapper around a spreadsheet holding a configuration table.

- `sheet` — the underlying `Spreadsheet::Sheet`.
- `table` — the underlying `Table`.
- `create(doc=None, name="MasterSheet", title="")` → `MasterSheet` — create a
  sheet at document level.

Delegates to `table`: `title`, `set_title`, `parameters`, `configurations`,
`get_value`, `set_value`, `get_row`, `add_configuration`, `remove_configuration`,
`add_parameter`, `remove_parameter`, `validate`.

## `freecad.fcspreadsheet2.config_ref`

### `create(doc, master, configuration, name="ConfigRef")` → object

Create a `ConfigRef` (`App::FeaturePython`) linked to `master` (a
`Spreadsheet::Sheet`) and selecting `configuration` (a row name).

### `link_master_by_path(config_ref, file_path, object_name="MasterSheet")`

Point an existing ConfigRef's `Master` at a sheet in an external document. Opens
`file_path` if it is not already open. The owner document must already be saved.

### `class ConfigRef` — FeaturePython proxy

Object properties:

- `Master` — `App::PropertyXLink` to the master spreadsheet (same or another document).
- `Configuration` — `App::PropertyString` — the selected row name.
- `ManagedParameters` — `App::PropertyStringList` — parameter names exposed as
  properties (managed automatically).
- One dynamic **read-only** property per parameter (e.g. `Length`), typed by
  inference.

## `freecad.fcspreadsheet2.sheet`

### `class Sheet(obj)`

Low-level wrapper around a `Spreadsheet::Sheet` (used internally by `Table`).

- `create(doc=None, name="Spreadsheet")` → `Sheet`
- `set(address, value)`, `get(address)`, `get_contents()`, `clear(address)`, `clear_all()`
- `set_alias(address, alias)`, `get_alias(address)`, `get_cell_from_alias(alias)`
