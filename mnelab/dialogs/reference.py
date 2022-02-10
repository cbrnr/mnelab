# Copyright (c) MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QRadioButton,
    QVBoxLayout,
)


class ReferenceDialog(QDialog):
    def __init__(self, parent, available_channels):
        super().__init__(parent)
        self.setWindowTitle("Change reference")
        vbox = QVBoxLayout(self)

        self.add_group = QGroupBox("Add reference (all zero)")
        self.reref_group = QGroupBox("Re-reference to existing channel(s)")

        vbox.addWidget(self.add_group)
        vbox.addWidget(self.reref_group)

        self.add_group.setCheckable(True)
        self.reref_group.setCheckable(True)

        self.add_group.setChecked(False)

        self.add_channellist = QLineEdit()
        add_grid = QGridLayout()
        add_grid.setColumnStretch(0, 2)
        add_grid.setColumnStretch(1, 3)
        add_grid.addWidget(QLabel("Channel(s):"), 0, 0)
        add_grid.addWidget(self.add_channellist, 0, 1)
        self.add_group.setLayout(add_grid)

        self.reref_average = QRadioButton("Average")
        self.reref_channels = QRadioButton("Channel(s):")
        self.reref_channellist = QListWidget()
        self.reref_channellist.insertItems(0, available_channels)
        self.reref_average.setChecked(True)
        self.reref_channellist.setEnabled(False)
        self.reref_channellist.setSelectionMode(QListWidget.ExtendedSelection)
        reref_grid = QGridLayout()
        reref_grid.setColumnStretch(0, 2)
        reref_grid.setColumnStretch(1, 3)
        reref_grid.addWidget(self.reref_average, 0, 0)
        reref_grid.addWidget(self.reref_channels, 1, 0, alignment=Qt.AlignTop)
        reref_grid.addWidget(self.reref_channellist, 1, 1)

        self.reref_group.setLayout(reref_grid)

        self.reref_channels.toggled.connect(self.toggle_reref_channellist)
        self.add_group.toggled.connect(self.toggle_ok)
        self.add_channellist.textChanged.connect(self.toggle_ok)
        self.reref_group.toggled.connect(self.toggle_ok)
        self.reref_channels.toggled.connect(self.toggle_ok)
        self.reref_channellist.itemSelectionChanged.connect(self.toggle_ok)

        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        vbox.addWidget(self.buttonbox)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)
        vbox.setSizeConstraint(QVBoxLayout.SetFixedSize)

    def toggle_reref_channellist(self):
        self.reref_channellist.setEnabled(self.reref_channels.isChecked())

    def toggle_ok(self):
        if self.add_group.isChecked() and not self.add_channellist.text():
            self.buttonbox.button(QDialogButtonBox.Ok).setEnabled(False)
            return

        if not self.add_group.isChecked() and not self.reref_group.isChecked():
            self.buttonbox.button(QDialogButtonBox.Ok).setEnabled(False)
            return

        if self.reref_group.isChecked() and self.reref_channels.isChecked() and not self.reref_channellist.selectedItems():  # noqa: E501
            self.buttonbox.button(QDialogButtonBox.Ok).setEnabled(False)
            return

        self.buttonbox.button(QDialogButtonBox.Ok).setEnabled(True)
