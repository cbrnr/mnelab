# Authors: Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

from qtpy.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                            QFormLayout, QLabel, QSpinBox)
from qtpy.QtCore import Qt, Slot


class RunICADialog(QDialog):
    def __init__(self, parent, nchan, methods):
        super().__init__(parent)
        self.setWindowTitle("Run ICA")

        form = QFormLayout(self)
        self.method = QComboBox()
        self.method.addItems(methods)
        self.method.setCurrentIndex(int("Picard" in methods))

        self.method.currentIndexChanged.connect(self.toggle_options)
        form.addRow(QLabel("Method:"), self.method)

        self.extended = QCheckBox()
        self.extended.setChecked(True)
        form.addRow(QLabel("Extended:"), self.extended)

        self.ortho = QCheckBox()
        self.ortho.setChecked(False)
        form.addRow(QLabel("Orthogonal:"), self.ortho)

        self.n_components = QSpinBox()
        self.n_components.setRange(0, nchan)
        self.n_components.setValue(nchan)
        self.n_components.setAlignment(Qt.AlignRight)
        form.addRow(QLabel("Number of components:"), self.n_components)

        self.exclude_bad_segments = QCheckBox()
        self.exclude_bad_segments.setChecked(True)
        form.addRow(QLabel("Exclude bad segments:"), self.exclude_bad_segments)

        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok |
                                     QDialogButtonBox.Cancel)
        form.addRow(buttonbox)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        form.setSizeConstraint(QFormLayout.SetFixedSize)

        self.toggle_options()

    @Slot()
    def toggle_options(self):
        """Toggle extended options.
        """
        if self.method.currentText() == "Picard":
            self.extended.setEnabled(True)
            self.ortho.setEnabled(True)
        elif self.method.currentText() == "Infomax":
            self.extended.setEnabled(True)
            self.ortho.setChecked(False)
            self.ortho.setEnabled(False)
        else:
            self.extended.setChecked(False)
            self.extended.setEnabled(False)
            self.ortho.setChecked(False)
            self.ortho.setEnabled(False)
