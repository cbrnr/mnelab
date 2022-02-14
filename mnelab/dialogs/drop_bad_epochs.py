# Copyright (c) MNELAB developers
#
# License: BSD (3-clause)

from mne.channels.channels import _unit2human
from mne.io.pick import get_channel_type_constants
from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)


def _label(channel_type):
    label = channel_type.upper()
    try:
        unit = _unit2human[get_channel_type_constants()[channel_type]["unit"]]
        label += f" ({unit})"
    except KeyError:
        pass
    return label


class DropBadEpochsDialog(QDialog):
    def __init__(self, parent, types):
        super().__init__(parent)
        self.setWindowTitle("Drop bad epochs")

        vbox = QVBoxLayout(self)

        self.reject_box = QGroupBox("Reject (maximum PTP amplitude)")
        self.reject_box.setCheckable(True)
        self.reject_box.setChecked(False)
        self.reject_fields = {}
        reject_grid = QGridLayout()
        for row, type in enumerate(types):
            reject_grid.addWidget(QLabel(_label(type)), row, 0)
            self.reject_fields[type] = QLineEdit()
            reject_grid.addWidget(self.reject_fields[type], row, 1)
        self.reject_box.setLayout(reject_grid)
        vbox.addWidget(self.reject_box)

        self.flat_box = QGroupBox("Flat (minimum PTP amplitude)")
        self.flat_box.setCheckable(True)
        self.flat_box.setChecked(False)
        self.flat_fields = {}
        flat_grid = QGridLayout()
        for row, type in enumerate(types):
            flat_grid.addWidget(QLabel(_label(type)), row, 0)
            self.flat_fields[type] = QLineEdit()
            flat_grid.addWidget(self.flat_fields[type], row, 1)
        self.flat_box.setLayout(flat_grid)
        vbox.addWidget(self.flat_box)

        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        vbox.addWidget(self.buttonbox)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)
        self.flat_box.toggled.connect(self.toggle_ok)
        self.reject_box.toggled.connect(self.toggle_ok)
        vbox.setSizeConstraint(QGridLayout.SetFixedSize)

    @Slot()
    def toggle_ok(self):
        self.buttonbox.button(QDialogButtonBox.Ok).setEnabled(False)
        if self.reject_box.isChecked() or self.flat_box.isChecked():
            self.buttonbox.button(QDialogButtonBox.Ok).setEnabled(True)
