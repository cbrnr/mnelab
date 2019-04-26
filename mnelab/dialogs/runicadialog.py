from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QGridLayout, QLabel,
                             QSpinBox, QComboBox, QDialogButtonBox, QCheckBox)
from PyQt5.QtCore import Qt, pyqtSlot


class RunICADialog(QDialog):
    def __init__(self, parent, nchan, have_picard=True, have_sklearn=True):
        super().__init__(parent)
        self.setWindowTitle("Run ICA")
        vbox = QVBoxLayout(self)
        grid = QGridLayout()
        grid.addWidget(QLabel("Method:"), 0, 0)
        self.method = QComboBox()
        self.methods = {"Infomax": "infomax", "Extended-infomax": "extended-infomax"}
        if have_sklearn:
            self.methods["FastICA"] = "fastica"
        if have_picard:
            self.methods["Picard"] = "picard"
        self.method.addItems(self.methods.keys())
        if have_picard:
            self.method.setCurrentText("Picard")
        else:
            self.method.setCurrentText("Infomax")
        min_len = max(len(key) for key in self.methods.keys())
        self.method.setMinimumContentsLength(min_len)
        grid.addWidget(self.method, 0, 1)

        self.ortho_label = QLabel("Orthogonal:")
        grid.addWidget(self.ortho_label, 2, 0)
        self.ortho = QCheckBox()
        self.ortho.setChecked(False)
        grid.addWidget(self.ortho, 1, 1)

        self.toggle_options()
        self.method.currentIndexChanged.connect(self.toggle_options)

        grid.addWidget(QLabel("Number of components:"), 3, 0)
        self.n_components = QSpinBox()
        self.n_components.setMinimum(0)
        self.n_components.setMaximum(nchan)
        self.n_components.setValue(nchan)
        self.n_components.setAlignment(Qt.AlignRight)
        grid.addWidget(self.n_components, 2, 1)
        grid.addWidget(QLabel("Exclude bad segments:"), 4, 0)
        self.exclude_bad_segments = QCheckBox()
        self.exclude_bad_segments.setChecked(True)
        grid.addWidget(self.exclude_bad_segments)
        vbox.addLayout(grid)
        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok |
                                     QDialogButtonBox.Cancel)
        vbox.addWidget(buttonbox)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        vbox.setSizeConstraint(QVBoxLayout.SetFixedSize)

    @pyqtSlot()
    def toggle_options(self):
        """Toggle extended options.
        """
        if self.method.currentText() == "Picard":
            self.extended_label.show()
            self.extended.show()
            self.ortho_label.show()
            self.ortho.show()
        elif self.method.currentText() == "Infomax":
            self.extended_label.show()
            self.extended.show()
            self.ortho_label.hide()
            self.ortho.hide()
        else:
            self.extended_label.hide()
            self.extended.hide()
            self.ortho_label.hide()
            self.ortho.hide()
