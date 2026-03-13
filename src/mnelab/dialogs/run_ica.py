# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QLabel,
    QVBoxLayout,
)

from mnelab.widgets import FlatSpinBox


class RunICADialog(QDialog):
    def __init__(self, parent, nchan, highpass, methods):
        super().__init__(parent)
        self.setWindowTitle("Run ICA")

        vbox = QVBoxLayout(self)

        grid = QGridLayout()
        grid.addWidget(QLabel("Method:"), 0, 0)
        self.method = QComboBox()
        self.method.addItems(methods)
        self.method.setCurrentIndex(0)
        self.method.currentIndexChanged.connect(self.toggle_options)
        grid.addWidget(self.method, 0, 1)

        self.extended_label = QLabel("Extended:")
        grid.addWidget(self.extended_label, 1, 0)
        self.extended = QCheckBox()
        self.extended.setChecked(True)
        grid.addWidget(self.extended, 1, 1)

        self.ortho_label = QLabel("Orthogonal:")
        grid.addWidget(self.ortho_label, 2, 0)
        self.ortho = QCheckBox()
        self.ortho.setChecked(False)
        grid.addWidget(self.ortho, 2, 1)
        if "Picard" not in methods:
            self.ortho_label.hide()
            self.ortho.hide()

        grid.addWidget(QLabel("Number of components:"), 3, 0)
        self.n_components = FlatSpinBox()
        self.n_components.setRange(0, nchan)
        self.n_components.setValue(nchan)
        self.n_components.setAlignment(Qt.AlignmentFlag.AlignRight)
        grid.addWidget(self.n_components, 3, 1)

        grid.addWidget(QLabel("Exclude bad segments:"), 4, 0)
        self.exclude_bad_segments = QCheckBox()
        self.exclude_bad_segments.setChecked(True)
        grid.addWidget(self.exclude_bad_segments, 4, 1)

        vbox.addLayout(grid)

        if highpass > 0:
            hp_label = QLabel(
                "<i>High-pass filtering before ICA is essential "
                f"({highpass:.1f} Hz high-pass filter detected).</i>"
            )
        else:
            hp_label = QLabel(
                "<i>High-pass filtering before ICA is essential "
                "(no high-pass filter detected).</i>"
            )
            hp_label.setStyleSheet("color: #d32f2f;")
        hp_label.setWordWrap(True)
        vbox.addWidget(hp_label)

        buttonbox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        vbox.addWidget(buttonbox)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        vbox.setSizeConstraint(QVBoxLayout.SizeConstraint.SetFixedSize)

        self.toggle_options()
        self.setFocus()

    @Slot()
    def toggle_options(self):
        """Toggle extended options."""
        if self.method.currentText() == "Picard":  # enable extended and ortho
            self.extended_label.setEnabled(True)
            self.extended.setEnabled(True)
            self.ortho_label.setEnabled(True)
            self.ortho.setEnabled(True)
        elif self.method.currentText() == "Infomax":  # enable extended
            self.extended_label.setEnabled(True)
            self.extended.setEnabled(True)
            self.ortho_label.setEnabled(False)
            self.ortho.setChecked(False)
            self.ortho.setEnabled(False)
        else:
            self.extended_label.setEnabled(False)
            self.extended.setChecked(False)
            self.extended.setEnabled(False)
            self.ortho_label.setEnabled(False)
            self.ortho.setChecked(False)
            self.ortho.setEnabled(False)
