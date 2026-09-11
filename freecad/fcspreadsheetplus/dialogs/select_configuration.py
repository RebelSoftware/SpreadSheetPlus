# SPDX-License-Identifier: LGPL-2.1-or-later
"""Dialog for picking a configuration row (sorted, case-insensitive search)."""

from __future__ import annotations

from PySide6 import QtWidgets


class SelectConfigurationDialog(QtWidgets.QDialog):
    """Pick a configuration from a sorted, searchable list.

    The list is sorted alphabetically (by lower-case name) regardless of the
    order of the rows in the sheet, and the search box filters case-insensitively.
    """

    def __init__(self, configurations, current: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Switch configuration")
        self.setModal(True)
        self.resize(320, 400)
        self._names = sorted(configurations, key=str.lower)

        layout = QtWidgets.QVBoxLayout(self)

        self.search = QtWidgets.QLineEdit(self)
        self.search.setPlaceholderText("Type to search…")
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
