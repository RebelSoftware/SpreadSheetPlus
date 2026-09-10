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

from .table import Table

GROUP = "ConfigRef"


def _coerce_bool(value: str) -> bool | None:
    lowered = value.strip().lower()
    if lowered in ("true", "1"):
        return True
    if lowered in ("false", "0"):
        return False
    return None


def _is_int(value: str) -> bool:
    try:
        int(value)
        return True
    except ValueError:
        return False


def _is_float(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False


def infer_type(values: list[str]) -> str:
    """Infer a FreeCAD property type from raw (string) cell values."""
    nonempty = [v for v in values if v != ""]
    if not nonempty:
        return "App::PropertyString"
    if all(_coerce_bool(v) is not None for v in nonempty):
        return "App::PropertyBool"
    if all(_is_int(v) for v in nonempty):
        return "App::PropertyInteger"
    if all(_is_float(v) for v in nonempty):
        return "App::PropertyFloat"
    return "App::PropertyString"


def coerce(value: str, prop_type: str):
    """Coerce a raw cell string to the value expected by a property type."""
    if prop_type == "App::PropertyBool":
        return _coerce_bool(value)
    if prop_type == "App::PropertyInteger":
        return int(value)
    if prop_type in ("App::PropertyFloat", "App::PropertyLength", "App::PropertyDistance"):
        return float(value)
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
            return
        self._syncing = True
        try:
            params = table.parameters()
            self._sync_properties(obj, table, params)
            self._sync_values(obj, table, params)
        finally:
            self._syncing = False

    def _sync_properties(self, obj, table, params) -> None:
        managed = list(obj.ManagedParameters)

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
            if hasattr(obj, name):
                if name in managed:
                    new_managed.append(name)
                # else: name collides with a built-in property; leave unmanaged
                continue
            # add a missing property (new parameter, or one lost during restore)
            values = [table.get_value(c, name) for c in table.configurations()]
            obj.addProperty(
                infer_type(values),
                name,
                GROUP,
                f"Parameter '{name}' from the master configuration",
            )
            new_managed.append(name)

        if list(obj.ManagedParameters) != new_managed:
            obj.ManagedParameters = new_managed

    def _sync_values(self, obj, table, params) -> None:
        config = obj.Configuration
        if not config:
            return
        try:
            row = table.get_row(config)
        except KeyError:
            return
        for name in params:
            if not hasattr(obj, name):
                continue
            prop_type = obj.getTypeIdOfProperty(name)
            value = coerce(row[name], prop_type)
            try:
                if getattr(obj, name) != value:
                    setattr(obj, name, value)
            except Exception:
                # value cannot be coerced to the property type; leave as-is
                continue


def create(doc, master, configuration: str, name: str = "ConfigRef"):
    """Create and return a ConfigRef FeaturePython object."""
    doc = doc or App.ActiveDocument
    if doc is None:
        raise ValueError("FCSpreadSheetPlus: no active document")
    obj = doc.addObject("App::FeaturePython", name)
    ConfigRef(obj)
    obj.Master = master
    obj.Configuration = configuration
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
