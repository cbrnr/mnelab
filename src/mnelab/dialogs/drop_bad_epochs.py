# © MNELAB developers
#
# License: BSD (3-clause)

from mne.channels.channels import _unit2human
from mne.io import get_channel_type_constants
from PySide6.QtCore import QRegularExpression, Slot
from PySide6.QtGui import QRegularExpressionValidator
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

        decimal_re = QRegularExpression(r"^\d*\.?\d*$")
        decimal_validator = QRegularExpressionValidator(decimal_re, self)

        for row, type in enumerate(types):
            reject_grid.addWidget(QLabel(_label(type)), row, 0)
            self.reject_fields[type] = QLineEdit()
            self.reject_fields[type].setValidator(decimal_validator)
            self.reject_fields[type].textChanged.connect(self.toggle_ok)
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
            self.flat_fields[type].setValidator(decimal_validator)
            self.flat_fields[type].textChanged.connect(self.toggle_ok)
            flat_grid.addWidget(self.flat_fields[type], row, 1)
        self.flat_box.setLayout(flat_grid)
        vbox.addWidget(self.flat_box)

        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        vbox.addWidget(self.buttonbox)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)
        self.flat_box.toggled.connect(self.toggle_ok)
        self.reject_box.toggled.connect(self.toggle_ok)
        self.toggle_ok()
        vbox.setSizeConstraint(QGridLayout.SetFixedSize)

    @Slot()
    def toggle_ok(self):
        ok_btn = self.buttonbox.button(QDialogButtonBox.Ok)
        ok_btn.setEnabled(False)

        # require at least one group checked
        if not (self.reject_box.isChecked() or self.flat_box.isChecked()):
            return

        # for a checked group, require at least one field to be non-empty
        def any_field_filled(fields):
            return any(w.text().strip() != "" for w in fields.values())

        # enable OK only if each checked group has at least one value
        if self.reject_box.isChecked() and not any_field_filled(self.reject_fields):
            return
        if self.flat_box.isChecked() and not any_field_filled(self.flat_fields):
            return

        ok_btn.setEnabled(True)
