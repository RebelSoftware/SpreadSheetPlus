# SPDX-License-Identifier: LGPL-2.1-or-later
"""ConfigRef: a per-part link to a MasterSheet with a selected configuration.

A ConfigRef is an `App::FeaturePython` that links to a `Spreadsheet::Sheet`
(the master, possibly in another document) and selects one configuration row by
name. It exposes that row's parameters as read-only dynamic properties,
refreshed from the master whenever the configuration changes or the document
recomputes.
"""

from __future__ import annotations

import os

import FreeCAD as App

from .table import EMPTY, EXPRESSION, NUMBER, QUANTITY, STRING, Table

GROUP = "ConfigRef"

# FreeCAD unit-type name -> property class for quantity columns. Unmapped unit
# types fall back to App::PropertyString (the value is stored as text).
_QUANTITY_PROPERTY_BY_TYPE = {
    "Length": "App::PropertyLength",
    "Angle": "App::PropertyAngle",
    "Mass": "App::PropertyMass",
    "Area": "App::PropertyArea",
    "Volume": "App::PropertyVolume",
    "Temperature": "App::PropertyTemperature",
    "TimeSpan": "App::PropertyTime",
    "Frequency": "App::PropertyFrequency",
    "Force": "App::PropertyForce",
    "Pressure": "App::PropertyPressure",
    "Power": "App::PropertyPower",
    "Velocity": "App::PropertyVelocity",
    "Acceleration": "App::PropertyAcceleration",
}
_QUANTITY_PROPERTY_TYPES = frozenset(_QUANTITY_PROPERTY_BY_TYPE.values())


def _coerce_bool(value: str) -> bool | None:
    lowered = value.strip().lower()
    if lowered in ("true", "1"):
        return True
    if lowered in ("false", "0"):
        return False
    return None


def _is_boolish(kind: str, value) -> bool:
    if kind == STRING:
        return _coerce_bool(value) is not None
    if kind == NUMBER:
        return value in (0, 1)
    return False


def infer_type(cells) -> str:
    """Infer a FreeCAD property type from parsed ``(kind, value)`` cells."""
    nonempty = [cell for cell in cells if cell[0] != EMPTY]
    if not nonempty:
        return "App::PropertyString"
    if all(_is_boolish(kind, value) for kind, value in nonempty):
        return "App::PropertyBool"
    if all(kind == NUMBER for kind, _ in nonempty):
        if all(isinstance(value, int) for _, value in nonempty):
            return "App::PropertyInteger"
        return "App::PropertyFloat"
    if all(kind == QUANTITY for kind, _ in nonempty):
        unit_types = {value.Unit.Type for _, value in nonempty}
        if len(unit_types) == 1:
            return _QUANTITY_PROPERTY_BY_TYPE.get(unit_types.pop(), "App::PropertyString")
        return "App::PropertyString"
    return "App::PropertyString"


def coerce(value, kind: str, prop_type: str):
    """Coerce a parsed cell value to the value expected by a property type."""
    if prop_type == "App::PropertyBool":
        return _coerce_bool(value) if kind == STRING else bool(value)
    if prop_type == "App::PropertyInteger":
        return int(value)
    if prop_type == "App::PropertyFloat":
        return float(value)
    if prop_type in _QUANTITY_PROPERTY_TYPES:
        # Quantity properties accept Units.Quantity directly and convert
        # numbers/strings to the property's unit (dimension-aware).
        return value
    # App::PropertyString (or unknown): store a faithful string.
    if kind == NUMBER:
        return str(value)
    if kind == QUANTITY:
        return value.UserString
    return value


class ConfigRef:
    """FeaturePython proxy for a ConfigRef object."""

    def __init__(self, obj) -> None:
        if not hasattr(obj, "Master"):
            obj.addProperty(
                "App::PropertyXLink",
                "Master",
                GROUP,
                "Linked master spreadsheet",
            )
        if not hasattr(obj, "Configuration"):
            obj.addProperty(
                "App::PropertyString",
                "Configuration",
                GROUP,
                "Selected configuration name",
            )
        if not hasattr(obj, "ManagedParameters"):
            obj.addProperty(
                "App::PropertyStringList",
                "ManagedParameters",
                GROUP,
                "Parameters exposed by this ConfigRef",
            )
        if not hasattr(obj, "ConfigurationValid"):
            obj.addProperty(
                "App::PropertyBool",
                "ConfigurationValid",
                GROUP,
                "Whether the selected configuration resolves",
                hidden=True,
            )
        if not hasattr(obj, "ConfigurationError"):
            obj.addProperty(
                "App::PropertyString",
                "ConfigurationError",
                GROUP,
                "Error message when the configuration cannot be resolved",
                hidden=True,
            )
        obj.Proxy = self
        self._syncing = False

    # -- helpers ---------------------------------------------------------
    def _table(self, obj) -> Table | None:
        master = obj.Master
        if master is None:
            return None
        return Table(master)

    def onChanged(self, obj, prop: str) -> None:
        # No work here. Changing a property marks the object for recompute, and
        # the actual sync runs in execute() (only on recompute, after the
        # document is fully restored). This avoids mutating properties while a
        # document is being restored, which would corrupt the exposed
        # parameter properties.
        pass

    def execute(self, obj) -> None:
        self._sync(obj)

    def _sync(self, obj) -> None:
        if self._syncing:
            return
        table = self._table(obj)
        if table is None:
            self._set_status(obj, "No master spreadsheet linked", False)
            return
        snapshot = table.snapshot()
        self._syncing = True
        try:
            managed = self._sync_properties(obj, snapshot)
            self._sync_values(obj, snapshot, managed)
        finally:
            self._syncing = False
        self._update_status(obj, snapshot)

    def _sync_properties(self, obj, snapshot) -> list[str]:
        managed = list(obj.ManagedParameters)
        params = snapshot.params

        # Remove managed properties whose parameter no longer exists. Only done
        # when we have a known non-empty parameter list (execute runs after the
        # document is fully restored, so params is reliable here).
        if params:
            for name in managed:
                if name not in params and hasattr(obj, name):
                    obj.removeProperty(name)
            managed = [n for n in managed if n in params]

        new_managed = []
        for name in params:
            column = snapshot.column(name)
            inferred = infer_type(column)
            if hasattr(obj, name):
                if name not in managed:
                    # name collides with a built-in property or a Python
                    # attribute (e.g. a parameter named "recompute"); leave it
                    # unmanaged rather than clobbering the object.
                    continue
                new_managed.append(name)
                # Re-type an existing managed property if its type no longer
                # matches the column. This matters when a column is created
                # while still empty: it is first exposed as a string and must
                # be upgraded once values arrive. Only re-type when the column
                # has content, so a transiently empty column does not demote a
                # typed property back to string.
                current = obj.getTypeIdOfProperty(name)
                if current != inferred and any(kind != EMPTY for kind, _ in column):
                    obj.removeProperty(name)
                    obj.addProperty(
                        inferred,
                        name,
                        GROUP,
                        f"Parameter '{name}' from the master configuration",
                        read_only=True,
                    )
                continue
            # add a missing property (new parameter, or one lost during restore)
            obj.addProperty(
                inferred,
                name,
                GROUP,
                f"Parameter '{name}' from the master configuration",
                read_only=True,
            )
            new_managed.append(name)

        if list(obj.ManagedParameters) != new_managed:
            obj.ManagedParameters = new_managed

        # Parameters are read-through: the master is the single source of
        # truth. Keep the exposed properties read-only in the property editor
        # so a user cannot edit them there (the edit would be silently
        # overwritten on the next recompute). Python can still set the value,
        # which execute() relies on.
        for name in new_managed:
            if "ReadOnly" not in obj.getEditorMode(name):
                obj.setEditorMode(name, 1)

        return new_managed

    def _sync_values(self, obj, snapshot, managed) -> None:
        config = obj.Configuration
        if not config:
            return
        # Only touch properties we own (ManagedParameters). Iterating over the
        # full parameter list would also hit names that collide with built-in
        # properties or Python attributes (e.g. a parameter named "recompute"),
        # which must not be read or written here.
        for name in managed:
            try:
                kind, value = snapshot.cell(config, name)
            except KeyError:
                return
            if kind in (EMPTY, EXPRESSION):
                continue
            prop_type = obj.getTypeIdOfProperty(name)
            coerced = coerce(value, kind, prop_type)
            try:
                if getattr(obj, name) != coerced:
                    setattr(obj, name, coerced)
            except Exception:
                # value cannot be coerced to the property type; leave as-is
                continue

    def _update_status(self, obj, snapshot) -> None:
        config = obj.Configuration
        error = ""
        valid = True
        if config:
            configs = snapshot.configs
            if configs and config not in configs:
                error = f"Unknown configuration: {config!r}"
                valid = False
        self._set_status(obj, error, valid)

    def _set_status(self, obj, error: str, valid: bool) -> None:
        if obj.ConfigurationValid != valid:
            obj.ConfigurationValid = valid
        if obj.ConfigurationError != error:
            obj.ConfigurationError = error


def create(doc, master, configuration: str, name: str = "ConfigRef"):
    """Create and return a ConfigRef FeaturePython object."""
    doc = doc or App.ActiveDocument
    if doc is None:
        raise ValueError("FCSpreadSheetPlus: no active document")
    obj = doc.addObject("App::FeaturePython", name)
    ConfigRef(obj)
    obj.Master = master
    obj.Configuration = configuration
    if App.GuiUp and hasattr(obj, "ViewObject") and obj.ViewObject is not None:
        from .view_providers import ConfigRefViewProvider

        ConfigRefViewProvider(obj.ViewObject)
    obj.recompute()
    return obj


def link_master_by_path(config_ref, file_path: str, object_name: str = "MasterSheet"):
    """Point a ConfigRef's Master at a MasterSheet in an external document.

    Opens *file_path* if it is not already open, then sets the `Master` link to
    the object named *object_name* in that document.
    """
    target = os.path.abspath(file_path)
    doc = None
    for candidate in App.listDocuments().values():
        try:
            if os.path.abspath(candidate.FileName) == target:
                doc = candidate
                break
        except OSError:
            continue
    if doc is None:
        doc = App.openDocument(file_path)
    master = doc.getObject(object_name)
    if master is None:
        raise ValueError(f"object {object_name!r} not found in {file_path!r}")
    config_ref.Master = master
    return config_ref
