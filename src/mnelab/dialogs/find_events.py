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

from mnelab.widgets import FlatSpinBox, set_tooltip

MAX_INT = 2147483647
DEFAULT_MASK = 2**16 - 1


class FindEventsDialog(QDialog):
    def __init__(self, parent, channels, default_stim, mask_enabled=False):
        super().__init__(parent)
        self.setWindowTitle("Find Events")
        vbox = QVBoxLayout(self)
        grid = QGridLayout()

        stim_label = QLabel("Stim Channel:")
        self.stimchan = QComboBox()
        self.stimchan.addItems(channels)
        self.stimchan.setCurrentIndex(default_stim)
        set_tooltip(
            "Choose the channel containing trigger values", stim_label, self.stimchan
        )
        grid.addWidget(stim_label, 0, 0)
        grid.addWidget(self.stimchan, 0, 1)

        consecutive_label = QLabel("Consecutive:")
        self.consecutive = QComboBox()
        self.consecutive.addItems(["Increasing", "True", "False"])
        self.consecutive.setCurrentIndex(0)
        set_tooltip(
            '"Increasing" detects adjacent events only when the value increases; '
            '"True" detects every change; "False" detects changes to or from zero',
            consecutive_label,
            self.consecutive,
        )
        grid.addWidget(consecutive_label, 1, 0)
        grid.addWidget(self.consecutive, 1, 1)

        initial_event_label = QLabel("Initial Event:")
        self.initial_event = QCheckBox()
        self.initial_event.setChecked(False)
        set_tooltip(
            "Create an event when the first sample has a nonzero trigger value",
            initial_event_label,
            self.initial_event,
        )
        grid.addWidget(initial_event_label, 2, 0)
        grid.addWidget(self.initial_event, 2, 1)

        mask_label = QLabel("Mask:")
        mask_hbox = QHBoxLayout()
        self.mask_enabled = QCheckBox()
        self.mask_enabled.setChecked(mask_enabled)
        set_tooltip(
            "Apply a bitwise mask to trigger values", mask_label, self.mask_enabled
        )
        mask_hbox.addWidget(self.mask_enabled)
        self.mask_value = FlatSpinBox()
        self.mask_value.setMinimum(0)
        self.mask_value.setMaximum(MAX_INT)
        self.mask_value.setValue(DEFAULT_MASK)
        self.mask_value.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.mask_value.setEnabled(mask_enabled)
        set_tooltip("Set the bitwise mask applied to trigger values", self.mask_value)
        mask_hbox.addWidget(self.mask_value)
        self.mask_bits_label = QLabel()
        self.mask_bits_label.setFont(
            QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        )
        self._update_mask_bits_label(DEFAULT_MASK)
        self.mask_bits_label.setEnabled(mask_enabled)
        mask_hbox.addWidget(self.mask_bits_label)
        mask_hbox.addStretch()
        grid.addWidget(mask_label, 3, 0)
        grid.addLayout(mask_hbox, 3, 1)
        self.mask_enabled.toggled.connect(self._on_mask_toggled)
        self.mask_value.valueChanged.connect(self._update_mask_bits_label)

        min_duration_label = QLabel("Minimum Duration:")
        self.minduredit = FlatSpinBox()
        self.minduredit.setMaximum(MAX_INT)
        self.minduredit.setAlignment(Qt.AlignmentFlag.AlignRight)
        set_tooltip(
            "Ignore trigger changes shorter than this duration in seconds",
            min_duration_label,
            self.minduredit,
        )
        grid.addWidget(min_duration_label, 4, 0)
        grid.addWidget(self.minduredit, 4, 1)

        shortest_event_label = QLabel("Shortest Event:")
        self.shortesteventedit = FlatSpinBox()
        self.shortesteventedit.setValue(2)
        self.shortesteventedit.setMaximum(MAX_INT)
        self.shortesteventedit.setAlignment(Qt.AlignmentFlag.AlignRight)
        set_tooltip(
            "Require events to last at least this many samples",
            shortest_event_label,
            self.shortesteventedit,
        )

        grid.addWidget(shortest_event_label, 5, 0)
        grid.addWidget(self.shortesteventedit, 5, 1)

        vbox.addLayout(grid)
        buttonbox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        vbox.addWidget(buttonbox)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        vbox.setSizeConstraint(QVBoxLayout.SizeConstraint.SetFixedSize)
        self.setFocus()

    def _on_mask_toggled(self, checked):
        self.mask_value.setEnabled(checked)
        self.mask_bits_label.setEnabled(checked)

    def _update_mask_bits_label(self, value):
        bits = format(value, "032b")
        self.mask_bits_label.setText(f"{bits[:16]}\n{bits[16:]}")
