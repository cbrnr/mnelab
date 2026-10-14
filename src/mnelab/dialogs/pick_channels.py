# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QRadioButton,
)

from mnelab.widgets import CheckListWidget


class PickChannelsDialog(QDialog):
    def __init__(self, parent, channels, types):
        super().__init__(parent)
        self.setWindowTitle("Pick Channels")

        grid = QGridLayout(self)

        self.by_name = QRadioButton("By Name:")
        self.by_name.setToolTip("Pick individual channels by name")
        grid.addWidget(self.by_name, 0, 0, Qt.AlignmentFlag.AlignTop)
        self.names = CheckListWidget(channels, "Channel", "channels")
        grid.addWidget(self.names, 0, 1)
        self.by_name.setChecked(True)

        self.by_type = QRadioButton("By Type:")
        self.by_type.setToolTip("Pick channels by their type")
        grid.addWidget(self.by_type, 1, 0, Qt.AlignmentFlag.AlignTop)
        self.types = CheckListWidget(types, "Type", "channel types")
        self.types.set_max_visible_rows(3.5)
        grid.addWidget(self.types, 1, 1)

        self.buttonbox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        grid.addWidget(self.buttonbox, 2, 0, 1, -1)
        grid.setRowStretch(0, 1)  # give most of the space to the channel names
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)
        self.types.checks_changed.connect(self.toggle_buttons)
        self.names.checks_changed.connect(self.toggle_buttons)
        self.by_name.toggled.connect(self.toggle_buttons)
        self.toggle_buttons()  # initialize OK button state

        self.by_name.toggled.connect(self.toggle_lists)
        self.by_type.toggled.connect(self.toggle_lists)
        self.toggle_lists()
        self.setMinimumWidth(400)
        self.resize(400, 540)
        self.setFocus()

    @Slot()
    def toggle_buttons(self):
        """Toggle OK button."""
        self.buttonbox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        if (
            self.by_name.isChecked()
            and self.names.checked_rows()
            or self.by_type.isChecked()
            and self.types.checked_rows()
        ):
            self.buttonbox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)

    @Slot()
    def toggle_lists(self):
        self.names.setEnabled(self.by_name.isChecked())
        self.types.setEnabled(not self.by_name.isChecked())
