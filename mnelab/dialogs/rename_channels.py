# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QLineEdit,
    QRadioButton,
    QVBoxLayout,
)


class RenameChannelsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Rename channels")

        self.prefix_group = QGroupBox("Modify prefix")
        self.prefix_group.setCheckable(True)
        self.prefix_group.setChecked(False)

        self.prefix_strip = QRadioButton("Strip character(s):")
        self.prefix_strip_chars = QLineEdit()
        self.prefix_strip.setChecked(True)
        self.prefix_slice = QRadioButton("Delete amount:")
        self.prefix_slice_num = QDoubleSpinBox()
        self.prefix_slice_num.setMinimum(0)
        self.prefix_slice_num.setDecimals(0)

        prefix_grid = QGridLayout()
        prefix_grid.addWidget(self.prefix_strip, 0, 0)
        prefix_grid.addWidget(self.prefix_strip_chars, 0, 1)
        prefix_grid.addWidget(self.prefix_slice, 1, 0)
        prefix_grid.addWidget(self.prefix_slice_num, 1, 1)
        self.prefix_group.setLayout(prefix_grid)

        self.suffix_group = QGroupBox("Modify suffix")
        self.suffix_group.setCheckable(True)
        self.suffix_group.setChecked(False)

        self.suffix_strip = QRadioButton("Strip character(s):")
        self.suffix_strip_chars = QLineEdit()
        self.suffix_strip.setChecked(True)
        self.suffix_slice = QRadioButton("Delete amount:")
        self.suffix_slice_num = QDoubleSpinBox()
        self.suffix_slice_num.setMinimum(0)
        self.suffix_slice_num.setDecimals(0)

        suffix_grid = QGridLayout()
        suffix_grid.addWidget(self.suffix_strip, 0, 0)
        suffix_grid.addWidget(self.suffix_strip_chars, 0, 1)
        suffix_grid.addWidget(self.suffix_slice, 1, 0)
        suffix_grid.addWidget(self.suffix_slice_num, 1, 1)
        self.suffix_group.setLayout(suffix_grid)

        vbox = QVBoxLayout(self)
        vbox.addWidget(self.prefix_group)
        vbox.addWidget(self.suffix_group)

        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        vbox.addWidget(self.buttonbox)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)
        self.prefix_slice.toggled.connect(self.toggle_prefix)
        self.suffix_slice.toggled.connect(self.toggle_suffix)
        self.toggle_prefix()
        self.toggle_suffix()
        vbox.setSizeConstraint(QVBoxLayout.SetFixedSize)

    @Slot()
    def toggle_prefix(self):
        slice_on = self.prefix_slice.isChecked()
        self.prefix_slice_num.setEnabled(slice_on)
        self.prefix_strip_chars.setEnabled(not slice_on)

    @Slot()
    def toggle_suffix(self):
        slice_on = self.suffix_slice.isChecked()
        self.suffix_slice_num.setEnabled(slice_on)
        self.suffix_strip_chars.setEnabled(not slice_on)
