from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QGridLayout, QLabel,
                             QSpinBox, QComboBox, QDialogButtonBox, QCheckBox)
from PyQt5.QtCore import Qt


class RunICADialog(QDialog):
    def __init__(self, parent, nchan, have_picard=True):
        super().__init__(parent)
        self.setWindowTitle("Run ICA")
        vbox = QVBoxLayout(self)
        grid = QGridLayout()
        grid.addWidget(QLabel("Method:"), 0, 0)
        self.method = QComboBox()
        methods = {"Extended Infomax": "extended-infomax",
                   "Infomax": "infomax", "FastICA": "fastica"}
        if have_picard:
            methods["Picard"] = "picard"
        self.method.addItems(methods.keys())
        grid.addWidget(self.method, 0, 1)
        grid.addWidget(QLabel("Number of components:"), 1, 0)
        self.n_components = QSpinBox()
        self.n_components.setMinimum(0)
        self.n_components.setMaximum(nchan)
        self.n_components.setValue(nchan)
        self.n_components.setAlignment(Qt.AlignRight)
        grid.addWidget(self.n_components, 1, 1)
        grid.addWidget(QLabel("Exclude bad segments:"), 2, 0)
        self.exclude_bad_segments = QCheckBox()
        self.exclude_bad_segments.setChecked(True)
        grid.addWidget(self.exclude_bad_segments)
        vbox.addLayout(grid)
        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok |
                                     QDialogButtonBox.Cancel)
        vbox.addWidget(buttonbox)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
