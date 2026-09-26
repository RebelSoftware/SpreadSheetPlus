# SPDX-License-Identifier: LGPL-2.1-or-later
"""ConfigRef: a per-part link to a MasterSheet with a selected configuration.

A ConfigRef links to a `Spreadsheet::Sheet` (the master, possibly in another
document) and selects one configuration row by name. It exposes that row's
parameters as read-only dynamic properties, refreshed from the master whenever
the configuration changes or the document recomputes.

Choosing a row is a pick from the master's configurations, never free text, so
both places that show the selection offer that pick:

* the ConfigRef's own ``Configuration`` property carries the ``UserEdit``
  status, which makes FreeCAD's property editor show an edit button whose click
  it routes to :meth:`ConfigRef.editProperty` - the hook that opens the
  configuration picker (see `dialogs.select_configuration.choose_configuration`).
* the selector a container carries for the reference (see `_sync_slots`) is an
  ``App::PropertyEnumeration`` of the available rows, which the property editor
  shows as a drop-down. FreeCAD only lets a *Python* object react to a property
  click, and a `PartDesign::Body` / `App::Part` is not one, so a drop-down is
  the only way a part can offer the list too - it is what FreeCAD's own
  configuration table does on a Body.
"""

from __future__ import annotations

import os

import FreeCAD as App

from .master_sheet import keep_shared
from .table import EMPTY, EXPRESSION, NUMBER, QUANTITY, STRING, Table

GROUP = "ConfigRef"

#: Property group holding the read-only validation status properties. They are
#: kept out of `GROUP` so the problems do not sit in between the editable inputs
#: (`Master`, `Configuration`) and the parameters exposed from the master.
VALIDATION_GROUP = "Validation"

#: Object type used for new ConfigRefs.
#:
#: A ConfigRef must be a child that its container accepts, and the containers
#: differ (verified against FreeCAD 1.1, ``PartDesign::Body::isAllowed()`` and
#: ``ViewProviderBody::canDropObject()``):
#:
#: * ``App::Part`` / ``App::DocumentObjectGroup`` accept any document object,
#: * a ``PartDesign::Body`` only accepts ``PartDesign::Feature``, ``Part::Datum``,
#:   ``Part::Part2DObject``, the ShapeBinders, ``App::VarSet``,
#:   ``App::DatumElement`` and ``App::LocalCoordinateSystem``.
#:
#: So a plain ``App::FeaturePython`` (what this addon used to create) is refused
#: by a Body, and a ``Part::FeaturePython`` is accepted but then *replaces the
#: Body's BaseFeature* — neither is what a configuration reference wants.
#: ``Part::Part2DObjectPython`` is the only Python-extensible type a Body takes
#: as an ordinary child (it is what Draft uses for its scripted objects). The
#: geometry/attachment properties it brings along are hidden in the property
#: editor, see ``_hide_inherited_properties``.
CONTAINER_OBJECT_TYPE = "Part::Part2DObjectPython"

#: Type used by ConfigRefs created by earlier versions and by callers that ask
#: for it explicitly. Still fully supported, but FreeCAD gives no way to change
#: an object's type, so such a ConfigRef cannot be moved into a
#: ``PartDesign::Body``; see ``convert_to_container_type``.
LEGACY_OBJECT_TYPE = "App::FeaturePython"

#: Properties inherited from the container-friendly base type that describe
#: geometry/attachment and are meaningless for a configuration reference.
_HIDDEN_BASE_PROPERTIES = (
    "AttacherEngine",
    "AttacherType",
    "AttachmentSupport",
    "AttachmentOffset",
    "MapMode",
    "MapPathParameter",
    "MapReversed",
    "Shape",
    "ShapeMaterial",
)

#: Read-only status properties (all in `VALIDATION_GROUP`), kept visible in the
#: property editor so the problem is discoverable and not just in a console
#: warning.
_STATUS_PROPERTIES = (
    "ConfigurationValid",
    "ConfigurationError",
    "TableValid",
    "TableErrors",
)

#: Property type of a container's configuration selector. An enumeration is
#: shown as a drop-down of its items, which is how the user picks a row on the
#: part/Body itself (a Body is a C++ object, so it cannot run our own dialog -
#: see the module docstring).
_SELECTOR_TYPE = "App::PropertyEnumeration"

#: Hidden list of the configuration selectors a container owns. It records
#: which properties on the container were created by this workbench, so stale
#: ones can be removed without ever touching a property of the document.
_SLOT_REGISTRY = "_ConfigurationSlots"

#: Names of the configuration selectors currently in use, so the document
#: observer can recognise one without inspecting any object.
_SLOT_NAMES: set = set()

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


def _supports_container_type(doc) -> bool:
    """Whether *doc* can create a `Part::Part2DObjectPython` object."""
    try:
        import Part  # noqa: F401  (registers the Part object types)
    except Exception:
        return False
    try:
        return CONTAINER_OBJECT_TYPE in doc.supportedTypes()
    except Exception:
        # Older builds without Document.supportedTypes(): try our luck.
        return True


def object_type(doc=None) -> str:
    """Return the object type to use for a new ConfigRef in *doc*.

    Prefers `CONTAINER_OBJECT_TYPE` so the reference can be placed inside a
    `PartDesign::Body` as well as in a `Part`/group; falls back to
    `LEGACY_OBJECT_TYPE` when the Part module is unavailable.
    """
    doc = doc or App.ActiveDocument
    if doc is not None and not _supports_container_type(doc):
        return LEGACY_OBJECT_TYPE
    return CONTAINER_OBJECT_TYPE


def _add_object(doc, name: str, type_id: str | None = None):
    """Add the ConfigRef's document object, with a legacy-type fallback."""
    wanted = type_id or object_type(doc)
    if wanted == CONTAINER_OBJECT_TYPE:
        try:
            return doc.addObject(wanted, name)
        except Exception:
            # The Part types are missing/not registered: fall back to a plain
            # feature so creating a reference still works.
            pass
    return doc.addObject(LEGACY_OBJECT_TYPE, name)


def _hide_inherited_properties(obj) -> None:
    """Hide the base type's geometry/attachment properties in the editor."""
    for name in _HIDDEN_BASE_PROPERTIES:
        if not hasattr(obj, name):
            continue
        try:
            if obj.getEditorMode(name) != ["Hidden"]:
                obj.setEditorMode(name, 2)
        except Exception:
            continue


def _mark_user_edit(obj, name: str) -> None:
    """Let the property editor offer an edit button for *name*.

    A property carrying the ``UserEdit`` status is shown with a button whose
    click FreeCAD routes to the owning object's `editProperty` hook. Older
    releases do not know the status at all; there the property stays a plain
    text field instead of turning into an unresponsive button.
    """
    try:
        if "UserEdit" not in obj.getPropertyStatus():
            return
        obj.setPropertyStatus(name, "UserEdit")
    except Exception:
        # getPropertyStatus()/setPropertyStatus() are not available on very old
        # builds: no click-to-edit then, but the reference still works.
        return


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
        if not hasattr(obj, "ConfigurationName"):
            obj.addProperty(
                "App::PropertyString",
                "ConfigurationName",
                GROUP,
                "Name of this configuration on its part",
            )
        if not obj.ConfigurationName:
            # Documents written before this property existed: the object name is
            # a sensible default, and unlike the object name it survives an
            # App::Link copy (which is what keeps a variant's selectors wired).
            obj.ConfigurationName = obj.Name
        # A selected row is a configuration *choice*, so mark the property:
        # App::Link copy-on-change mirrors the marked properties of the object
        # that is linked, which is what gives every link its own selection.
        obj.setPropertyStatus("Configuration", "CopyOnChange")
        # ...and a choice among the master's rows, never free text: "UserEdit"
        # makes the property editor show an edit button for it and call the
        # proxy's editProperty() when it is clicked, which opens the picker.
        _mark_user_edit(obj, "Configuration")
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
                VALIDATION_GROUP,
                "Whether the selected configuration resolves",
                read_only=True,
            )
        if not hasattr(obj, "ConfigurationError"):
            obj.addProperty(
                "App::PropertyString",
                "ConfigurationError",
                VALIDATION_GROUP,
                "Error message when the configuration cannot be resolved",
                read_only=True,
            )
        if not hasattr(obj, "TableValid"):
            obj.addProperty(
                "App::PropertyBool",
                "TableValid",
                VALIDATION_GROUP,
                "Whether the master configuration table is structurally valid",
                read_only=True,
            )
        if not hasattr(obj, "TableErrors"):
            obj.addProperty(
                "App::PropertyString",
                "TableErrors",
                VALIDATION_GROUP,
                "Structural problems found in the master configuration table",
                read_only=True,
            )
        obj.Proxy = self
        self._syncing = False
        _hide_inherited_properties(obj)

    # -- helpers ---------------------------------------------------------
    def _table(self, obj) -> Table | None:
        master = obj.Master
        if master is None:
            return None
        return Table(master)

    def editProperty(self, name: str) -> bool:
        """Open the configuration picker - FreeCAD's property editor hook.

        A property that carries the ``UserEdit`` status gets an edit button in
        the property editor, and clicking it calls this method on the proxy
        (``FeaturePythonImp::editProperty``). The selection is one of the
        master's rows, so the picker replaces typing a name by hand.

        Returns True when the property was handled. FreeCAD treats a falsy
        return as "not implemented" and falls back to doing nothing.
        """
        if name != "Configuration":
            return False
        if not App.GuiUp:
            return False
        # GUI code (Qt), so import it only when the hook actually runs: this
        # module is imported headless too.
        from .dialogs.select_configuration import choose_configuration

        obj = object_of(self)
        if obj is None:
            return False
        choose_configuration(obj)
        return True

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
        self._share_master(obj)
        table = self._table(obj)
        snapshot = table.snapshot() if table is not None else None
        problems = self._apply_container_row(
            obj, snapshot.configs if snapshot is not None else ()
        )
        if table is None:
            problems.append("No master spreadsheet linked")
            self._set_status(obj, "\n".join(problems), False)
            self._set_table_status(obj, ["No master spreadsheet linked"])
            return
        self._syncing = True
        try:
            managed = self._sync_properties(obj, snapshot)
            self._sync_values(obj, snapshot, managed)
        finally:
            self._syncing = False
        self._update_status(obj, snapshot, problems)
        self._update_table_status(obj, snapshot, managed)

    def _share_master(self, obj) -> None:
        """Keep the master sheet out of variant copies (`master_sheet.keep_shared`).

        A variant deep-copies the part *and its dependencies*, so without the
        marker the copied reference reads a snapshot of the table instead of the
        shared master (see `MasterSheet.keep_shared`). Only a same-document
        master needs it: FreeCAD already leaves objects from other documents out
        of a copy-on-change copy, and a sheet in another file is not ours to
        modify anyway.
        """
        master = obj.Master
        if master is None or getattr(master, "Document", None) is not obj.Document:
            return
        keep_shared(master)

    def _apply_container_row(self, obj, configurations=()) -> list[str]:
        """Adopt the row selected on the part, when the part owns a selector.

        FreeCAD's App::Link copy-on-change only mirrors properties of the object
        that is linked, never of its children, so a part carries one selector
        property per configuration - that is what lets a variant pick its own row
        for every configuration instead of sharing one part-wide name. A
        ConfigRef follows that selector; `variants.VariantObserver` is what marks
        it for recompute when the selector changes, because nothing inside the
        part may depend on the part itself (FreeCAD forbids that cycle).

        *configurations* are the rows the master has now; they become the items
        of the selector, so the part's property editor can offer them.
        """
        container = parent_group(obj)
        if container is None or container.TypeId == "App::LinkGroup":
            # Outside a part - including the private LinkGroup FreeCAD uses to
            # hold copy-on-change copies - the ConfigRef is its own selector.
            return []
        row, problems = _sync_slots(container, obj, configurations)
        if row is None:
            # No usable selector (the name is taken on the container): the
            # ConfigRef keeps working from its own value, and says why.
            return problems
        if row != obj.Configuration:
            obj.Configuration = row
        return problems

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
            if name in new_managed:
                # A duplicate parameter name makes the table invalid (reported
                # through TableErrors); keep the first column only.
                continue
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

    def _update_status(self, obj, snapshot, problems=()) -> None:
        messages = list(problems)
        config = obj.Configuration
        if config:
            configs = snapshot.configs
            if configs and snapshot.resolve_config(config) is None:
                messages.append(f"Unknown configuration: {config!r}")
        self._set_status(obj, "\n".join(messages), not messages)

    def _update_table_status(self, obj, snapshot, managed) -> None:
        """Report structural problems in the linked master table.

        Everything is derived from the cached snapshot, so this costs no extra
        reads of the spreadsheet.
        """
        problems = list(snapshot.problems())
        # A parameter whose name collides with a built-in property or a Python
        # attribute (e.g. a column called "recompute") cannot be exposed, so
        # _sync_properties skips it. TableSnapshot.problems() cannot see that,
        # so report it from the set of parameters actually exposed here.
        for name in snapshot.params:
            if name not in managed and hasattr(obj, name):
                problems.append(
                    f"parameter name collides with an existing property: {name!r}"
                )
        self._set_table_status(obj, problems)

    def _set_status(self, obj, error: str, valid: bool) -> None:
        changed = obj.ConfigurationValid != valid
        if changed:
            obj.ConfigurationValid = valid
        if obj.ConfigurationError != error:
            obj.ConfigurationError = error
            changed = True
        # Keep the status visible and read-only in the property editor (also
        # migrates properties created as hidden in older documents).
        self._normalize_status_properties(obj)
        if changed:
            self._refresh_icon(obj)

    def _set_table_status(self, obj, problems) -> None:
        valid = not problems
        message = "\n".join(problems)
        changed = obj.TableValid != valid
        if changed:
            obj.TableValid = valid
        if obj.TableErrors != message:
            obj.TableErrors = message
            changed = True
        self._normalize_status_properties(obj)
        if changed:
            self._refresh_icon(obj)

    @staticmethod
    def _normalize_status_properties(obj) -> None:
        """Keep the status properties read-only, visible and in one group.

        Also migrates documents written by earlier versions: the status
        properties used to be created hidden (before 0.2) and in the
        "ConfigRef" group (before the validation group existed). Changing a
        group is metadata only, so the value and the editor mode are untouched.
        """
        for name in _STATUS_PROPERTIES:
            if obj.getGroupOfProperty(name) != VALIDATION_GROUP:
                obj.setGroupOfProperty(name, VALIDATION_GROUP)
            if obj.getEditorMode(name) != ["ReadOnly"]:
                obj.setEditorMode(name, 1)

    @staticmethod
    def _refresh_icon(obj) -> None:
        """Ask the tree to re-read the icon after a validity change.

        The view provider picks its icon from the status properties, so the
        tree has to be told that they changed.
        """
        if not App.GuiUp:
            return
        view = getattr(obj, "ViewObject", None)
        if view is None:
            return
        try:
            view.signalChangeIcon()
        except Exception:
            pass


def object_of(proxy):
    """The document object a ConfigRef *proxy* belongs to (or None).

    FreeCAD hands the property-editor hook `editProperty` only the property
    name, so the proxy has to find its own object. Storing the object on the
    proxy is not the way here: a proxy that carries FreeCAD's ``__object__``
    attribute is called *without* the object by every FeaturePython callback
    (`FeaturePythonImp` picks the signature from that attribute), which would
    change `execute`/`onChanged` for the whole add-on. A stored attribute would
    have to be re-established after a reload as well - and a document object is
    not serializable, so it would break saving. Matching the proxy identity is
    exact (FreeCAD gives every object its own proxy instance) and costs one
    walk of the open documents on a click.
    """
    for doc in App.listDocuments().values():
        for obj in doc.Objects:
            if getattr(obj, "Proxy", None) is proxy:
                return obj
    return None


def create(doc, master, configuration: str, name: str = "ConfigRef"):
    """Create and return a ConfigRef object.

    The object is created with `CONTAINER_OBJECT_TYPE` so it can be moved into
    any container FreeCAD offers, including a `PartDesign::Body`.
    """
    doc = doc or App.ActiveDocument
    if doc is None:
        raise ValueError("SpreadSheetPlus: no active document")
    obj = _add_object(doc, name)
    ConfigRef(obj)
    obj.Master = master
    obj.Configuration = configuration
    attach_view_provider(obj)
    obj.recompute()
    return obj


def attach_view_provider(obj) -> None:
    """Give *obj* the ConfigRef tree icon (GUI only)."""
    if not App.GuiUp:
        return
    view = getattr(obj, "ViewObject", None)
    if view is None:
        return
    from .view_providers import ConfigRefViewProvider

    ConfigRefViewProvider(view)


def parent_group(obj):
    """Return the object whose `Group` contains *obj*, if any."""
    doc = getattr(obj, "Document", None)
    if doc is None:
        return None
    for candidate in doc.Objects:
        try:
            if obj in getattr(candidate, "Group", []):
                return candidate
        except Exception:
            continue
    return None


def slot_name(obj) -> str:
    """Name of the container property that selects *obj*'s row."""
    name = getattr(obj, "ConfigurationName", "")
    return name or obj.Name


def _config_refs_in(container) -> list:
    """The ConfigRefs that live directly in *container*."""
    found = []
    try:
        children = list(container.Group)
    except Exception:
        return found
    for child in children:
        if isinstance(getattr(child, "Proxy", None), ConfigRef):
            found.append(child)
    return found


def _registered_slots(container) -> list[str]:
    """The configuration selectors this workbench created on *container*."""
    return list(getattr(container, _SLOT_REGISTRY, ()) or ())


def _selector_items(container, name: str) -> list[str]:
    """The items of a container's selector ([] when it is not an enumeration)."""
    if container.getTypeIdOfProperty(name) != _SELECTOR_TYPE:
        return []
    return list(container.getEnumerationsOfProperty(name) or ())


def _store_slot_value(container, name: str, value: str) -> None:
    """Write *value* to a container's configuration selector.

    A selector is an `App::PropertyEnumeration`, and an enumeration can only
    hold one of its own items: assigning anything else raises. A value the
    selector does not know yet - a row the master does not have, or the empty
    string of a reference that has not picked a row - is therefore added as an
    item instead of being rejected, so writing a selection can neither fail nor
    silently replace the selection with another row. `_sync_slots` drops the
    extra item again on the next recompute, once nothing selects it.

    This is also the write path for the plain string selectors of documents
    written by earlier versions; a string property takes any value.
    """
    if container.getTypeIdOfProperty(name) != _SELECTOR_TYPE:
        setattr(container, name, value)
        return
    items = _selector_items(container, name)
    if value not in items:
        items.append(value)
        setattr(container, name, items)
    if getattr(container, name, None) != value:
        setattr(container, name, value)


def _refresh_slot_items(container, name: str, row: str, configurations) -> None:
    """Offer exactly *configurations* on the selector, and select *row*.

    *row* is kept as an extra item when it is not one of *configurations*: an
    enumeration cannot hold anything but one of its own items, and silently
    moving the selection to another row would change the part behind the user's
    back. That the row does not resolve is reported by the reference's status.
    """
    if container.getTypeIdOfProperty(name) != _SELECTOR_TYPE:
        _store_slot_value(container, name, row)
        return
    items = sorted(configurations, key=str.lower)
    if row not in items:
        items.append(row)
    if items != _selector_items(container, name):
        setattr(container, name, items)
    if getattr(container, name, None) != row:
        setattr(container, name, row)


def _add_selector(container, name: str, obj) -> None:
    """Add the `App::PropertyEnumeration` a container selects rows with."""
    container.addProperty(
        _SELECTOR_TYPE,
        name,
        GROUP,
        f"Selected configuration row of {obj.Label}",
    )


def _convert_selector(container, name: str, obj) -> None:
    """Rebuild the plain string selector of an earlier version as an enumeration.

    FreeCAD cannot change a property's type, so the property is replaced. The
    row it selected is kept, and a link that mirrors the selector copies the new
    type on the next recompute (verified against FreeCAD 1.1).
    """
    row = getattr(container, name, "") or ""
    container.removeProperty(name)
    _add_selector(container, name, obj)
    container.setPropertyStatus(name, "CopyOnChange")
    _store_slot_value(container, name, row)


def _sync_slots(container, obj, configurations=()):
    """Make sure *container* carries a row selector for every ConfigRef in it.

    Returns ``(row, problems)``: the row selected on the container (``None``
    when the container cannot carry a selector for *obj*) and a list of
    human-readable problems.

    The selectors are the object of FreeCAD's ``App::Link`` copy-on-change: they
    carry the ``CopyOnChange`` status, so a link to the part gains one mirror per
    configuration under ``Configuration (<group>)`` in its property editor, and
    a variant inherits the row selected on that link. That is why they live on
    the container and not on the ConfigRef - only the linked object's own
    properties are mirrored.

    Each selector is an `App::PropertyEnumeration` of the rows *configurations*
    (the master's configurations, as the reference sees them now), which is what
    lets the part offer them as a drop-down in the property editor: a Body is a
    C++ object, so it cannot open the reference's picker dialog the way the
    ConfigRef's own ``Configuration`` property can (see the module docstring).
    """
    problems = []
    if not hasattr(container, _SLOT_REGISTRY):
        container.addProperty(
            "App::PropertyStringList",
            _SLOT_REGISTRY,
            GROUP,
            "Configuration selectors created by SpreadSheetPlus",
            hidden=True,
        )

    wanted = {}
    for ref in _config_refs_in(container):
        wanted.setdefault(slot_name(ref), []).append(ref)

    # Forget selectors whose ConfigRef is gone (deleted, renamed or moved out).
    registered = _registered_slots(container)
    keep = [name for name in registered if name in wanted]
    for name in registered:
        if name not in wanted and hasattr(container, name):
            container.removeProperty(name)
            _SLOT_NAMES.discard(name)
    if keep != registered:
        setattr(container, _SLOT_REGISTRY, keep)

    name = slot_name(obj)
    if not name.isidentifier():
        problems.append(f"configuration name is not a valid property name: {name!r}")
        return None, problems
    if len(wanted.get(name, ())) > 1:
        problems.append(
            f"configuration name is used by more than one ConfigRef: {name!r}"
        )
        return None, problems
    if not hasattr(container, name):
        _add_selector(container, name, obj)
        container.setPropertyStatus(name, "CopyOnChange")
        setattr(container, _SLOT_REGISTRY, keep + [name])
        _SLOT_NAMES.add(name)
    elif name not in keep:
        # The property predates us (a name clash on the container): never claim
        # a property this workbench did not create.
        problems.append(
            f"cannot add a {name!r} configuration: {container.Label} already "
            f"has a property with that name"
        )
        return None, problems
    elif container.getTypeIdOfProperty(name) != _SELECTOR_TYPE:
        # A selector written by an earlier version: a plain string back then.
        _convert_selector(container, name, obj)

    # A fresh (or emptied) selector starts from the ConfigRef's selection;
    # otherwise the selector is what the reference follows, so the part and all
    # its variants stay in charge of the row.
    row = getattr(container, name, None) or obj.Configuration or ""
    _refresh_slot_items(container, name, row, configurations)
    return getattr(container, name, None), problems


def row_selector(obj):
    """Return the ``(source, property)`` a row selected for *obj* is written to.

    A ConfigRef inside a container selects through that container's selector -
    the part owns the row, which is what `App::Link` copy-on-change mirrors, so
    a variant can pick its own. A reference outside a part (or one whose name the
    container cannot use) is its own selector.

    Writing *source* is **not** what creates a variant: FreeCAD syncs the change
    into the mirrored property of every link that still follows it, and only a
    change on the link itself makes that link diverge (see
    `variants.variant_links`).
    """
    container = parent_group(obj)
    name = slot_name(obj)
    if container is not None and name in _registered_slots(container):
        return container, name
    return obj, "Configuration"


def switch_configuration(obj, row: str) -> None:
    """Select *row* for *obj*, through the part's selector when it has one.

    Writing the part's selector marks *obj* for recompute explicitly, because a
    container property change does not re-execute its children - this route has
    to work whether or not `variants.VariantObserver` is attached.
    """
    source, name = row_selector(obj)
    if source is obj:
        obj.Configuration = row
        return
    _store_slot_value(source, name, row)
    obj.touch()


def _expressions_of(obj):
    """Yield ``(property, expression)`` pairs defined on *obj*."""
    try:
        engine = obj.ExpressionEngine
    except Exception:
        return
    for entry in engine or []:
        try:
            yield entry[0], entry[1]
        except Exception:
            continue


def _expressions_mentioning(doc, name: str, label: str = ""):
    """Collect expressions that mention *name* or *label*.

    Entries are ``(object, property, expression)`` tuples, collected *before*
    the old object is deleted: FreeCAD drops expressions that point at an object
    which is removed, so they cannot be recovered afterwards.

    Note that FreeCAD's ``<<...>>`` syntax refers to an object's **label**,
    while ``Name.Property`` uses the internal name, so both spellings are
    matched here.
    """
    found = []
    for candidate in doc.Objects:
        for prop, expression in _expressions_of(candidate):
            if name in expression or (label and label in expression):
                found.append((candidate, prop, expression))
    return found


def _reapply_expressions(references) -> None:
    """Set the collected expressions again, forcing a fresh parse."""
    for target, prop, expression in references:
        try:
            target.clearExpression(prop)
            target.setExpression(prop, expression)
        except Exception as exc:
            App.Console.PrintWarning(
                f"SpreadSheetPlus: could not re-apply expression {expression!r} on "
                f"{target.Name}.{prop}: {exc}\n"
            )


def convert_to_container_type(obj):
    """Rebuild a legacy ConfigRef as a container-friendly object.

    ConfigRefs created by earlier versions are `App::FeaturePython` objects,
    which FreeCAD refuses to drop into a `PartDesign::Body`. FreeCAD cannot
    change an object's type, so the object is rebuilt under the **same name**
    (so expressions referring to it, by name or by label, keep resolving) and
    put back into the container it lived in.

    Returns the new object, or *obj* unchanged when it already has a type that
    containers accept.
    """
    doc = getattr(obj, "Document", None)
    if doc is None:
        raise ValueError("SpreadSheetPlus: object is not part of a document")
    if obj.TypeId == CONTAINER_OBJECT_TYPE:
        return obj

    name = obj.Name
    label = obj.Label
    master = getattr(obj, "Master", None)
    configuration = getattr(obj, "Configuration", "")
    container = parent_group(obj)
    # Expressions that use this reference are dropped when it is deleted, so
    # remember them and put them back on the rebuilt object.
    references = _expressions_mentioning(doc, name, label)

    doc.openTransaction("Convert ConfigRef")
    try:
        doc.removeObject(name)
        new_obj = _add_object(doc, name, CONTAINER_OBJECT_TYPE)
        proxy = ConfigRef(new_obj)
        if master is not None:
            new_obj.Master = master
        new_obj.Configuration = configuration
        new_obj.Label = label
        if container is not None:
            container.addObject(new_obj)
        attach_view_provider(new_obj)
        # Build the parameter properties before anything else recomputes:
        # expressions elsewhere in the document refer to them by name, and an
        # evaluation that fails (property not there yet) would stay disabled.
        proxy.execute(new_obj)
        _reapply_expressions(references)
        doc.recompute()
    except Exception:
        doc.abortTransaction()
        raise
    doc.commitTransaction()
    return new_obj


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
