# Changelog

All notable changes to **FCSpreadSheetPlus** are recorded here. Dates are
ISO 8601 (`YYYY-MM-DD`).

## [0.1.0] — 2026-09-13

Initial release.

**Core**
- `MasterSheet` — a single document-level configuration table
  (rows = configurations, columns = parameters) built on FreeCAD's
  `Spreadsheet::Sheet`.
- `ConfigRef` — a per-part `App::FeaturePython` that links to a master sheet
  (same document or cross-file via `App::PropertyXLink`) and exposes the
  selected configuration's parameters as read-only properties.
- Parts reference parameters with plain expressions
  (`<<ConfigRef>>.Length`), so one spreadsheet can drive many parts and copying
  a part no longer copies the sheet.

**Values**
- Type inference: booleans, integers, floats, and unit-bearing quantities
  (`App::PropertyLength` / `Angle` / `Mass` / …).
- Content-addressed table snapshot cache (parses the master once per change).

**UX**
- Workbench with commands: Create MasterSheet, Create ConfigRef, Edit
  configuration table, Switch configuration, Create spreadsheet.
- Table editor with a validation status line.
- Case-insensitive configuration names; sorted, searchable configuration
  picker.
- `ConfigurationValid` / `ConfigurationError` status shown in the property
  editor.

**Robustness**
- Safe recompute/save/restore of dynamic properties; broken-link and
  unknown-configuration handling; parameter-name collision protection;
  automatic re-typing when a column's values change type.

**i18n**
- All UI strings translatable; German demo translation included.
