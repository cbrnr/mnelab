# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QGridLayout,
    QLabel,
    QVBoxLayout,
)


class PSDDialog(QDialog):
    def __init__(self, parent, fmin, fmax, montage):
        super().__init__(parent)
        self.setWindowTitle("Power Spectral Density")

        vbox = QVBoxLayout(self)
        grid = QGridLayout()

        fmin_label = QLabel("Lower frequency (Hz):")
        self.fmin_input = QDoubleSpinBox()
        self.fmin_input.setMinimum(0)
        self.fmin_input.setDecimals(1)
        self.fmin_input.setValue(fmin)
        self.fmin_input.setSingleStep(1)
        self.fmin_input.setMaximum(fmax)
        self.fmin_input.setAlignment(Qt.AlignRight)
        grid.addWidget(fmin_label, 0, 0)
        grid.addWidget(self.fmin_input, 0, 1)

        fmax_label = QLabel("Upper frequency (Hz):")
        self.fmax_input = QDoubleSpinBox()
        self.fmax_input.setMinimum(0)
        self.fmax_input.setDecimals(1)
        self.fmax_input.setValue(60)
        self.fmax_input.setSingleStep(1)
        self.fmax_input.setMaximum(fmax)
        self.fmax_input.setAlignment(Qt.AlignRight)
        grid.addWidget(fmax_label, 1, 0)
        grid.addWidget(self.fmax_input, 1, 1)

        bad_label = QLabel("Include bad channels:")
        self.bad_checkbox = QCheckBox()
        self.bad_checkbox.setChecked(True)
        grid.addWidget(bad_label, 2, 0)
        grid.addWidget(self.bad_checkbox, 2, 1)

        color_label = QLabel("Use spatial colors:")
        self.color_checkbox = QCheckBox()
        self.color_checkbox.setChecked(True)
        grid.addWidget(color_label, 3, 0)
        grid.addWidget(self.color_checkbox, 3, 1)
        if not montage:
            color_label.setEnabled(False)
            self.color_checkbox.setEnabled(False)
            self.color_checkbox.setChecked(False)

        vbox.addLayout(grid)

        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        vbox.addWidget(self.buttonbox)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)

        self.fmin_input.valueChanged.connect(self.fmax_input.setMinimum)
        self.fmax_input.valueChanged.connect(self.fmin_input.setMaximum)

    @property
    def fmin(self):
        """Get the lower frequency limit."""
        return self.fmin_input.value()

    @property
    def fmax(self):
        """Get the upper frequency limit."""
        return self.fmax_input.value()

    @property
    def exclude(self):
        """Check if bad channels should be excluded."""
        if self.bad_checkbox.isChecked():
            return ()
        else:
            return "bads"

    @property
    def spatial_colors(self):
        """Check if spatial colors should be used."""
        return self.color_checkbox.isChecked()
