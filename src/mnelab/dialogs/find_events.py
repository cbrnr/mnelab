# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)

from mnelab.widgets import FlatSpinBox

MAX_INT = 2147483647
DEFAULT_MASK = 2**16 - 1


class FindEventsDialog(QDialog):
    def __init__(self, parent, channels, default_stim, mask_enabled=False):
        super().__init__(parent)
        self.setWindowTitle("Find Events")
        vbox = QVBoxLayout(self)
        grid = QGridLayout()

        grid.addWidget(QLabel("Stim channel:"), 0, 0)
        self.stimchan = QComboBox()
        self.stimchan.addItems(channels)
        self.stimchan.setCurrentIndex(default_stim)
        grid.addWidget(self.stimchan, 0, 1)

        grid.addWidget(QLabel("Consecutive"), 1, 0)
        self.consecutive = QComboBox()
        self.consecutive.addItems(["Increasing", "True", "False"])
        self.consecutive.setCurrentIndex(0)
        grid.addWidget(self.consecutive, 1, 1)

        grid.addWidget(QLabel("Initial event"), 2, 0)
        self.initial_event = QCheckBox()
        self.initial_event.setChecked(False)
        grid.addWidget(self.initial_event, 2, 1)

        grid.addWidget(QLabel("Mask:"), 3, 0)
        mask_hbox = QHBoxLayout()
        self.mask_enabled = QCheckBox()
        self.mask_enabled.setChecked(mask_enabled)
        mask_hbox.addWidget(self.mask_enabled)
        self.mask_value = FlatSpinBox()
        self.mask_value.setMinimum(0)
        self.mask_value.setMaximum(MAX_INT)
        self.mask_value.setValue(DEFAULT_MASK)
        self.mask_value.setAlignment(Qt.AlignRight)
        self.mask_value.setEnabled(mask_enabled)
        mask_hbox.addWidget(self.mask_value)
        self.mask_bits_label = QLabel()
        self.mask_bits_label.setFont(QFontDatabase.systemFont(QFontDatabase.FixedFont))
        self._update_mask_bits_label(DEFAULT_MASK)
        self.mask_bits_label.setEnabled(mask_enabled)
        mask_hbox.addWidget(self.mask_bits_label)
        mask_hbox.addStretch()
        grid.addLayout(mask_hbox, 3, 1)
        self.mask_enabled.toggled.connect(self._on_mask_toggled)
        self.mask_value.valueChanged.connect(self._update_mask_bits_label)

        grid.addWidget(QLabel("Minimum duration:"), 4, 0)
        self.minduredit = FlatSpinBox()
        self.minduredit.setMaximum(MAX_INT)
        self.minduredit.setAlignment(Qt.AlignRight)
        grid.addWidget(self.minduredit, 4, 1)

        grid.addWidget(QLabel("Shortest event:"), 5, 0)
        self.shortesteventedit = FlatSpinBox()
        self.shortesteventedit.setValue(2)
        self.shortesteventedit.setMaximum(MAX_INT)
        self.shortesteventedit.setAlignment(Qt.AlignRight)

        grid.addWidget(self.shortesteventedit, 5, 1)

        vbox.addLayout(grid)
        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        vbox.addWidget(buttonbox)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        vbox.setSizeConstraint(QVBoxLayout.SetFixedSize)
        self.setFocus()

    def _on_mask_toggled(self, checked):
        self.mask_value.setEnabled(checked)
        self.mask_bits_label.setEnabled(checked)

    def _update_mask_bits_label(self, value):
        bits = format(value, "032b")
        self.mask_bits_label.setText(f"{bits[:16]}\n{bits[16:]}")
