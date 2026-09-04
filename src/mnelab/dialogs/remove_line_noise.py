# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QLabel,
    QVBoxLayout,
)

from mnelab.widgets import FlatDoubleSpinBox, set_tooltip


class RemoveLineNoiseDialog(QDialog):
    """Configure line-noise removal."""

    def __init__(self, parent=None, sfreq=None):
        super().__init__(parent)
        self.setWindowTitle("Remove Line Noise")
        vbox = QVBoxLayout(self)

        grid = QGridLayout()
        self._nyquist = None if sfreq is None else sfreq / 2
        maximum_frequency = (
            1_000_000 if self._nyquist is None else max(0.1, self._nyquist - 0.01)
        )

        line_frequency_label = QLabel("Line Frequency (Hz):")
        self._line_frequency = FlatDoubleSpinBox()
        self._line_frequency.setRange(0.1, maximum_frequency)
        self._line_frequency.setDecimals(2)
        self._line_frequency.setSingleStep(0.5)
        self._line_frequency.setValue(min(50, maximum_frequency))
        self._line_frequency.setAlignment(Qt.AlignmentFlag.AlignRight)
        set_tooltip(
            "Set the fundamental frequency of the electrical line noise",
            line_frequency_label,
            self._line_frequency,
        )
        grid.addWidget(line_frequency_label, 0, 0)
        grid.addWidget(self._line_frequency, 0, 1)

        harmonics_label = QLabel("Include Harmonics:")
        self.include_harmonics = QCheckBox()
        self.include_harmonics.setChecked(True)
        set_tooltip(
            "Remove all harmonics below the Nyquist frequency",
            harmonics_label,
            self.include_harmonics,
        )
        grid.addWidget(harmonics_label, 1, 0)
        grid.addWidget(self.include_harmonics, 1, 1)
        vbox.addLayout(grid)

        note = QLabel(
            "<i>Line noise is removed by estimating and subtracting fitted "
            "sinusoids in overlapping windows.</i>"
        )
        note.setWordWrap(True)
        note.setMinimumWidth(400)
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
    def line_frequency(self):
        """Return the selected line-noise frequency."""
        return float(self._line_frequency.value())
