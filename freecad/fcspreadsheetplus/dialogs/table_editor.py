# SPDX-License-Identifier: LGPL-2.1-or-later
"""Qt dialog for editing a configuration table.

Parameters are shown as columns; configurations as rows. Cell edits are written
back through the MasterSheet API (which recomputes after each write).
"""

from __future__ import annotations

from PySide6 import QtWidgets

from ..master_sheet import MasterSheet


class TableEditorDialog(QtWidgets.QDialog):
    """Edit a MasterSheet's configuration table."""

    def __init__(self, master: MasterSheet, parent=None) -> None:
        super().__init__(parent)
        self.master = master
        self.setWindowTitle("Edit configuration table")
        self.setModal(True)
        self._build_ui()
        self._reload()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)

        self.table = QtWidgets.QTableWidget(self)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        self.status = QtWidgets.QLabel(self)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        row_buttons = QtWidgets.QHBoxLayout()
        self.add_config_btn = QtWidgets.QPushButton("Add configuration", self)
        self.remove_config_btn = QtWidgets.QPushButton("Remove configuration", self)
        self.add_param_btn = QtWidgets.QPushButton("Add parameter", self)
        self.remove_param_btn = QtWidgets.QPushButton("Remove parameter", self)
        for btn in (
            self.add_config_btn,
            self.remove_config_btn,
            self.add_param_btn,
            self.remove_param_btn,
        ):
            row_buttons.addWidget(btn)
        layout.addLayout(row_buttons)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            self,
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.add_config_btn.clicked.connect(self._add_configuration)
        self.remove_config_btn.clicked.connect(self._remove_configuration)
        self.add_param_btn.clicked.connect(self._add_parameter)
        self.remove_param_btn.clicked.connect(self._remove_parameter)

    def _reload(self) -> None:
        params = self.master.parameters()
        configs = self.master.configurations()
        self.table.setColumnCount(len(params))
        self.table.setHorizontalHeaderLabels(params)
        self.table.setRowCount(len(configs))
        self.table.setVerticalHeaderLabels(configs)
        for r, config in enumerate(configs):
            for c, param in enumerate(params):
                item = QtWidgets.QTableWidgetItem(self.master.get_value(config, param))
                self.table.setItem(r, c, item)
        self._refresh_status()

    def _refresh_status(self) -> None:
        problems = self.master.validate()
        if problems:
            self.status.setText("\n".join(problems))
            self.status.setStyleSheet("color: #b00020; font-weight: bold;")
        else:
            self.status.setText("Table OK")
            self.status.setStyleSheet("color: #4caf50;")

    def _write_back(self) -> None:
        params = self.master.parameters()
        configs = self.master.configurations()
        for r, config in enumerate(configs):
            for c, param in enumerate(params):
                item = self.table.item(r, c)
                if item is not None:
                    self.master.set_value(config, param, item.text())

    def _on_accept(self) -> None:
        self._write_back()
        self.accept()

    # -- row / column editing -------------------------------------------
    def _add_configuration(self) -> None:
        name, ok = QtWidgets.QInputDialog.getText(self, "Add configuration", "Configuration name:")
        if ok and name.strip():
            self.master.add_configuration(name.strip())
            self._reload()

    def _remove_configuration(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            return
        config = self.table.verticalHeaderItem(row).text()
        self.master.remove_configuration(config)
        self._reload()

    def _add_parameter(self) -> None:
        name, ok = QtWidgets.QInputDialog.getText(self, "Add parameter", "Parameter name:")
        if ok and name.strip():
            self.master.add_parameter(name.strip())
            self._reload()

    def _remove_parameter(self) -> None:
        col = self.table.currentColumn()
        if col < 0:
            return
        param = self.table.horizontalHeaderItem(col).text()
        self.master.remove_parameter(param)
        self._reload()
