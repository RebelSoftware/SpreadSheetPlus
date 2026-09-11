# FCSpreadSheetPlus — Project Plan

## Goal

Decouple the spreadsheet from the part so that a **single master spreadsheet**
exists once per project (and is reusable across files), and each **part links to
it and selects a named row** (a "configuration"). Multiple parts can use
different rows — or the same row — from one spreadsheet.

## 1. Problem statement (why the current model hurts)

FreeCAD's Spreadsheet workbench today:

1. A `Spreadsheet::Sheet` normally lives **inside** the Body/Part it drives.
2. A **configuration table** (`src/Mod/Spreadsheet/Gui/DlgSheetConf.cpp`) binds a
   range of sheet cells to a dynamic `PropertyEnumeration` on the part using
   **hidden references** (`hiddenref` / `href` expression functions).
3. The part's parameters resolve their values from those bound cells.

Because the sheet is embedded in the part:

- Copying the part, or making a linked copy with "copy on change", **copies the
  sheet**.
- Editing one parameter across N parts means editing N copied sheets.

## 2. Target model

```
Document (or separate "library" document)
└── MasterSheet                 # one instance, holds the table
        rows    = configurations (named)
        columns = parameters (named)

Part A ──► ConfigRef ──► MasterSheet, row "ConfigA"
Part B ──► ConfigRef ──► MasterSheet, row "ConfigB"
Part C ──► ConfigRef ──► MasterSheet, row "ConfigA"   (shared row)
```

- **MasterSheet** — top-level document object that wraps a `Spreadsheet::Sheet`
  plus a *table schema* (which rows are configurations, which columns are
  parameters). It is never embedded in a part.
- **ConfigRef** — a small per-part object (`App::FeaturePython`) that:
  - links to a `MasterSheet` (`App::PropertyLink` same-document,
    `App::PropertyXLink` cross-file),
  - selects a configuration **by name** (`PropertyEnumeration` populated from the
    row names),
  - exposes the selected row's parameters (as read-only dynamic properties or
    bound hidden references) so the part's parameters can reference them.
- Part parameters then use ordinary expressions such as
  `<<ConfigRef>>.ParamName` — they never reference the sheet directly.

## 3. Table convention (canonical layout)

One spreadsheet = **one** configuration table, so no marker is needed. The
layout is fixed:

- **Row 1** — free text (table title / notes). Ignored by the code except the
  optional title in `A1`.
- **Row 2** — header row: parameter names in columns `B`, `C`, ... (read
  rightwards until empty). The `A2` cell is a cosmetic label for the
  configuration-name column and is ignored by lookups.
- **Column A, rows 3..n** — configuration names (read downwards until empty).
- **Data** — `B3..` — one value per (configuration, parameter).

Example:

```
             A           B        C       D        E
1   This is my test Spreadsheet configuration
2   [Blank]           Length   Width   Depth   Enabled
3   TypeA                80      40      10     True
4   TypeB                85      42     100     False
5   TypeC                90      55      90     True
```

- Parameter names come from `B2, C2, ...`.
- Configuration names come from `A3, A4, ...`.
- `A1` optionally holds the title; `A2` is free-form and not used for lookup.
- Rows/columns are kept contiguous: adding appends, removing deletes the row or
  column (via `Sheet.removeRows` / `removeColumns`) so the "read until empty"
  scan stays correct.

## 4. Component / function inventory

### A. Table model (headless, pure Python)
- `freecad/fcspreadsheetplus/table.py`
  - `Table(sheet)` — wraps a `Spreadsheet::Sheet` as a named table.
  - `read_schema()` → `{param_name: col_index}`, `[config_names]`
  - `write_schema(param_names, config_names)` — lays out the header/name cells.
  - `get_value(config_name, param_name)` / `set_value(...)`
  - `get_row(config_name)` → dict of `{param: value}`
  - `discover()` — locate the table range from the marker.
  - `validate()` — check for duplicate names, empty cells, invalid identifiers.

### B. MasterSheet object
- `freecad/fcspreadsheetplus/master_sheet.py`
  - `MasterSheet.create(doc)` — creates a `Spreadsheet::Sheet` (or a
    `App::FeaturePython` that owns a sheet) at the document root, initializes the
    table.
  - Exposes `parameters`, `configurations`, `add_configuration`, `remove_configuration`,
    `add_parameter`, `rename_parameter`, `set_value`, `get_value`.

### C. ConfigRef object (the decoupling link)
- `freecad/fcspreadsheetplus/config_ref.py`
  - `ConfigRef` proxy for an `App::FeaturePython` with:
    - `Master` — `App::PropertyXLink` → MasterSheet.
    - `Configuration` — `App::PropertyEnumeration` (row names) + `App::PropertyString`
      fallback.
  - `onChanged(obj, "Configuration")` — (re)create the dynamic read-only
    properties for the selected row, one per parameter.
  - `rebuild_parameters(obj)` — add/remove dynamic properties to match the
    master's parameter columns.
  - `resolve_cell(obj, param)` — map `(config, param)` → sheet cell address.
  - ViewProvider: `ConfigRefViewProvider` (icon, tree display, no shape).

### D. Expression / binding layer
- `freecad/fcspreadsheetplus/bind.py`
  - `bind_to_config_ref(part, config_ref, param_map)` — set expressions on the
    part's parameters: `part.setExpression("Length", "<<ConfigRef>>.Length")`.
  - `link_parameter(obj, prop, cell)` — *(planned, then dropped)* set a hidden
    reference `obj.setExpression(prop, "hiddenref(MasterSheet.B2)")` for
    two-way binding. Rejected for now — see decision 3.
  - `unbind(...)` helpers.

### E. Cross-file layer
- `freecad/fcspreadsheetplus/external.py`
  - `attach_external_master(config_ref, file_path)` — set the `PropertyXLink`
    to an external document's MasterSheet (via `App::Link` / `Document.open`).
  - Path handling (relative vs absolute), placeholder/dependency management.

### F. UX (GUI)
- `freecad/fcspreadsheetplus/commands/` — commands:
  - `CreateMasterSheet` — create a `MasterSheet` in the active document.
  - `CreateConfigRef` — turn the selected sheet into a `ConfigRef` (first row).
  - `EditConfigTable` — open the table editor dialog.
  - `SwitchConfiguration` — change the selected row from the tree/property editor.
  - `CreateSheet` — create a plain `Spreadsheet::Sheet` (parity with default workbench).
- `freecad/fcspreadsheetplus/dialogs/table_editor.py` — `TableEditorDialog`
  (params = columns, configs = rows, add/remove buttons, write-back on OK).
- `freecad/fcspreadsheetplus/view_providers.py` — `ConfigRefViewProvider` (tree icon).

## 5. Phased roadmap

### Phase 0 — Table model + tests (no GUI)
- Implement `table.py` on top of `Spreadsheet::Sheet`.
- Headless tests: create sheet → write schema → get/set values → discover →
  validate.
- **Exit criteria:** `freecadcmd tests/test_table.py` green.

### Phase 1 — Same-document single instance
- `MasterSheet` object + `ConfigRef` (`App::FeaturePython`) with `PropertyLink`.
- Row selection via `PropertyEnumeration`; dynamic parameter properties.
- Part parameters reference `<<ConfigRef>>.<param>`.
- **Exit criteria:** two parts in one document share one sheet, each with a
  different row; changing the sheet updates both; part copy no longer copies the
  sheet.

### Phase 2 — Cross-file sharing
- Switch `ConfigRef.Master` to `App::PropertyXLink` + `App::Link`.
- External document resolution, relative paths, recompute on load.
- **Exit criteria:** master sheet lives in `library.FCStd`; parts in another
  file reference it.

### Phase 3 — UX polish
- Toolbar/menu commands, tree context menus, table editor dialog, configuration
  switcher, error indicators (missing row/param, broken link).
- **Status: done** — 5 commands, `TableEditorDialog`, `ConfigRefViewProvider`,
  `tests/test_gui.py` (4/4 offscreen).

### Phase 4 — Robustness & advanced
- Caching of resolved rows; efficient recompute on parameter/row changes.
- ~~Two-way binding via `hiddenref`~~ — **rejected**: a shared cell would let a
  naive edit on one part silently change every other part using that cell.
  ConfigRef parameters are read-only; revisit only if user feedback asks for it.
- Undo/redo, document save/restore, units, i18n, validation UI.
- Addon Manager packaging.

## 6. Key technical decisions & risks

| Decision | Options | Notes |
| :--- | :--- | :--- |
| Language boundary | Python vs C++ patch | Most of this is expressible in Python via `FeaturePython`, `PropertyXLink`, `setExpression`. Hidden-ref *binding* and cross-doc recompute are the riskiest parts to replicate exactly. |
| Value propagation | (a) expression read-through, (b) copy-on-switch, (c) hidden-ref binding | Use (a) expressions; (c) is **rejected** — two-way editing risks surprising cross-part changes on shared cells. |
| Row selection | `PropertyEnumeration` vs `PropertyString` | Enumeration gives a drop-down and validates names; keep a string fallback for not-yet-created rows. |
| MasterSheet type | wrap existing `Spreadsheet::Sheet` vs custom `FeaturePython` | Wrapping the existing sheet preserves the full cell/expression engine. |
| Cross-file | `PropertyXLink` + `App::Link` | Standard FreeCAD mechanism (`doc#obj.prop` ObjectIdentifiers already support this). |

## 7. Decisions (confirmed with you)

1. **Part scope** — support both `PartDesign::Body` and `App::Part`.
2. **Cross-file** — start same-document (Phase 1 uses `PropertyLink`); add
   cross-file via `PropertyXLink` / `App::Link` in Phase 2.
3. **Edit model** — read-through only: values are edited at the `MasterSheet`;
   parts resolve values via expressions. Two-way binding is **rejected** (not
   just deferred): a ConfigRef parameter is often shared by several parts, so
   editing it in place would silently update all of them. Exposed parameters
   are therefore read-only in the property editor.
4. **Parameter surface** — `ConfigRef` exposes **all** parameters of the table
   as read-only dynamic properties.

### Remaining open (can decide later)
- Whether `MasterSheet` wraps an existing `Spreadsheet::Sheet` or owns its own.

## 8. Documentation (written as we go)

Docs ship with each phase (same commit). Current files:

- `docs/usage.md` — how to use the workbench: table layout, scripting quick
  start, sharing across parts, cross-file, value types.
- `docs/api.md` — reference for `Table`, `MasterSheet`, `ConfigRef`, `Sheet`.
- `README.md` — landing page linking into `docs/`.

Add the GUI workflow (toolbar/dialog steps) to `usage.md` once Phase 3 lands.
