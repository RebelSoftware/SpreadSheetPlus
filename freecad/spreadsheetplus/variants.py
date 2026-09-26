# SPDX-License-Identifier: LGPL-2.1-or-later
"""Part variants: the App::Link "Copy on change" glue.

A part is configured through its *container* - the Body or Part the ConfigRefs
live in - because FreeCAD's ``App::Link`` copy-on-change only mirrors properties
of the object that is linked, never of its children. Each ConfigRef in the part
gets a selector property on it (created by ``config_ref._sync_slots``), marked
``CopyOnChange``, so a link gains one mirror per configuration under
``Configuration (<group>)`` in its property editor and every variant can pick its
own rows.

The selectors are only half of it. When FreeCAD re-configures a variant it
*pastes* the new value into the copy's selector, and nothing else happens: the
copy's own children are not re-executed, and no object inside the part may depend
on the part itself (that is a DAG cycle FreeCAD refuses). A document observer is
the only hook that sees that paste, and it is what makes the copy re-read its
rows - see :class:`VariantObserver`.

A variant is created by changing *the link's* mirrored property, never by
changing the part: FreeCAD's `LinkBaseExtension::setupCopyOnChange` connects to
the source's properties and pastes each change into the link's mirror with the
copy trigger suppressed. `variant_links()` reports the links a part-side change
therefore reaches without copying, so the GUI can say so.
"""

from __future__ import annotations

import FreeCAD as App

from .config_ref import (
    _SLOT_NAMES,
    ConfigRef,
    _config_refs_in,
    _registered_slots,
    _store_slot_value,
    parent_group,
    slot_name,
)

#: ``App.isRestoring`` is not in very old releases; without it the observer can
#: only rely on the fact that a recompute does not run mid-restore.
_is_restoring = getattr(App, "isRestoring", None)

_observer = None


class VariantObserver:
    """Keep every part's configuration selectors and its ConfigRefs in step.

    Two jobs, both driven by property changes:

    * a *selector* changed - the user picked a row on the part, a variant was
      created, or FreeCAD pasted a value into a variant copy: mark that part's
      ConfigRefs for recompute so they re-read their row.
    * a ConfigRef's own ``Configuration`` changed - the Switch configuration
      command, the property editor, or a script: copy it up into the part's
      selector so the part and its future variants follow.

    Both directions only ever make the two values equal, so the pair converges
    without re-entrancy bookkeeping.
    """

    def slotChangedObject(self, obj, prop: str) -> None:
        # Loading a document replays every property of every object; running
        # work then would touch objects that are still being restored.
        if _is_restoring is not None and _is_restoring():
            return

        if prop in _SLOT_NAMES:
            for ref in _config_refs_in(obj):
                if slot_name(ref) == prop:
                    ref.touch()
            return

        if prop != "Configuration":
            return
        if not isinstance(getattr(obj, "Proxy", None), ConfigRef):
            return
        container = parent_group(obj)
        if container is None:
            return
        name = slot_name(obj)
        if name not in _registered_slots(container):
            return
        if getattr(container, name, None) != obj.Configuration:
            _store_slot_value(container, name, obj.Configuration)


def variant_links(source, name: str) -> list:
    """The links that would make an independent variant if *name* changed.

    These are the links that still follow *source* (they have not diverged into
    a copy yet) and mirror *name* with the ``CopyOnChange`` status. FreeCAD
    copies the source into an independent object as soon as one of *their*
    mirrored properties changes, so this is the set to point a user at when a row
    is switched on the part itself: FreeCAD deliberately syncs such a change into
    the mirrors instead, which is why a part-side switch updates every link that
    follows the part and never creates a variant.

    Returns an empty list for a source that has no such links.
    """
    doc = getattr(source, "Document", None)
    found = []
    for candidate in getattr(doc, "Objects", ()):
        # A copy-on-change link points at the source until it diverges; after
        # that its mirrored properties are its own rows, not the part's.
        if getattr(candidate, "LinkedObject", None) is not source:
            continue
        if name not in candidate.PropertiesList:
            continue
        try:
            if "CopyOnChange" in candidate.getPropertyStatus(name):
                found.append(candidate)
        except Exception:
            continue
    return found


def attach() -> None:
    """Attach the variant observer (idempotent)."""
    global _observer
    if _observer is None:
        _observer = VariantObserver()
        App.addDocumentObserver(_observer)


def detach() -> None:
    """Detach the variant observer."""
    global _observer
    if _observer is not None:
        App.removeDocumentObserver(_observer)
        _observer = None
