# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QLabel,
    QVBoxLayout,
)

from mnelab.widgets import FlatDoubleSpinBox


class ResampleDialog(QDialog):
    def __init__(self, parent, current_sfreq):
        super().__init__(parent)
        self.setWindowTitle("Resample Data")
        vbox = QVBoxLayout(self)

        grid = QGridLayout()
        grid.addWidget(QLabel("Current Sampling Frequency:"), 0, 0)
        current_label = QLabel(f"{current_sfreq:.1f} Hz")
        current_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        grid.addWidget(current_label, 0, 1)

        grid.addWidget(QLabel("New Sampling Frequency:"), 1, 0)
        self._new_sfreq = FlatDoubleSpinBox()
        self._new_sfreq.setMinimum(0.1)
        self._new_sfreq.setMaximum(1_000_000)
        self._new_sfreq.setDecimals(1)
        self._new_sfreq.setSingleStep(1.0)
        self._new_sfreq.setSuffix(" Hz")
        self._new_sfreq.setValue(current_sfreq / 2)
        self._new_sfreq.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._new_sfreq.setMinimumWidth(140)
        grid.addWidget(self._new_sfreq, 1, 1)

        vbox.addLayout(grid)

        note = QLabel(
            "<i>Resampling automatically applies a suitable anti-aliasing filter.</i>"
        )
        note.setMinimumWidth(460)
        vbox.addWidget(note)

        buttonbox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        vbox.addWidget(buttonbox)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        vbox.setSizeConstraint(QVBoxLayout.SizeConstraint.SetFixedSize)
        self.setFocus()

    @property
    def new_sfreq(self):
        return self._new_sfreq.value()
