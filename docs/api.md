# API reference

## `freecad.spreadsheetplus.table`

One spreadsheet = one configuration table. All cell access uses the fixed layout
described in [usage.md](usage.md).

### `column_name(index)` → `str`

Spreadsheet column label for a 0-based index (`0` → `"A"`, `26` → `"AA"`).

### `cell_address(col, row)` → `str`

A1-style address for 0-based indices, e.g. `cell_address(1, 2)` → `"B3"`.

### `parse_value(raw)` → `(kind, value)`

Parse a raw data-cell string (as returned by `Sheet.getContents`) into a typed
value. `kind` is one of `EMPTY`, `STRING`, `NUMBER`, `QUANTITY`, `EXPRESSION`;
`value` is an `int` / `float` / `str` / `Units.Quantity` (or `None`).

### `class Table(sheet)`

Wraps a `Spreadsheet::Sheet` with named-table access.

| Member | Description |
| :--- | :--- |
| `title` | property — free-text title stored in `A1` |
| `set_title(text)` | write the title |
| `parameters()` → `list[str]` | parameter names from row 2 |
| `configurations()` → `list[str]` | configuration names from column A |
| `get_value(config, param)` → `str` | display string of a cell (numbers/quantities as text) |
| `get_data(config, param)` → `(kind, value)` | parsed typed value of a cell |
| `get_column(param)` → `list[(kind, value)]` | parsed values for every configuration |
| `snapshot()` → `TableSnapshot` | parsed whole table, memoized by cell content |
| `set_value(config, param, value)` | write a cell (`str(value)`) |
| `get_row(config)` → `dict[str, str]` | all parameters for one configuration |
| `get_all()` → `dict[str, dict[str, str]]` | the whole table |
| `add_configuration(name)` | append a configuration row |
| `remove_configuration(name)` | delete a configuration row (shifts up) |
| `add_parameter(name)` | append a parameter column |
| `remove_parameter(name)` | delete a parameter column (shifts left) |
| `validate()` → `list[str]` | human-readable problems (empty = OK) |

### `class TableSnapshot`

Immutable parsed view of a table, produced by `Table.snapshot()`. The result is
memoized by raw cell content, so repeated reads of unchanged content reuse the
same object (shared across ConfigRefs and recomputes).

- `params` — tuple of parameter names.
- `configs` — tuple of configuration names.
- `cell(config, param)` → `(kind, value)` — parsed value of one cell (config name
  matched case-insensitively).
- `column(param)` → `list[(kind, value)]` — parsed values for every configuration.
- `resolve_config(name)` → `str | None` — canonical stored-case name for `name`
  (case-insensitive), or `None` if there is no such row.
- `problems()` → `list[str]` — structural problems found in the parse (duplicate
  parameter names, duplicate configuration names, parameters that are not valid
  identifiers; empty = OK). `Table.validate()` and `ConfigRef` derive their
  status from this, so validation costs no extra reads of the spreadsheet.

## `freecad.spreadsheetplus.master_sheet`

### `class MasterSheet(sheet)`

High-level wrapper around a spreadsheet holding a configuration table.

- `sheet` — the underlying `Spreadsheet::Sheet`.
- `table` — the underlying `Table`.
- `create(doc=None, name="MasterSheet", title="")` → `MasterSheet` — create a
  sheet at document level.

Delegates to `table`: `title`, `set_title`, `parameters`, `configurations`,
`get_value`, `set_value`, `get_row`, `add_configuration`, `remove_configuration`,
`add_parameter`, `remove_parameter`, `validate`.

## `freecad.spreadsheetplus.config_ref`

### `create(doc, master, configuration, name="ConfigRef")` → object

Create a `ConfigRef` linked to `master` (a `Spreadsheet::Sheet`) and selecting
`configuration` (a row name).

The object is created with the type `CONTAINER_OBJECT_TYPE`
(`Part::Part2DObjectPython`) so it can be placed inside any container FreeCAD
offers, including a `PartDesign::Body` (see
[Putting a ConfigRef inside a part](usage.md#putting-a-configref-inside-a-part-container)).
If the Part module is unavailable, `create()` falls back to
`LEGACY_OBJECT_TYPE` (`App::FeaturePython`).

### `object_type(doc=None)` → str

The object type `create()` uses for `doc` (see `CONTAINER_OBJECT_TYPE`).

### `convert_to_container_type(obj)` → object

Rebuild a `ConfigRef` created by version 0.1 (`App::FeaturePython`) as a
container-friendly object. The object is recreated under the same internal name
and re-added to its container; label, `Master`, `Configuration` and parameters
are preserved, and expressions that referenced the old object are re-applied.
Returns `obj` unchanged if it already has a suitable type.

### `parent_group(obj)` → object or None

The document object whose `Group` contains `obj` (the container it lives in).

### `attach_view_provider(obj)`

Attach `ConfigRefViewProvider` to `obj` (GUI only). Called by `create()`.

### `link_master_by_path(config_ref, file_path, object_name="MasterSheet")`

Point an existing ConfigRef's `Master` at a sheet in an external document. Opens
`file_path` if it is not already open. The owner document must already be saved.

### `switch_configuration(obj, row)`

Select `row` for a ConfigRef: writes the part's selector when it has one (and
marks the ConfigRef for recompute, since a container property change does not
re-execute its children), otherwise writes `Configuration` directly.

### `class ConfigRef` — FeaturePython proxy

Object properties:

- `Master` — `App::PropertyXLink` to the master spreadsheet (same or another document).
- `Configuration` — `App::PropertyString` — the selected row name.
- `ConfigurationName` — `App::PropertyString` — what this configuration is called
  on the part; defaults to the object's name. It names the selector property the
  container gets (see *Part variants*) and is preserved by an `App::Link` copy,
  so a variant's ConfigRefs keep pointing at their selectors.
- `ManagedParameters` — `App::PropertyStringList` — parameter names exposed as
  properties (managed automatically).
- One dynamic property per parameter (e.g. `Length`), typed by inference:
  booleans, integers, floats, or quantity properties (`App::PropertyLength`,
  `App::PropertyAngle`, `App::PropertyMass`, …) for unit-bearing cells.
- `ConfigurationValid` / `ConfigurationError` — read-only status properties
  (visible in the property editor) reporting whether the selected
  configuration resolves.
- `TableValid` / `TableErrors` — read-only status properties reporting whether
  the linked master table is structurally sound: `TableErrors` collects the
  `TableSnapshot.problems()` of the master plus any parameter whose name
  collides with an existing property (such a column cannot be exposed and would
  otherwise be dropped silently). Both are set when the reference recomputes;
  with no master linked they read `False` / `"No master spreadsheet linked"`.

All four status properties live in their own property-editor group,
`VALIDATION_GROUP` (`"Validation"`), so the reported problems do not sit in
between the editable inputs (`Master`, `Configuration`) and the parameters
exposed from the master, which stay in `GROUP` (`"ConfigRef"`). Documents
written before that group existed are migrated on the next recompute;
`ConfigRef._normalize_status_properties()` also keeps them visible and
read-only.

The view provider turns either failure into a tree signal: the reference is
shown with a warning icon (`spreadsheetplus-config-warning.svg`) instead of the
normal one whenever `ConfigurationValid` or `TableValid` is false.

The proxy is type-agnostic: it drives `Part::Part2DObjectPython` objects created
by this version as well as the `App::FeaturePython` objects written by version
0.1. The geometry/attachment properties of the container-friendly base type
(`Shape`, `AttachmentSupport`, `MapMode`, …) are hidden in the property editor.

### Part variants

A part can be driven by several configurations at once, one per master table.
FreeCAD's `App::Link` copy-on-change only mirrors properties of the object that is
*linked*, never of its children, so the part - not the ConfigRef - has to carry
the selectors:

- Every ConfigRef inside a container makes the container grow one selector
  property named after its `ConfigurationName` (`App::PropertyString`, group
  `ConfigRef`, status `CopyOnChange`). The names this workbench created are listed
  in the container's hidden `_ConfigurationSlots` property; selectors whose
  ConfigRef is gone are removed again, and no property the workbench did not
  create is ever touched.
- `Configuration` follows its selector. Both directions are kept equal:
  `config_ref.switch_configuration()` (and any direct write to `Configuration`)
  copies the row up into the selector, and a selector change marks the ConfigRefs
  of that part for recompute so they re-read their row. A clash - two
  configurations with the same `ConfigurationName`, or a name that collides with
  an existing property of the container - is reported through
  `ConfigurationError`, and that ConfigRef falls back to its own
  `Configuration`.
- `Link → part` with **Link Copy On Change** `Enabled`/`Tracking` then offers one
  entry per configuration under `Configuration (ConfigRef)`, and every variant
  keeps its own rows. See `docs/usage.md`.

### Module constants

- `CONTAINER_OBJECT_TYPE` (`Part::Part2DObjectPython`) — what new ConfigRefs are
  created as; the only Python-extensible type a `PartDesign::Body` accepts.
- `LEGACY_OBJECT_TYPE` (`App::FeaturePython`) — the pre-0.2 type.
- `GROUP` (`ConfigRef`) — the property group shown in the property editor.

## `freecad.spreadsheetplus.variants`

### `attach()` / `detach()`

Attach (idempotently) or detach the module's document observer. `attach()` is
called from the package's `__init__`, so part variants work headless as well as
in the GUI.

### `class VariantObserver`

A `FreeCAD.addDocumentObserver` object, kept in step with the parts in every
document. FreeCAD pastes a variant's new selector value into the *copy*, and no
object inside the part may depend on the part itself (that is a DAG cycle), so
this observer is the only hook that sees the change. It does two things:

- a selector changed → mark that part's ConfigRefs for recompute, so they read
  the new row (`slotChangedObject`);
- a ConfigRef's `Configuration` changed → copy it up into the part's selector.

Both directions only make the two values equal, so they converge without
re-entrancy bookkeeping. The handler runs on every property change in every
document, so it is deliberately cheap: it skips while a document is being
restored and otherwise tests a set of selector names before doing any work.

## `freecad.spreadsheetplus.view_providers`

### `class ConfigRefViewProvider`

View provider for `ConfigRef` objects. Sets the tree icon (config icon) and
supports serialization (`__getstate__`/`__setstate__`). Attached automatically
by `config_ref.create()` when the GUI is up.

## `freecad.spreadsheetplus.dialogs.select_configuration`

### `class SelectConfigurationDialog(configurations, current="", parent=None)`

Qt dialog that picks a configuration row from a **sorted** list with a
case-insensitive **type-to-search** filter. `selected()` returns the chosen
name (or `None`). Used by the Switch Configuration command.

## `freecad.spreadsheetplus.commands`

Workbench commands (installed by `init_gui.py`):

| Class | Command name |
| :--- | :--- |
| `CreateMasterSheet` | `SpreadSheetPlus_CreateMasterSheet` |
| `CreateConfigRef` | `SpreadSheetPlus_CreateConfigRef` |
| `SwitchConfiguration` | `SpreadSheetPlus_SwitchConfiguration` |

### `freecad.spreadsheetplus.commands.create_config_ref`

- `ACTIVE_CONTAINER_KEYS` — `("pdbody", "part")`, FreeCAD's keys for the active
  container (`Gui/ActiveObjectList.h`).
- `active_container(doc=None)` → object or `None` — the container new objects
  should go into: the active `PartDesign::Body`, else the active `App::Part`,
  in the same document (`None` when nothing is active or the GUI is down).
- `add_to_active_container(obj, doc=None)` → container or `None` — add `obj` to
  that container (warns instead of raising if the container refuses it).

`CreateConfigRef` uses them, so a reference created while a body/part is active
is added to it — the same behaviour as FreeCAD's own object commands. The
`MasterSheet` deliberately stays at the document root: it is shared by several
parts and must not be copied along with a container.
