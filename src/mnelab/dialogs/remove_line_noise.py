# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSlider,
    QVBoxLayout,
)

from mnelab.pipeline import LINE_NOISE_DEFAULTS
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
        self.include_harmonics.setChecked(LINE_NOISE_DEFAULTS["include_harmonics"])
        set_tooltip(
            "Remove all harmonics below the Nyquist frequency",
            harmonics_label,
            self.include_harmonics,
        )
        grid.addWidget(harmonics_label, 1, 0)
        grid.addWidget(self.include_harmonics, 1, 1)
        vbox.addLayout(grid)

        advanced = QGroupBox("Advanced Settings")
        advanced_grid = QGridLayout(advanced)

        window_length_label = QLabel("Window Length (s):")
        self._window_length = FlatDoubleSpinBox()
        self._window_length.setRange(0.1, 1_000_000)
        self._window_length.setDecimals(2)
        self._window_length.setSingleStep(1)
        self._window_length.setValue(LINE_NOISE_DEFAULTS["window_length"])
        self._window_length.setAlignment(Qt.AlignmentFlag.AlignRight)
        set_tooltip(
            "Duration of the windows in which line noise is fitted (shorter windows "
            "follow faster changes but also remove more signal close to the line "
            "frequencies)",
            window_length_label,
            self._window_length,
        )
        advanced_grid.addWidget(window_length_label, 0, 0)
        advanced_grid.addWidget(self._window_length, 0, 1)

        overlap_label = QLabel("Overlap:")
        self._overlap = QSlider(Qt.Orientation.Horizontal)
        self._overlap.setRange(0, 95)  # percent
        self._overlap.setSingleStep(5)
        self._overlap.setPageStep(10)
        self._overlap.setValue(round(LINE_NOISE_DEFAULTS["overlap"] * 100))
        self._overlap_value = QLabel()
        self._overlap_value.setMinimumWidth(
            self._overlap_value.fontMetrics().horizontalAdvance("100 %")
        )
        self._overlap_value.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._overlap.valueChanged.connect(
            lambda value: self._overlap_value.setText(f"{value} %")
        )
        self._overlap_value.setText(f"{self._overlap.value()} %")
        set_tooltip(
            "Overlap between successive windows",
            overlap_label,
            self._overlap,
            self._overlap_value,
        )
        overlap_box = QHBoxLayout()
        overlap_box.addWidget(self._overlap)
        overlap_box.addWidget(self._overlap_value)
        advanced_grid.addWidget(overlap_label, 1, 0)
        advanced_grid.addLayout(overlap_box, 1, 1)

        tolerance_label = QLabel("Frequency Tolerance (Hz):")
        self._freq_tolerance = FlatDoubleSpinBox()
        self._freq_tolerance.setRange(0, 1_000_000)
        self._freq_tolerance.setDecimals(2)
        self._freq_tolerance.setSingleStep(0.05)
        self._freq_tolerance.setValue(LINE_NOISE_DEFAULTS["freq_tolerance"])
        self._freq_tolerance.setAlignment(Qt.AlignmentFlag.AlignRight)
        set_tooltip(
            "Maximum deviation of the actual line frequency from its nominal value "
            "(the deviation is estimated separately in every window; set to 0 to fit "
            "only the nominal frequency)",
            tolerance_label,
            self._freq_tolerance,
        )
        advanced_grid.addWidget(tolerance_label, 2, 0)
        advanced_grid.addWidget(self._freq_tolerance, 2, 1)

        skip_label = QLabel("Skip Annotations:")
        self._skip_by_annotation = QLineEdit(
            ", ".join(LINE_NOISE_DEFAULTS["skip_by_annotation"])
        )
        set_tooltip(
            "Comma-separated annotation descriptions (matched at the start, ignoring "
            "case) that mark spans to leave unchanged (leave empty to clean the data "
            "in a single segment)",
            skip_label,
            self._skip_by_annotation,
        )
        advanced_grid.addWidget(skip_label, 3, 0)
        advanced_grid.addWidget(self._skip_by_annotation, 3, 1)
        vbox.addWidget(advanced)

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

    @property
    def parameters(self):
        """Return the selected options as keyword arguments for the model."""
        skip = [
            item.strip()
            for item in self._skip_by_annotation.text().split(",")
            if item.strip()
        ]
        return {
            "line_freq": self.line_frequency,
            "include_harmonics": self.include_harmonics.isChecked(),
            "window_length": float(self._window_length.value()),
            "overlap": self._overlap.value() / 100,
            "freq_tolerance": float(self._freq_tolerance.value()),
            "skip_by_annotation": skip,
        }
