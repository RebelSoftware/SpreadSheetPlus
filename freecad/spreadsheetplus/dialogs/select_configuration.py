# SPDX-License-Identifier: LGPL-2.1-or-later
"""Picking a configuration row: the picker dialog and the flow around it.

`choose_configuration()` is what the *Switch configuration* command and the
ConfigRef's `Configuration` property editor button both call, so the two stay
identical.
"""

from __future__ import annotations

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtWidgets

from ..i18n import translate


def choose_configuration(ref, parent=None) -> bool:
    """Let the user pick a configuration row for *ref* and select it.

    Returns True when a row was chosen. This is the shared implementation of
    the *Switch configuration* command and of the ConfigRef property editor
    button, so both offer exactly the same list and the same case-insensitive
    search (see `config_ref.ConfigRef.editProperty`).
    """
    # Imported here rather than at module level: `master_sheet` drags in table
    # parsing, which is not worth loading just to build a dialog.
    from ..config_ref import row_selector, switch_configuration
    from ..master_sheet import MasterSheet

    master = getattr(ref, "Master", None)
    if master is None:
        return False

    dialog = SelectConfigurationDialog(
        MasterSheet(master).configurations(),
        ref.Configuration,
        parent if parent is not None else Gui.getMainWindow(),
    )
    if not dialog.exec():
        return False
    choice = dialog.selected()
    if not choice:
        return False

    switch_configuration(ref, choice)
    hint = _following_link_hint(ref)
    if hint:
        App.Console.PrintMessage(hint)
    ref.Document.recompute()
    return True


def _following_link_hint(ref) -> str | None:
    """The line to report after a switch, or None when no link follows *ref*.

    A switch here changes the *part* - the reference's container, or the
    reference itself. FreeCAD copies a link into an independent variant only when
    one of the link's *own* mirrored properties changes; a change on the part is
    synced into the mirror instead. So the links that still follow the part
    follow this switch as well, and the row of a variant has to be set on the
    link. Nobody guesses that, so it is worth a line in the report view.
    """
    from ..config_ref import row_selector
    from ..variants import variant_links

    source, name = row_selector(ref)
    linked = variant_links(source, name)
    if not linked:
        return None
    labels = ", ".join(sorted(link.Label for link in linked))
    return translate(
        "SpreadSheetPlus",
        "{} is linked by {} (copy on change): they follow the part's "
        "configuration. Change the row on the link itself to give a variant its "
        "own configuration.\n",
    ).format(source.Label, labels)


class SelectConfigurationDialog(QtWidgets.QDialog):
    """Pick a configuration from a sorted, searchable list.

    The list is sorted alphabetically (by lower-case name) regardless of the
    order of the rows in the sheet, and the search box filters case-insensitively.
    """

    def __init__(self, configurations, current: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(translate("SpreadSheetPlus", "Switch configuration"))
        self.setModal(True)
        self.resize(320, 400)
        self._names = sorted(configurations, key=str.lower)

        layout = QtWidgets.QVBoxLayout(self)

        self.search = QtWidgets.QLineEdit(self)
        self.search.setPlaceholderText(translate("SpreadSheetPlus", "Type to search…"))
        self.search.setClearButtonEnabled(True)
        layout.addWidget(self.search)

        self.list = QtWidgets.QListWidget(self)
        for name in self._names:
            self.list.addItem(name)
        layout.addWidget(self.list)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.search.textChanged.connect(self._filter)
        self.search.returnPressed.connect(self.accept)
        self.list.itemDoubleClicked.connect(self.accept)

        self._select_current(current)
        self._filter("")
        self.search.setFocus()

    def _select_current(self, current: str) -> None:
        if not current:
            return
        for row in range(self.list.count()):
            item = self.list.item(row)
            if item.text().lower() == current.lower():
                self.list.setCurrentItem(item)
                return

    def _filter(self, text: str) -> None:
        needle = text.strip().lower()
        for row in range(self.list.count()):
            item = self.list.item(row)
            item.setHidden(needle not in item.text().lower())

    def selected(self) -> str | None:
        """Return the chosen configuration name, or None if nothing is selected."""
        item = self.list.currentItem()
        if item is not None and not item.isHidden():
            return item.text()
        for row in range(self.list.count()):
            candidate = self.list.item(row)
            if not candidate.isHidden():
                return candidate.text()
        return None
