# Changelog

All notable changes to **SpreadSheetPlus** are recorded here. Dates are
ISO 8601 (`YYYY-MM-DD`).

## [Unreleased]

**Added**
- **Part variants.** A part can now be configured by several `ConfigRef`s at
  once, one per master table, and every `App::Link` variant picks its own row for
  each of them (Length, Pitch, Head style, …) instead of needing one
  combinatorial row per possible part. Each ConfigRef inside a container gives
  the container a selector property named after its new `ConfigurationName`,
  marked `CopyOnChange` so the link mirrors one entry per configuration under
  `Configuration (ConfigRef)`. `freecad.spreadsheetplus.variants` attaches the
  document observer that keeps a part's selectors and its ConfigRefs equal in
  both directions - FreeCAD pastes a variant's new value into the copy and
  nothing inside the part may depend on the part itself, so this is the only hook
  that sees it. Clashing configuration names are reported through
  `ConfigurationError`.
- Validation is now surfaced on the part, not just in the API. A `ConfigRef`
  carries two read-only status properties, `TableValid` and `TableErrors`, that
  report structural problems in the linked master table (duplicate parameter
  names, duplicate configuration names, parameters that are not valid
  identifiers, and parameters whose name collides with an existing property and
  can therefore not be exposed). The reference's tree icon changes to a warning
  icon while `ConfigurationValid` or `TableValid` is false, so a broken part is
  visible without opening the property editor.
- `TableSnapshot.problems()` — the structural check as a method on the parsed
  snapshot. `Table.validate()` now delegates to it, so both the master sheet and
  every `ConfigRef` report the same problems from the same cached parse.
- The four status properties (`ConfigurationValid`, `ConfigurationError`,
  `TableValid`, `TableErrors`) now live in their own **Validation** group in the
  property editor instead of sharing the `ConfigRef` group, so they no longer
  sit in between the editable inputs and the exposed parameters. Documents
  written before the group existed are migrated on the next recompute.

**Fixed**
- A `ConfigRef` can now be moved (dragged) into any container, including a
  `PartDesign::Body`, not just a `Part` or a Std group. New references are
  created as `Part::Part2DObjectPython`, the only Python-extensible type a Body
  accepts (`PartDesign::Body::isAllowed()`); a plain `App::FeaturePython` was
  refused by a Body and a `Part::FeaturePython` would have become the Body's
  base feature. The geometry/attachment properties of that base type are hidden
  in the property editor.
- **Create ConfigRef** now creates the reference inside the *active* container
  (the active `PartDesign::Body`, else the active `Part`) as FreeCAD's own
  object commands do; with no active container it stays at the document root.
- `convert_to_container_type(obj)` upgrades a reference created by 0.1 in place,
  preserving its label, master sheet, configuration, parameters, container and
  the expressions that use it.

**Docs**
- New usage section on placing a `ConfigRef` inside a part/body, and on
  upgrading references from 0.1.
- Corrected expression examples: `<<Name>>.Property` in FreeCAD expression
  syntax refers to an object's **label** (and breaks when the object is
  relabelled); the internal-name form `ConfigRefA.Length` is the robust one and
  is what the docs now use.

**Tests / tooling**
- Added `tests/test_container.py` (GUI): dropping a `ConfigRef` into a
  `PartDesign::Body` / `App::Part` / Std group, moving it between containers,
  expression syntax, and the 0.1→0.2 conversion.
- Added `tests/run_freecad_gui.sh`, which runs the GUI tests with the offscreen
  Qt platform. The AppImage's `AppRun` wrapper forces `QT_QPA_PLATFORM=xcb`,
  which overrode the caller's environment and opened a real window; the VS Code
  GUI test task now uses this script.
- Added `docs/development.md`: running FreeCAD headlessly (the `AppRun`
  `QT_QPA_PLATFORM` trap, the runner's options, GUI-script exit requirements),
  the VS Code tasks, and where to read FreeCAD's behaviour in a local source
  checkout.

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
- Workbench with commands: Create MasterSheet, Create ConfigRef, Switch
  configuration. (The sheet itself is edited in FreeCAD's normal spreadsheet
  editor.)
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
