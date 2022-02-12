# Copyright (c) MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QListWidget,
    QRadioButton,
)

from .utils import select_all


class PickChannelsDialog(QDialog):
    def __init__(self, parent, channels, types):
        super().__init__(parent)
        self.setWindowTitle("Pick channels")

        grid = QGridLayout(self)

        self.by_name = QRadioButton("By name:")
        grid.addWidget(self.by_name, 0, 0, Qt.AlignTop)
        self.names = QListWidget()
        self.names.insertItems(0, channels)
        self.names.setSelectionMode(QListWidget.ExtendedSelection)
        select_all(self.names)
        grid.addWidget(self.names, 0, 1)
        self.by_name.setChecked(True)

        self.by_type = QRadioButton("By type:")
        grid.addWidget(self.by_type, 1, 0, Qt.AlignTop)
        self.types = QListWidget()
        self.types.insertItems(0, types)
        self.types.setSelectionMode(QListWidget.ExtendedSelection)
        self.types.setMaximumHeight(self.types.sizeHintForRow(0) * 5.5)
        select_all(self.types)
        grid.addWidget(self.types, 1, 1)

        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        grid.addWidget(self.buttonbox, 2, 0, 1, -1)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)
        self.types.itemSelectionChanged.connect(self.toggle_buttons)
        self.names.itemSelectionChanged.connect(self.toggle_buttons)
        self.by_name.toggled.connect(self.toggle_buttons)
        self.toggle_buttons()  # initialize OK button state

        self.by_name.toggled.connect(self.toggle_lists)
        self.by_type.toggled.connect(self.toggle_lists)
        self.toggle_lists()

    @Slot()
    def toggle_buttons(self):
        """Toggle OK button."""
        self.buttonbox.button(QDialogButtonBox.Ok).setEnabled(False)
        if (self.by_name.isChecked() and self.names.selectedItems()
                or self.by_type.isChecked() and self.types.selectedItems()):
            self.buttonbox.button(QDialogButtonBox.Ok).setEnabled(True)

    @Slot()
    def toggle_lists(self):
        self.names.setEnabled(self.by_name.isChecked())
        self.types.setEnabled(not self.by_name.isChecked())
